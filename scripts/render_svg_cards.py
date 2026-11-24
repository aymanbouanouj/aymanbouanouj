#!/usr/bin/env python3
"""Render the GitHub profile dashboard and its offline review page."""
from __future__ import annotations

import argparse
import base64
import calendar
import datetime as dt
import html
import hashlib
import io
import json
import math
import os
import re
import struct
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from xml.etree import ElementTree as ET

from fontTools import subset
from fontTools.pens.boundsPen import BoundsPen
from fontTools.svgLib.path import parse_path
from fontTools.ttLib import TTFont, TTLibError

from brand_paths import PURPLE, WHITE
from dashboard_data import (
    CONTRIBUTIONS, MERGED_SEARCH, OWNER, ROOT, activity, contribution_url, read_json, validate,
)
from dashboard_technology import PRIVATE, SEED as TECHNOLOGY_SEED, grid_items, validate as validate_technology

WIDTH = 1160
ASSETS = ROOT / "assets/dashboard"
PROFILE = f"https://github.com/{OWNER}"
LIVE = f"https://raw.githubusercontent.com/{OWNER}/{OWNER}/profile-live/cards/"
SOURCE = f"{PROFILE}/{OWNER}/tree/profile-live/cards"
PROFILE_LINKS_URL = "https://beacons.ai/aymanbounaouj"
# Intentionally empty until the portfolio is launched. Set this to its real HTTPS URL,
# then regenerate README.md to activate the Portfolio button; never use a dummy link.
PORTFOLIO_SITE_URL = ""
DEMO = f"https://{OWNER}.github.io/ab-train-ticket-studio/"
HERO_NAME = "Ayman Bounaouj"
HERO_HEADLINE = "Software Developer"
HERO_SUBHEADLINES = ("Full-Stack Web Development", "Building Practical & Secure Digital Products")

INK = "#f6f3fc"
COPY = "#d9d6e4"
MUTED = "#b4adc5"
VIOLET = "#bd8dff"
BRAND = "#8d43ff"
LILAC = "#b85cff"
BORDER = "#353145"
SURFACE = "#131522"
HEAT = ("#232034", "#4d307c", "#7345b5", "#a46bf0", "#cf9dff")
SVG_NS = "http://www.w3.org/2000/svg"
FONT_URI = "data:font/woff;base64,"
FONT_DATA = re.compile(re.escape(FONT_URI) + r"([A-Za-z0-9+/=]+)")
TRAIN_URI = "data:image/jpeg;base64,"
TRAIN_SHA256 = "c1f329c32b3724b142393e8b34f12da8636db2cc5c233e874520ac049679d7fa"
HERO_BG_SHA256 = "4cc81a8eea82f21757609fa4da6f3416859ae7ef3eacd8a3fbdcc30296c8632a"

FONT_FILES = {
    400: "Poppins-Regular.ttf",
    500: "Poppins-Medium.ttf",
    600: "Poppins-SemiBold.ttf",
    700: "Poppins-Bold.ttf",
}
TRANSPARENT_HEADING_STYLE = (
    '@media (prefers-color-scheme: light){'
    '.transparent-heading text{fill:#241b34}'
    '.transparent-heading text[text-anchor="end"]{fill:#514861}'
    '.transparent-heading path{stroke:#67419e}'
    '}'
)
ANIMATION = """
@keyframes rise{from{opacity:.35;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}
@keyframes fade{from{opacity:.25}to{opacity:1}}
@keyframes grow{from{transform:scaleY(.16)}to{transform:scaleY(1)}}
@keyframes glint{0%,100%{opacity:1}45%{opacity:.62}}
.rise,.fade,.grow,.glint{animation-fill-mode:backwards;animation-delay:var(--delay,0ms);
animation-duration:380ms;animation-timing-function:cubic-bezier(.21,.65,.29,1)}
.rise{animation-name:rise}.fade{animation-name:fade}.glint{animation-name:glint;animation-duration:640ms}
.grow{animation-name:grow;transform-box:fill-box;transform-origin:center bottom}
@media (prefers-reduced-motion: reduce){
.rise,.fade,.grow,.glint{animation:none!important;opacity:1!important;transform:none!important}
}
"""

GLYPHS = {
    "code": "M8 6 2 12l6 6m8-12 6 6-6 6M14 3l-4 18",
    "flame": "M12 22a8 8 0 0 0 8-8c0-4-2-6-4-8 .5 3-1 4-2 4 0-4-2-7-5-8 1 5-5 7-5 12a8 8 0 0 0 8 8Zm0 0a3 3 0 0 0 3-3c0-2-1-3-3-4-2 1-3 2-3 4a3 3 0 0 0 3 3Z",
    "merge": "M6 9v6m3 3c7 0 9-4 9-9M6 3a3 3 0 1 0 0 6 3 3 0 0 0 0-6Zm0 12a3 3 0 1 0 0 6 3 3 0 0 0 0-6Zm12-12a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z",
    "calendar": "M7 3v4m10-4v4M4 10h16M6 5h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Zm4 11 1.5 1.5L15 14",
    "grid": "M4 9h16M4 15h16M9 4v16m6-16v16M6 4h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z",
    "stack": "m12 3 9 5-9 5-9-5 9-5ZM3 12l9 5 9-5M3 16l9 5 9-5",
    "tools": "m14 6 4-4 4 4-4 4m-4-4 4 4M3 21l7-7m-7 7 2 1 7-7M9 6a4 4 0 0 0-5-4l2 3-1 2-3-1a4 4 0 0 0 5 5l9 9a2 2 0 0 0 3-3l-9-9a4 4 0 0 0-1-2Z",
    "rocket": "M8 16 5 19m-2 2 2-5m3-4c2-5 5-8 13-9-1 8-4 11-9 13l-4-4Zm0 0H4l-2 4h5m5 0v5l4-2v-5m1-7h.01",
    "branch": "M6 8v8m12-8c0 8-6 8-9 8M6 2a3 3 0 1 0 0 6 3 3 0 0 0 0-6Zm0 14a3 3 0 1 0 0 6 3 3 0 0 0 0-6ZM18 2a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z",
    "target": "M20 10a8 8 0 1 1-6-6m3 8a5 5 0 1 1-5-5m0 5 9-9m-5 0h5v5",
    "pin": "m15 3 6 6-4 1-3 5-5 1-1-5 5-3 2-5Zm-7 13-5 5",
    "repo": "M5 17h14V4H6a2 2 0 0 0-2 2v13a2 2 0 0 1 2-2zm-1 2a2 2 0 0 0 2 2h13M8 7h7",
    "star": "m12 3 2.6 5.7 6.2.8-4.6 4.3 1.2 6.2-5.4-3.1-5.4 3.1 1.2-6.2-4.6-4.3 6.2-.8L12 3Z",
    "external": "M13 4h7v7m0-7-9 9m7 1v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4",
    "arrow": "M4 12h15m-6-6 6 6-6 6",
    "profile": "M8 20H4v-4a4 4 0 0 1 4-4h8a4 4 0 0 1 4 4v4H8ZM12 3a3 3 0 1 1 0 6 3 3 0 0 1 0-6Z",
    "linkedin": "M3 9v12m0-17v.5M9 21V9m0 5a5 5 0 0 1 10 0v7",
    "instagram": "M7 3h10a4 4 0 0 1 4 4v10a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V7a4 4 0 0 1 4-4Zm5 5a4 4 0 1 0 0 8 4 4 0 0 0 0-8Zm5.5-1.5h.01",
    "facebook": "M17 3h-3a4 4 0 0 0-4 4v14m-4-10h11",
    "x": "M4 3l16 18M20 3 4 21M4 3h5l11 18h-5",
    "medium": "M2 8h3l7 9 7-9h3M5 8v10m14-10v10",
    "chat": "M4 4h16v13H9l-5 4zm4 5h8m-8 4h5",
    "windows": "M2 5l9-1.6v8H2Zm11-2 9-1.6v10h-9ZM2 13h9v8l-9-1.6Zm11 0h9v10l-9-1.6Z",
}

PROJECTS = {
    "morocco2030": (
        "Morocco2030",
        "Tournament portal with role-based staff access.",
        ("Laravel", "PHP", "MySQL"),
    ),
    "ab-train-ticket-studio": (
        "AB Train Ticket Studio",
        "Rail booking simulation with QR and PDF tickets.",
        ("JavaScript", "Vite", "Playwright"),
    ),
    "PC-Full-Check": (
        "PC Full Check",
        "Read-only Windows diagnostics and local reports.",
        ("PowerShell", "Windows"),
    ),
    "violetgate": (
        "VioletGate",
        "Responsive authentication UI with keyboard access.",
        ("HTML", "CSS", "JavaScript"),
    ),
    "ayman-calc": (
        "Ayman Calc",
        "Responsive calculator without eval().",
        ("HTML", "CSS", "JavaScript"),
    ),
}
PINS = (
    ("violetgate", PROJECTS["violetgate"][1]),
    ("ayman-calc", PROJECTS["ayman-calc"][1]),
)
PROJECT_EVIDENCE = {
    "morocco2030": "RBAC and automated tests",
    "ab-train-ticket-studio": "4 languages; browser tests",
    "PC-Full-Check": "Privacy controls; test suite",
}
CURRENT = (
    (OWNER, "Profile automation", "code"),
    ("Understand-Anything", "Understand-Anything", "branch"),
    ("gestion-vaccination", "Gestion Vaccination", "stack"),
)
# Optical maximums for the visible paths, in SVG units. Wide and outline marks
# need more room than filled squares to read as part of the same set.
GRID_MARK_SIZES = {
    "PHP": (48, 30), "JavaScript": (35, 35), "TypeScript": (35, 35),
    "Python": (39, 37), "HTML": (34, 38), "CSS": (34, 38),
    "MySQL": (43, 37), "Laravel": (42, 41), "React": (43, 40),
    "Docker": (45, 35), "Playwright": (42, 34), "Tailwind CSS": (44, 32),
    "Vite": (39, 39), "Node.js": (38, 40), "Composer": (39, 42),
    "pnpm": (33, 33), "GitHub Actions": (37, 37), "PowerShell": (40, 35),
}
EXTERNAL_COPY = (
    ("Egonex-AI / Understand-Anything", "Apply dashboard filters to the structural code graph."),
    ("OWASP / Cheat Sheet Series", "Contributed to the cheat-sheet revision discussion."),
    ("php / doc-en", "Clarify the distinction between Error and Exception."),
)
HEADERS = {
    "featured": ("Featured Projects", "Selected public software", "rocket"),
    "opensource": ("Open Source & Verified Contributions", "Upstream GitHub work", "branch"),
    "building": ("Recently Updated Projects", "Last public push", "target"),
    "pinned": ("More Repositories", "Additional public projects", "pin"),
}


def esc(value) -> str:
    return html.escape(str(value), quote=True)


@lru_cache
def font_metrics(weight: int) -> tuple[int, dict[int, int]]:
    with TTFont(ASSETS / "fonts" / FONT_FILES[weight]) as font:
        metrics = font["hmtx"].metrics
        return font["head"].unitsPerEm, {code: metrics[g][0] for code, g in font.getBestCmap().items()}


def text_width(value: str, size: float, weight: int = 400) -> float:
    units, widths = font_metrics(weight)
    return sum(widths.get(ord(c), units) for c in value) * size / units


@lru_cache(maxsize=128)
def font_subset(weight: int, characters: str) -> str:
    """Run the pyftsubset engine in-process, then encode its WOFF output."""
    with TTFont(ASSETS / "fonts" / FONT_FILES[weight], recalcTimestamp=False) as font:
        options = subset.Options()
        options.hinting = False
        options.layout_features = []
        options.name_IDs = [0, 1, 2, 4, 6, 13, 14]
        options.ignore_missing_unicodes = False
        worker = subset.Subsetter(options=options)
        worker.populate(text=characters)
        worker.subset(font)
        font.flavor = "woff"
        buffer = io.BytesIO()
        font.save(buffer)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def wrap(value: str, *, size: float, width: float) -> list[str]:
    lines: list[str] = []
    for word in value.split():
        if lines and text_width(lines[-1] + " " + word, size) <= width:
            lines[-1] += " " + word
        else:
            lines.append(word)
    return lines


def wrap_badge(value: str, *, size: float, width: float, weight: int) -> list[str]:
    lines = []
    while text_width(value, size, weight) > width:
        end = next(index for index in range(1, len(value) + 1) if text_width(value[:index], size, weight) > width)
        end = max(1, end - 1)
        split = value.rfind(" ", 0, end + 1)
        end = split if split > 0 else end
        lines.append(value[:end])
        value = value[end:].lstrip()
    return lines + [value]


def box(x, y, w, h, fill=SURFACE, stroke="none", radius=0) -> str:
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>'


def path(geometry, fill="none", stroke="none", line=1) -> str:
    return (f'<path d="{geometry}" fill="{fill}" stroke="{stroke}" stroke-width="{line}"'
            ' stroke-linecap="round" stroke-linejoin="round"/>')


def circle(x, y, r, fill) -> str:
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}"/>'


def group(content, transform="", *, motion="", delay=0) -> str:
    transform_attr = f' transform="{transform}"' if transform else ""
    animate = f' class="{motion}" style="--delay:{delay}ms"' if motion else ""
    return f"<g{transform_attr}{animate}>{content}</g>"


def panel(x, y, w, h, radius=14, *, fill="url(#panel)", stroke=BORDER) -> str:
    return box(x + .6, y + .6, w - 1.2, h - 1.2, fill, stroke, radius)


def gradient(name, stops, *, axis=(0, 0, 0, 1)) -> str:
    x1, y1, x2, y2 = axis
    colors = "".join(f'<stop offset="{at}" stop-color="{color}"/>' for at, color in stops)
    return (f'<linearGradient id="{name}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">'
            f"{colors}</linearGradient>")


def light(name, color, opacity, *, cx=".5", cy=".5") -> str:
    return (f'<radialGradient id="{name}" cx="{cx}" cy="{cy}" r=".5">'
            f'<stop stop-color="{color}" stop-opacity="{opacity}"/>'
            f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>')


def clip(name, shape, content) -> tuple[str, str]:
    return f'<clipPath id="{name}">{shape}</clipPath>', f'<g clip-path="url(#{name})">{content}</g>'


def glyph(name: str, x: float, y: float, size: float, color=VIOLET) -> str:
    if name == "windows":
        mark = path(GLYPHS[name], fill=color)
    else:
        mark = path(GLYPHS[name], stroke=color, line=1.7)
    return group(mark, f"translate({x} {y}) scale({size / 24:.5f})")


@lru_cache
def icon_registry() -> dict:
    return read_json(ASSETS / "tech-icons.json")


@lru_cache
def brand_icons() -> dict:
    icons = icon_registry()["icons"].copy()
    legacy = read_json(ROOT / "scripts/tech_icon_paths.json")["icons"]
    for name, mark in legacy.items():
        if name in icons and name != "PowerShell":
            continue
        icon = {"d": mark["path"], "fill": mark["color"]}
        if mark.get("stroke"):
            icon.update(fill="none", stroke=mark["color"])
        icons[name] = {"viewBox": mark["viewBox"], "paths": [icon]}
    return icons


def icon_paths(icon: dict) -> str:
    return "".join(path(p["d"], p["fill"], p["stroke"], line=2.2) if "stroke" in p else
                   f'<path d="{esc(p["d"])}" fill="{esc(p["fill"])}"/>' for p in icon["paths"])


def technology(name: str, x: float, y: float, size: float) -> str:
    if name == "Windows":
        return glyph("windows", x, y, size, "#5dbdff")
    icon = brand_icons()[name]
    return group(icon_paths(icon), f'translate({x} {y}) scale({size / icon["viewBox"]:.5f})')


@lru_cache
def grid_mark(name: str) -> tuple[str, tuple[float, float, float, float]] | None:
    icon = icon_registry()["grid_icons"].get(name) or brand_icons().get(name)
    if icon is None:
        return None
    pen = BoundsPen(None)
    for item in icon["paths"]:
        parse_path(item["d"], pen)
    return icon_paths(icon), pen.bounds


def centered_mark(name: str, cx: float, cy: float, *, width: int, height: int) -> str:
    mark = grid_mark(name)
    if mark is None:
        size = min(width, height, 30)
        return f'<g aria-hidden="true">{glyph("code", cx - size / 2, cy - size / 2, size)}</g>'
    art, (left, top, right, bottom) = mark
    optical_w, optical_h = GRID_MARK_SIZES.get(name, (36, 36))
    scale = min(min(width, optical_w) / (right - left), min(height, optical_h) / (bottom - top))
    x = cx - (right + left) * scale / 2
    y = cy - (bottom + top) * scale / 2
    return group(art, f"translate({x:.3f} {y:.3f}) scale({scale:.6f})")


def logo(x, y, width) -> str:
    return group(path(WHITE, INK) + path(PURPLE, "url(#brand)"),
                 f"translate({x} {y}) scale({width / 314:.5f})")


class Card:
    def __init__(self, w: int, h: int, title: str, description: str):
        self.w, self.h = w, h
        self.title, self.description = title, description
        self.styles: list[str] = []
        self.parts: list[str] = []
        self.defs = [
            gradient("panel", ((0, "#171a28"), (1, "#11131e")), axis=(0, 0, 1, 1)),
            gradient("brand", ((0, BRAND), (1, LILAC)), axis=(0, 1, 1, 0)),
        ]
        self.glyphs: dict[int, set[str]] = {}

    def text(self, x, y, value, size, *, weight=400, fill=INK, anchor="start", tracking=0) -> str:
        value = str(value)
        _, supported = font_metrics(weight)
        self.glyphs.setdefault(weight, set()).update(char for char in value if ord(char) in supported)
        return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}"'
                f' text-anchor="{anchor}" letter-spacing="{tracking}">{esc(value)}</text>')

    def heading(self, title, note, symbol, *, x=0, y=0, width=WIDTH) -> str:
        return (glyph(symbol, x + 8, y + 13, 29)
                + self.section_title(x + 52, y + 39, title)
                + self.text(x + width - 8, y + 38, note, 17, fill=MUTED, anchor="end"))

    def section_title(self, x, y, title) -> str:
        return self.text(x, y, title, 33 if self.w < WIDTH else 34, weight=700, tracking="-.6")

    def add_transparent_heading(self, content: str) -> None:
        # These headings sit on the embedding page's canvas. Other card text sits on dark panels.
        self.styles.append(TRANSPARENT_HEADING_STYLE)
        self.parts.append(f'<g class="transparent-heading">{content}</g>')

    def svg(self, static: bool) -> str:
        faces = []
        for weight, characters in sorted(self.glyphs.items()):
            if characters:
                font = font_subset(weight, "".join(sorted(characters)))
                faces.append(f"@font-face{{font-family:ProfilePoppins;font-weight:{weight};"
                             f"src:url({FONT_URI}{font}) format('woff')}}")
        css = ("".join(faces)
               + "text{font-family:ProfilePoppins,Arial,Helvetica,sans-serif;font-variant-numeric:tabular-nums}"
               + "".join(self.styles)
               + ("" if static else ANIMATION.strip()))
        return (
            f'<svg xmlns="{SVG_NS}" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}"'
            ' role="img" aria-labelledby="title desc">'
            f'<title id="title">{esc(self.title)}</title><desc id="desc">{esc(self.description)}</desc>'
            f'<defs>{"".join(self.defs)}</defs><style>{css}</style>\n'
            + "\n".join(self.parts) + "\n</svg>\n"
        )


def system_illustration() -> str:
    grid = path("M13 147 153 89 299 148 157 206Z M49 132l145 59 M84 117l145 60 "
                "M118 103l146 59 M49 162l141-59 M85 177l142-59 M121 192l142-59",
                stroke="#493366")
    traces = (
        path("M41 74 81 90l33-14M244 60l-47 20M111 143l-25 11v23M210 124l37 15 31-12",
             stroke="#9d71ea", line=1.5)
        + path("M153 40v23M153 146v37M41 74v24M244 60v28M278 127v16",
               stroke="#53397d", line=1.2)
    )
    modules = "".join(
        group(path("M0-12 29 0 0 12-29 0Z", "#1c1230", color, 1.4)
              + path("M-15 0 0-6 15 0 0 6Z", "none", "#7850b4")
              + circle(0, 0, 2.45, dot), f"translate({x} {y})")
        for x, y, color, dot in ((41, 74, "#9964d9", "#dbb7ff"), (244, 60, "#9c6feb", "#d4b4ff"),
                                 (278, 127, "#744dbe", "#ae87ff"), (86, 177, "#6945ac", "#aa82f4"))
    )
    layers = (
        path("M81 114 153 84 225 114 225 129 153 159 81 129Z", "#110c22", "#6241a3", 1.4)
        + path("M81 114 153 144 225 114M153 144v15", stroke="#7b51c1", line=1.3)
        + path("M81 94 153 64 225 94 225 107 153 138 81 107Z", "#23143d", "#8e63ce", 1.5)
        + path("M81 94 153 124 225 94M153 124v14", stroke="#a57add", line=1.4)
        + path("M81 84 153 53 225 84 153 115Z", "url(#system-surface)", "#bd8dff", 1.75)
        + path("M99 84 153 61 207 84 153 107Z", "none", "#9065ce", 1.1)
        + path("M132 79l-10 5 10 4M174 79l10 5-10 4M156 75l-6 18", stroke="#f0d7ff", line=2.6)
        + path("M108 123l16 7m57-1 17-7", stroke="#b486f9", line=1.4)
    )
    terminals = circle(153, 39, 3.4, "#dbb9ff") + circle(153, 183, 3.1, "#b58cf1")
    return ('<g id="system-illustration">'
            '<ellipse cx="157" cy="112" rx="153" ry="101" fill="url(#system-glow)"/>'
            + grid + traces + modules + layers + terminals + "</g>")


@lru_cache(maxsize=1)
def hero_background() -> str:
    """Embed the approved owner-supplied violet background, checked against its exact digest."""
    payload = (ASSETS / "hero-background.jpg").read_bytes()
    if hashlib.sha256(payload).hexdigest() != HERO_BG_SHA256:
        raise ValueError("Hero background bytes differ from the owner-supplied reference")
    return TRAIN_URI + base64.b64encode(payload).decode("ascii")


def hero(*, compact=False) -> Card:
    w, h = (680, 234) if compact else (WIDTH, 235)
    first_line, second_line = HERO_SUBHEADLINES
    card = Card(w, h, f"{HERO_NAME} | {HERO_HEADLINE}", f"{first_line}. {second_line}. "
                "Original AB monogram beside a layered developer system and its connected modules.")
    card.styles.append("text{opacity:.98}")
    card.defs += [
        gradient("hero", ((0, "#17122b"), (".57", "#0d101d"), (1, "#191133")), axis=(0, 0, 1, 1)),
        gradient("system-surface", ((0, "#593381"), (".58", "#351957"), (1, "#1a1234")), axis=(0, 0, 1, 1)),
        light("system-glow", "#8b45f1", ".43"),
    ]
    backdrop = (
        box(0, 0, w, h, "url(#hero)")
        + f'<image x="0" y="0" width="{w}" height="{h}" preserveAspectRatio="none" href="{hero_background()}"/>'
    )
    art = group(system_illustration(), "translate(852 13) scale(.98)") if not compact else (
        '<g opacity=".56">' + group(system_illustration(), "translate(538 118) scale(.48)") + "</g>"
    )
    edge, inside = clip("hero-crop", box(0, 0, w, h, radius=20), backdrop + art)
    card.defs.append(edge)
    card.parts.extend((inside, panel(0, 0, w, h, 20, fill="none", stroke="#564574")))
    if compact:
        mark = logo(31, 44, 122) + path("M183 41v151", stroke="#645478", line=1.1)
        copy = (card.text(212, 78, HERO_NAME, 48, weight=600, tracking="-1.5")
                + card.text(213, 123, HERO_HEADLINE, 35, weight=600, fill=VIOLET, tracking="-.55")
                + card.text(214, 160, first_line, 24, weight=500, fill=COPY)
                + card.text(214, 195, second_line, 21, fill=COPY, tracking="-.22"))
    else:
        mark = logo(73, 67, 140) + path("M248 43v151", stroke="#645478", line=1.15)
        copy = (card.text(288, 82, HERO_NAME, 58, weight=600, tracking="-1.55")
                + card.text(289, 133, HERO_HEADLINE, 42, weight=600, fill=VIOLET, tracking="-.65")
                + card.text(290, 170, first_line, 25, weight=500, fill=COPY)
                + card.text(290, 201, second_line, 23, fill=COPY))
    card.parts.extend((group(mark, motion="glint", delay=80), group(copy, motion="rise")))
    return card


def button(label, symbol, *, primary=False, unpublished=False) -> Card:
    """Standalone SVG button. README handles navigation through an outer HTML anchor."""
    w, h = 182, 50
    detail = ("Portfolio website is not published yet; the button has no link."
              if unpublished else "Opens " + label + " in the linked public profile.")
    card = Card(w, h, label, detail)
    ink = "#26113f" if primary else COPY
    card.defs.append(gradient("action", ((0, "#8c43ef"), (".55", "#b663ff"),
                                          (1, "#d48dff")), axis=(0, 0, 1, 1)))
    card.parts.append(panel(0, 0, w, h, 12,
                            fill="#302044" if unpublished else "url(#action)" if primary else "url(#panel)",
                            stroke="#77539d" if unpublished else "#aa72ed" if primary else BORDER))
    if unpublished:
        card.parts.append(card.text(w / 2, 22, label, 18, weight=600, fill="#e3ccff", anchor="middle"))
        card.parts.append(card.text(w / 2, 39, "Coming soon", 12.5, fill="#d3b5f1", anchor="middle"))
    elif primary:
        # Faithful to the reference: Portfolio text and an external-link arrow, no extra left icon.
        card.parts.append(card.text(31, 31, label, 18, weight=600, fill=ink))
        card.parts.append(glyph("external", 147, 17, 15, ink))
    else:
        card.parts.append(glyph(symbol, 13, 15, 20, ink))
        card.parts.append(card.text(43, 31, label, 17, weight=600, fill=ink))
        card.parts.append(glyph("arrow", 151, 17, 16, MUTED))
    return card


def metrics(stats: dict, public: dict, *, compact=False) -> Card:
    numbers = (
        ("code", f'{stats["total"]:,}', "Contributions in the last year"),
        ("flame", f'{stats["current"]:,} ' + ("day" if stats["current"] == 1 else "days"),
         "Current streak"),
        ("merge", f'{public["merged_public_prs"]:,}', "Merged public PRs"),
        ("calendar", f'{stats["active"]:,}', "Active days in the last year"),
    )
    w = 680 if compact else WIDTH
    cols = 2 if compact else 4
    height, gap = 104, 15
    h = 2 * height + gap if compact else height
    tile = (w - (cols - 1) * gap) / cols
    card = Card(w, h, "GitHub statistics",
                ". ".join(f"{label} {value}" for _, value, label in numbers)
                + f'. Calendar checked {stats["verified_at"].date():%Y-%m-%d} UTC.')
    card.defs.append(light("metricglow", "#a44ffb", ".16"))
    for index, (symbol, value, label) in enumerate(numbers):
        y, x = divmod(index, cols)
        x, y = x * (tile + gap), y * (height + gap)
        body = panel(x, y, tile, height, fill="#1b172a" if index == 0 else "url(#panel)")
        body += f'<ellipse cx="{x+47}" cy="{y+51}" rx="40" ry="41" fill="url(#metricglow)"/>'
        body += glyph(symbol, x + 25, y + 31, 43)
        body += card.text(x + 88, y + 49, value, 33 if len(value) < 9 else 28,
                          weight=600, tracking="-1")
        for line, text in enumerate(wrap(label, size=16, width=tile - 106)):
            body += card.text(x + 89, y + 73 + 21 * line, text, 16, fill=COPY)
        card.parts.append(group(body, motion="rise", delay=100 + index * 55))
    return card


def heat_level(count: int) -> int:
    return sum(count >= cutoff for cutoff in (1, 4, 8, 16))


def contribution_calendar(stats: dict, *, compact=False) -> Card:
    start, end = stats["range"]
    sunday = start - dt.timedelta(days=(start.weekday() + 1) % 7)
    columns = (end - sunday).days // 7 + 1
    w = 680 if compact else WIDTH
    left, top = (64, 96) if compact else (98, 77)
    h = top + 128
    step = (w - left - 35) / columns
    card = Card(w, h, "Contribution Activity",
                f'{stats["total"]:,} GitHub contributions from {start} to {end}, UTC. '
                "Sunday to Saturday. Violet intensities represent 0, 1 to 3, 4 to 7, 8 to 15 and 16 or more.")
    card.styles.append("text{opacity:.98}")
    date_line = f'{stats["total"]:,} contributions  |  {start:%d %b %Y} to {end:%d %b %Y}'
    card.parts.extend((
        panel(0, 0, w, h, 17),
        card.heading("Contribution Activity", "" if compact else date_line, "grid", x=13, y=3, width=w - 26),
    ))
    if compact:
        card.parts.append(card.text(25, 66, date_line, 18, fill=COPY))
    for weekday, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        card.parts.append(card.text(left - 15, top + 9 + weekday * 13, name, 15, fill=COPY, anchor="end"))
    weeks: list[list[str]] = [[] for _ in range(columns)]
    months: list[tuple[float, str]] = []
    for item in stats["days"]:
        day, n = item["date"], item["count"]
        delta = (day - sunday).days
        col, row = divmod(delta, 7)
        x = left + col * step
        y = top + row * 13
        if day == start or day.day == 1:
            months.append((x, calendar.month_abbr[day.month]))
        label = f"{day.isoformat()}: {n} " + ("contribution" if n == 1 else "contributions")
        weeks[col].append(
            f'<rect x="{x:.2f}" y="{y}" width="{step - (1.9 if compact else 3.1):.2f}" height="10.5" rx="2"'
            f' data-date="{day.isoformat()}" data-count="{n}" fill="{HEAT[heat_level(n)]}">'
            f"<title>{label}</title></rect>"
        )
    # Prefer complete calendar months when the first partial month has little room.
    if len(months) > 1 and months[1][0] - months[0][0] < (36 if compact else 44):
        months.pop(0)
    right = left - 6
    for x, label in months:
        x = max(x, right + 6)
        label_width = text_width(label, 15)
        if x + label_width < w - 16:
            card.parts.append(card.text(round(x, 2), top - 8, label, 15, fill=COPY))
            right = x + label_width
    for index, week in enumerate(weeks):
        card.parts.append(group("".join(week), motion="fade", delay=170 + index * 9))

    legend = w - (241 if compact else 278)
    legend_y = top + 102
    card.parts.append(card.text(legend, legend_y + 12, "Less", 15, fill=COPY))
    for index, fill in enumerate(HEAT):
        card.parts.append(box(legend + 45 + index * 24, legend_y, 18, 14, fill, radius=3))
    card.parts.append(card.text(legend + 212, legend_y + 12, "More", 15, fill=COPY, anchor="end"))
    return card


def tech_grid(evidence: dict, *, tools=False, compact=False) -> Card:
    title, note, symbol = (("Frameworks / Build Tools", "Frameworks, build and delivery", "tools") if tools
                           else ("Languages & Technical Stack", "Evidence from public work", "stack"))
    items = grid_items(evidence, tools=tools)
    limit = (2 if tools else 3) if compact else (7 if tools else 6)
    cols = min(limit, max(1, len(items)))
    w = 680 if compact else WIDTH
    h = (82 if tools else 62) if compact else (76 if tools else 55)
    rows = max(1, (len(items) + cols - 1) // cols)
    inset = 10
    top = 58 if compact else 51
    gap = 14 if compact or not tools else 12
    available = w - 2 * inset - (cols - 1) * gap
    extra = [0] * cols
    if tools and not compact:
        room_for_label = {"Laravel": 14, "Composer": 12, "GitHub Actions": 32, "Playwright": 18}
        for col, (name, _) in enumerate(items[:cols]):
            extra[col] = room_for_label.get(name, 0)
    widths = [(available - sum(extra)) / cols + n for n in extra]
    extended = evidence.get("schema", 1) == 2
    empty = "No verified evidence available." if extended else "No verified public evidence available."
    description = ", ".join(name for name, _ in items) + ". Evidence links in the README." if items else empty
    if not tools and extended and any(all(proof["scope"] == PRIVATE for proof in evidence["evidence"][name])
                                      for name, _ in items):
        note = "Public work and language aggregates"
        description += " Includes authorized private language aggregates."
    label_inset = 64 if compact else (54 if tools else 67)
    name_size = (22 if tools else 21.5) if compact else (15.5 if tools else 16)
    caption_size = 17 if compact else 12.2
    name_step = math.ceil(name_size * 1.25)
    caption_step = math.ceil(caption_size * 1.25)
    badge_lines = []
    heights = [h] * rows
    for index, (name, caption) in enumerate(items):
        row, col = divmod(index, cols)
        room = widths[col] - label_inset - 6
        names = wrap_badge(name, size=name_size, width=room, weight=500) if extended else [name]
        captions = wrap_badge(caption, size=caption_size, width=room, weight=400) if extended else [caption]
        added = (len(names) - 1) * name_step + (len(captions) - 1) * caption_step
        heights[row] = max(heights[row], h + added)
        badge_lines.append((names, captions, added))
    card = Card(w, top + sum(heights) + (rows - 1) * gap + 2, title, description)
    # A translucent text layer avoids colored LCD fringes on small SVG text in Chromium.
    card.styles.append("text{opacity:.98}")
    card.defs.append(gradient("tech-panel", ((0, "#171b26"), (1, "#11151f")), axis=(0, 0, 1, 1)))
    heading = glyph(symbol, 16, 13, 29 if compact else 28) + card.section_title(68, 40 if compact else 39, title)
    if not compact:
        heading += card.text(w - inset, 38, note, 16.5, fill=COPY, anchor="end")
    card.add_transparent_heading(heading)
    if not items:
        card.parts.append(panel(inset, top, available, h, radius=12))
        card.parts.append(card.text(inset + 18, top + h / 2 + 6, empty, 21 if compact else 18, fill=COPY))
        return card

    for index, (name, _) in enumerate(items):
        row, col = divmod(index, cols)
        x = round(inset + sum(widths[:col]) + col * gap, 2)
        y = top + sum(heights[:row]) + row * gap
        width = round(widths[col], 2)
        center_y = y + heights[row] / 2
        body = panel(x, y, width, heights[row], radius=12, fill="url(#tech-panel)", stroke="#373b48")
        broad_slot = compact or not tools
        body += centered_mark(name, x + (32 if broad_slot else 27), center_y,
                              width=48 if broad_slot else 36, height=42)
        names, captions, added = badge_lines[index]
        baseline = center_y - 4 if tools else center_y + (7.5 if compact else 5.5)
        baseline -= added / 2
        label_x = round(x + label_inset, 2)
        for line, label in enumerate(names):
            body += card.text(label_x, baseline + line * name_step, label, name_size, weight=500)
        if tools:
            caption_y = baseline + (len(names) - 1) * name_step + (23 if compact else 17)
            for line, label in enumerate(captions):
                body += card.text(label_x, caption_y + line * caption_step, label, caption_size, fill=COPY)
        card.parts.append(group(body, motion="rise", delay=236 + min(index, 24) * 28))
    return card


def stadium_scene(card: Card) -> str:
    card.defs += [
        gradient("sky", ((0, "#212641"), (".5", "#7c4e66"), (".85", "#d58d78"), (1, "#f0a875"))),
        gradient("ring", ((0, "#fff1b7"), (".4", "#cf9771"), (1, "#755243"))),
        gradient("outer", ((0, "#90624e"), (".7", "#47313e"), (1, "#241c2b"))),
        light("stadiumlight", "#ffb473", ".63"),
    ]
    hills = (
        path("M0 58 42 47 64 53 87 43 119 56 145 46 171 55 200 40 235 53 269 42 297 53 327 45 376 59V147H0Z",
             "#64516d")
        + path("M0 68 34 60 70 72 104 58 139 65 169 56 196 69 228 55 262 62 293 51 336 63 376 54V147H0Z",
               "#453c59")
        + path("M0 88 52 69 117 86 154 71 217 84 284 68 321 81 376 75V147H0Z", "#292a43")
        + path("M0 113c59-9 93-15 145-12s47-12 114-9 89 14 117 14v41H0Z", "#202238")
    )
    city = "".join(
        box(i * 13 + 3, 93 + ((i * 7) % 13), 1.1 + i % 3, 1, "#be8a70", radius=".5")
        for i in range(29)
    )
    stands = (
        '<ellipse cx="250" cy="105" rx="108" ry="39" fill="url(#stadiumlight)"/>'
        '<ellipse cx="247" cy="121" rx="99" ry="19" fill="#101323" opacity=".78"/>'
        + path("M157 96q6 35 89 36 85 0 93-37l-15-2-153 1Z", "url(#outer)", "#d09073", ".7")
        + '<ellipse cx="248" cy="94" rx="92" ry="25" fill="#523d4a" stroke="#402f39"/>'
        '<ellipse cx="248" cy="91" rx="89" ry="23" fill="url(#ring)" stroke="#ffe0a2" stroke-width="1.35"/>'
        '<ellipse cx="248" cy="91" rx="67" ry="17" fill="#4a424d" stroke="#e7b997" stroke-width="1.1"/>'
        '<ellipse cx="248" cy="91" rx="51" ry="12" fill="#324e49"/>'
        + path("M223 87h48l10 8h-66Zm20 0 3 8m8-4h.1", stroke="#94b19a", line=".65")
        + path("M167 108c33 25 132 28 162-1m-150 11c29 17 109 18 138 0",
               stroke="#e0a271", line=".9")
    )
    for i in range(20):
        t = i / 19
        x = 166 + t * 164
        y = 110 + (1 - (2 * t - 1) ** 2) * 7
        stands += path(f"M{x:.2f} {y:.2f}l{(t-.5)*11:.2f} 7", stroke="#b77959", line=".85")
    return (
        box(0, 0, 376, 147, "url(#sky)")
        + '<ellipse cx="318" cy="53" rx="128" ry="47" fill="url(#stadiumlight)" opacity=".69"/>'
        + path("M135 33q89-9 171 0m-78 12q64-5 134 0", stroke="#d7a099", line=".7")
        + hills + city + stands
        + path("M5 145q59-26 142-23m156 18 73-12", stroke="#695061", line=".9")
    )


@lru_cache
def train_jpeg() -> bytes:
    jpeg = (ASSETS / "train-header.jpg").read_bytes()
    if hashlib.sha256(jpeg).hexdigest() != TRAIN_SHA256:
        raise ValueError("Train artwork failed its source fingerprint")
    return jpeg


def train_scene(card: Card) -> str:
    # The vector scene remains complete if a client blocks embedded raster content.
    card.defs += [
        gradient("train", ((0, "#252548"), (".65", "#806076"), (1, "#57465e"))),
        gradient("cab", ((0, "#eeeeff"), (".5", "#b4adcb"), (1, "#715f95"))),
        '<linearGradient id="train-tint" x1="0" x2="1" y1="1" y2="0">'
        '<stop stop-color="#211536" stop-opacity=".54"/>'
        '<stop offset=".66" stop-color="#443258" stop-opacity=".22"/>'
        '<stop offset="1" stop-color="#312454" stop-opacity=".36"/></linearGradient>',
    ]
    fallback = (
        box(0, 0, 376, 147, "url(#train)")
        + path("M0 84 93 55l36 14 39-17 63 21 81-28 64 33v69H0Z", "#443b60")
        + path("M92 147 376 118m-187 29 187-19", stroke="#a18da7", line=2)
        + path("M132 111 332 68l44 16v32l-205 14q-36 1-39-19Z", "url(#cab)", "#cec0e3", ".8")
        + path("M137 111 344 77l32 11v7l-232 27Z", "#30244c")
        + path("M176 118 376 99", stroke="#ab6bf0", line="3")
        + circle(153, 119, 2.7, "#ffe9b4")
    )
    embedded = base64.b64encode(train_jpeg()).decode("ascii")
    return (fallback + f'<image x="0" y="0" width="376" height="147" href="{TRAIN_URI}{embedded}"/>'
            + '<rect width="376" height="147" fill="url(#train-tint)"/>')


def diagnostics_scene(card: Card) -> str:
    card.defs += [
        gradient("pc", ((0, "#091731"), (".6", "#14345e"), (1, "#121637")), axis=(0, 0, 1, 1)),
        gradient("wave", ((0, "#102a66"), (".52", "#235dd6"), (1, "#51bdff")), axis=(0, 1, 1, 0)),
        gradient("wave2", ((0, "#0f1b45"), (".66", "#153d9a"), (1, "#456cf3")), axis=(0, 1, 1, 0)),
        light("pcglow", "#337afa", ".6"),
    ]
    ribbons = (
        path("M113 150C147 107 174 52 223 43c45-9 60 4 92-16 23-14 44-15 71 2v35c-26-15-55-19-98 19"
             "s-91 29-117 67Z", "url(#wave2)", "#3f75cc", ".85")
        + path("M154 150c32-47 77-48 106-65 41-24 66-82 116-66v44c-38-19-57 22-91 49-20 16-68 12-88 38Z",
               "url(#wave)", "#6fafff", ".8")
        + path("M191 147c32-20 78-22 114-42 27-16 39-44 71-48v68c-74-17-40 28-132 29Z",
               "url(#wave2)", "#405dc5", ".7")
        + path("M253 151c27-32 68-20 91-56 9-14 20-27 37-28m-200 82c41-41 75-27 122-77 28-30 55-40 78-32",
               stroke="#639cff", line="1.05")
    )
    terminal = (
        box(22, 31, 128, 78, "#0a142a", "#5181b6", 8)
        + path("M23 46h126", stroke="#31476d")
        + circle(32, 39, 1.6, "#b988f0") + circle(39, 39, 1.6, "#5dbdff")
        + glyph("windows", 34, 62, 32, "#5dbdff")
        + path("M79 68h52m-52 10h33m-33 10h41", stroke="#557fb2", line=2)
    )
    return (box(0, 0, 376, 147, "url(#pc)")
            + '<ellipse cx="226" cy="64" rx="168" ry="108" fill="url(#pcglow)"/>'
            + ribbons + terminal)


def stack_pills(card: Card, stack, x, y, *, small=False) -> str:
    items = []
    for name in stack:
        size = 14.5 if small else 15
        width = round(text_width(name, size, 600) + 37, 2)
        items.extend((box(x, y, width, 26, "#1a1b2a", "#3b344b", 8),
                      technology(name, x + 7, y + 5, 16),
                      card.text(x + 28, y + 17.6, name, size, weight=600, fill=COPY)))
        x += width + 7
    return "".join(items)


def counts(card: Card, repo: dict, x, y) -> str:
    stars = f'{repo["stars"]:,}'
    return (
        glyph("star", x, y - 15, 18, COPY) + card.text(x + 24, y, stars, 16, weight=600)
        + glyph("branch", x + 40 + text_width(stars, 16, 600), y - 15, 18, COPY)
        + card.text(x + 64 + text_width(stars, 16, 600), y, f'{repo["forks"]:,}', 16, weight=600)
    )


def feature(name: str, index: int) -> Card:
    title, copy, stack = PROJECTS[name]
    evidence = PROJECT_EVIDENCE[name]
    card = Card(376, 356, title, f'{copy} {evidence}. {", ".join(stack)}. Opens the repository.')
    draw = (stadium_scene, train_scene, diagnostics_scene)[index]
    art_height, illustration = clip("art-height", box(0, 0, card.w, 147), draw(card))
    clipping, art = clip("cover", box(0, 0, card.w, card.h, radius=14), illustration)
    card.defs.extend((clipping, art_height))
    content = panel(0, 0, card.w, card.h, fill="url(#panel)") + art
    content += panel(0, 0, card.w, card.h, 14, fill="none")
    content += path("M.6 147h374.8", stroke=BORDER)
    title_size = min(24, 310 / text_width(title, 1, 600))
    content += card.text(19, 181, title, round(title_size, 2), weight=600, tracking="-.4")
    content += glyph("external", 337, 163, 19, VIOLET)
    lines = wrap(copy, size=19, width=336)
    if len(lines) > 3:
        raise ValueError("Featured description exceeds its card")
    for line, words in enumerate(lines):
        content += card.text(20, 210 + line * 23, words, 19, fill=COPY)
    content += card.text(20, 278, evidence, 17.5, weight=500, fill="#d5bdff")
    content += stack_pills(card, stack, 19, 289)
    content += path("M19 324h338", stroke=BORDER)
    content += card.text(20, 345, "View source", 16, weight=600, fill=VIOLET)
    content += glyph("arrow", 337, 330, 16)
    card.parts.append(group(content, motion="rise", delay=340 + index * 55))
    return card


def heading_card(key: str, *, compact=False) -> Card:
    title, note, symbol = HEADERS[key]
    w = 680 if compact else WIDTH
    card = Card(w, 52, title, note)
    card.styles.append("text{opacity:.98}")
    card.add_transparent_heading(card.heading(title, "" if compact else note, symbol, width=w))
    return card


def collaboration(index: int, status: str, *, compact=False) -> Card:
    title, copy = EXTERNAL_COPY[index]
    _, kind, number = CONTRIBUTIONS[index]
    label = ("Issue" if kind == "issue" else "PR") + f" #{number}"
    w, h = (680, 112) if compact else (WIDTH, 63)
    card = Card(w, h, f"{title}, {label}, {status}", copy)
    fill, fg = {
        "Merged": ("#15382f", "#a6e9c9"), "Open": ("#31234b", "#dec5ff"),
        "Closed": ("#3a293c", "#e4bae1"), "Draft": ("#292638", "#d8cce5"),
    }[status]
    card.parts.extend((
        panel(0, 0, w, h, 12), box(16, 12, 40, 38, "#1b1c2c", BORDER, 8),
        glyph("chat" if kind == "issue" else "merge", 25, 20, 22),
        card.text(73, 28 if not compact else 34, title, 18 if not compact else 22, weight=600, fill="#d5bdff"),
        card.text(73, 49 if not compact else 61, copy, 15 if not compact else 19, fill=COPY),
        box(w - 269, 17 if not compact else 76, 96, 28, fill, radius=9),
        card.text(w - 221, 36 if not compact else 95, status, 15, weight=600, fill=fg, anchor="middle"),
        card.text(w - 50, 36 if not compact else 96, label, 16, weight=600, anchor="end"),
        glyph("arrow", w - 39, 22 if not compact else 82, 18),
    ))
    return card


def building(label: str, symbol: str, repo: dict) -> Card:
    stamp = dt.date.fromisoformat(repo["pushed_at"][:10])
    card = Card(376, 61, label, f"Last publicly pushed {stamp.isoformat()} UTC. Opens the repository.")
    card.parts.extend((
        panel(0, 0, card.w, card.h, 11),
        glyph(symbol, 16, 16, 28), card.text(57, 29, label, 18, weight=600),
        card.text(58, 48, f"Updated {stamp:%d %b %Y}", 13, fill=MUTED),
        glyph("arrow", 338, 20, 20),
    ))
    return card


def pin(name: str, copy: str) -> Card:
    title, _, stack = PROJECTS[name]
    card = Card(571, 138, title, f'Public repository. {copy} {", ".join(stack)}. Opens the repository.')
    card.parts.extend((
        panel(0, 0, card.w, card.h, 13), glyph("repo", 17, 14, 24),
        card.text(51, 34, title, 24, weight=600, fill="#d4bbff", tracking="-.25"),
        glyph("arrow", 534, 16, 19),
        card.text(19, 67, copy, 19, fill=COPY),
        stack_pills(card, stack, 19, 86, small=True),
        card.text(551, 126, "View source", 16, weight=600, fill=VIOLET, anchor="end"),
    ))
    return card


def technology_cards(evidence: dict) -> dict[str, Card]:
    return {name + suffix: tech_grid(evidence, tools=name == "tools", compact=bool(suffix))
            for name in ("technical", "tools") for suffix in ("", "-mobile")}


def artworks(stats: dict, public: dict, technology_evidence: dict | None) -> dict[str, Card]:
    repos = public["repositories"]
    files = {
        "link-profile": button("Profile links", "profile"),
        "link-portfolio": button("Portfolio", "external", primary=True,
                                 unpublished=not bool(PORTFOLIO_SITE_URL)),
    }
    if technology_evidence is not None:
        files.update(technology_cards(technology_evidence))
    for compact in (False, True):
        suffix = "-mobile" if compact else ""
        files["hero" + suffix] = hero(compact=compact)
        files["metrics" + suffix] = metrics(stats, public, compact=compact)
        files["calendar" + suffix] = contribution_calendar(stats, compact=compact)
        for key in HEADERS:
            files["heading-" + key + suffix] = heading_card(key, compact=compact)
        for index, record in enumerate(CONTRIBUTIONS):
            url = contribution_url(record)
            files[f"contribution-{record[2]}{suffix}"] = collaboration(
                index, public["contributions"][url], compact=compact)
    for index, name in enumerate(tuple(PROJECTS)[:3]):
        files["project-" + name.lower()] = feature(name, index)
    for name, label, symbol in CURRENT:
        files["building-" + name.lower()] = building(label, symbol, repos[name])
    for name, copy in PINS:
        files["pin-" + name.lower()] = pin(name, copy)
    return files


def dynamic(name: str) -> bool:
    return name.startswith(("metrics", "calendar", "contribution-", "building-", "technical", "tools"))


def link(url: str, label: str) -> str:
    return f'<a href="{esc(url)}">{label}</a>'


def image(name: str, alt: str, width: int = 780, *, mobile=False, href="", local=None, live=True) -> str:
    def src(key: str) -> str:
        if local is not None:
            return esc(local[key])
        base = LIVE if live and dynamic(key) else "./cards/"
        return esc(base + key + ".svg")

    tag = f'<img src="{src(name)}" width="{width}" alt="{esc(alt)}">'
    if mobile:
        tag = f'<picture><source media="(max-width: 680px)" srcset="{src(name + "-mobile")}">{tag}</picture>'
    return link(href, tag) if href else tag


def profile_markup(*, local: dict[str, str] | None = None, technology_evidence: dict | None = None,
                   live_technology: bool = False) -> str:
    # Never silently publish an insecure or malformed portfolio URL.
    if PORTFOLIO_SITE_URL:
        target = urlsplit(PORTFOLIO_SITE_URL)
        if (target.scheme != "https" or not target.netloc or
                target.username or target.password or any(c.isspace() for c in PORTFOLIO_SITE_URL)):
            raise ValueError("PORTFOLIO_SITE_URL must be an absolute HTTPS URL")
    if technology_evidence is None:
        technology_evidence = validate_technology(read_json(TECHNOLOGY_SEED))
    def img(*args, **kwargs):
        return image(*args, **kwargs, local=local)

    def social_badge(name: str, label: str, destination: str = "") -> str:
        alt = label + (" — official profile" if destination else " — website not launched yet")
        return img("link-" + name, alt, 150, href=destination)

    def block(content, css="wide"):
        return f'<p align="center" class="{css}">\n{content}\n</p>'

    def span(content, css):
        return f'<span class="{css}">\n{content}\n</span>'

    def section(key, content, layout, extra=""):
        header = img("heading-" + key, HEADERS[key][0], mobile=True)
        body = span(header, "wide heading") + "<br>\n" + span(content, layout)
        return block(body + extra, "section-group")

    def repo_url(name: str) -> str:
        return f"{PROFILE}/{name}"

    feature_cards = []
    for name, (title, copy, _) in tuple(PROJECTS.items())[:3]:
        feature_cards.append(img(f"project-{name.lower()}", f"{title}. {copy} {PROJECT_EVIDENCE[name]}. View source.",
                                 255, href=repo_url(name)))

    highlights = []
    for index, record in enumerate(CONTRIBUTIONS):
        title, copy = EXTERNAL_COPY[index]
        highlights.append(img(f"contribution-{record[2]}", f"{title} #{record[2]}. {copy}",
                              mobile=True, href=contribution_url(record)))

    tiles = [img(f"building-{name.lower()}", f"{label}. Public GitHub repository.", 255,
                 href=repo_url(name)) for name, label, _ in CURRENT]
    pins = [img(f"pin-{name.lower()}", f"{name}. {copy}", 386, href=repo_url(name))
            for name, copy in PINS]
    archive = ("./PROFILE-V5.md" if local is None else
               f"{PROFILE}/{OWNER}/blob/e5cc7ba352f13c55b4ccb8d11008bce1afbcd0e3/README.md")
    docs = "./docs/DASHBOARD.md" if local is None else "DASHBOARD.md"
    live_json = f"{PROFILE}/{OWNER}/blob/profile-live/cards/contributions.json"
    evidence_json = (f"{PROFILE}/{OWNER}/blob/profile-live/cards/technology.json" if live_technology
                     else "./data/dashboard-technology.json")
    evidence_link = link(evidence_json, "Technology evidence snapshot") + " · " if local is None else ""
    portfolio_report = f"{PROFILE}/{OWNER}/blob/profile-live/live/portfolio.md"
    language_report = portfolio_report + "#programming-languages"
    language_image = f"https://raw.githubusercontent.com/{OWNER}/{OWNER}/profile-live/live/portfolio-language-share.svg"
    language_body = ""
    if live_technology and local is None:
        language_body = f'<p align="center">{link(language_report, f\'<img src="{language_image}" width="510" alt="Language shares of GitHub Linguist detected bytes. Open the linked table for exact values.">\')}</p>\n'
    language_details = ("<details>\n<summary>Language distribution (%)</summary>\n" + language_body
                        + f'<p>{link(language_report, "View code-byte breakdown ↗")}</p>\n</details>')
    external_prs = "https://github.com/search?" + urlencode({
        "q": f"is:pr is:public author:{OWNER} -user:{OWNER}", "type": "pullrequests", "s": "updated", "o": "desc"})
    external_issues = "https://github.com/search?" + urlencode({
        "q": f"is:issue is:public author:{OWNER} -user:{OWNER}", "type": "issues", "s": "updated", "o": "desc"})
    more_contributions = ("<details>\n<summary>More contributions</summary>\n"
                          + f'<p>{link(external_prs, "All authored public external pull requests ↗")} · '
                          + f'{link(external_issues, "All authored public external issues ↗")} · '
                          + f'{link(portfolio_report + "#verified-external-contributions", "Verified merged PR inventory ↗")}</p>\n</details>')
    more_projects = f'{PROFILE}?tab=repositories&type=source&sort=updated'
    hero_description = ". ".join((HERO_HEADLINE, *HERO_SUBHEADLINES)) + "."
    readme_text = f"""<details>
<summary><h3>Profile text and data sources</h3></summary>
<p><strong>{esc(HERO_NAME)}</strong> · {esc(hero_description)}</p>
<ul>
<li>{link(repo_url("morocco2030"), "Morocco2030")}. Independent academic portal for multilingual tournament information and role-based staff workflows. {link(repo_url("morocco2030") + "/releases", "Releases")} · {link(repo_url("morocco2030") + "/actions/workflows/ci.yml", "CI")}</li>
<li>{link(repo_url("ab-train-ticket-studio"), "AB Train Ticket Studio")}. Independent booking simulation with sample tickets. {link(DEMO, "Live demo")}</li>
<li>{link(repo_url("PC-Full-Check"), "PC Full Check")}. Read-only Windows diagnostics and local reports. {link(repo_url("PC-Full-Check") + "/tree/main/tests", "Tests")}</li>
<li>{link(repo_url("violetgate"), "VioletGate")}. Authentication UI demo. {link(f"https://{OWNER}.github.io/violetgate/", "Live demo")} · {link(repo_url("ayman-calc"), "Ayman Calc")}. Browser calculator. {link(f"https://{OWNER}.github.io/ayman-calc/", "Live demo")}</li>
</ul>
<p>GitHub GraphQL supplies the {link(live_json, "daily counts")}. GitHub REST supplies repository totals and the {link("https://github.com/search?" + urlencode({"q": MERGED_SEARCH, "type": "pullrequests"}), "merged public PR search")}. {link(PROFILE, "GitHub’s native contribution graph")} shows current activity.</p>
<p>{link(docs, "Technical evidence and refresh setup")} · {evidence_link}{link(archive, "Original artwork and previous profile links")}</p>
<p><sub>© 2026 Ayman Bounaouj. Original AB branding. All rights reserved.</sub></p>
</details>"""
    social_first = "\n".join((
        social_badge("profile", "Profile links", PROFILE_LINKS_URL),
        social_badge("portfolio", "Portfolio", PORTFOLIO_SITE_URL),
    ))
    identity = img("hero", f"{HERO_NAME}. {hero_description}", mobile=True)
    tech_alt = "Languages & Technical Stack."
    tools_alt = "Frameworks / Build Tools."
    if live_technology:
        tech_alt += " See technology evidence in the profile data sources."
        tools_alt += " See technology evidence in the profile data sources."
    else:
        tech_alt += " " + ", ".join(name for name, _ in grid_items(technology_evidence))
        tools_alt += " " + ", ".join(name for name, _ in grid_items(technology_evidence, tools=True))
    return "\n\n".join((
        block(span(identity, "wide hero"), "section-group"),
        block(social_first, "social-row"),
        block(img("metrics", "Verified GitHub metrics. Yearly contributions, current streak, merged public pull requests and active days.",
                  mobile=True, href=SOURCE)),
        # Use the same verified snapshot as the metrics after the release switch.
        block(img("calendar", "Violet GitHub contribution calendar with weekday and month labels and intensity legend.",
                  mobile=True, href=PROFILE, live=live_technology)),
        block(img("technical", tech_alt.strip(), mobile=True, live=live_technology)),
        language_details,
        block(img("tools", tools_alt.strip(), mobile=True, live=live_technology)),
        section("featured", "\n".join(feature_cards), "project-row",
                "<br>\n" + span(f"<sub>{link(DEMO, 'AB Train Ticket Studio live demo ↗')}</sub>", "demo")),
        section("opensource", "<br>\n".join(highlights), "wide contributions"),
        more_contributions,
        section("building", "\n".join(tiles), "building-row"),
        section("pinned", "\n".join(pins), "pin-row",
                "<br>\n" + span(f"<sub>{link(more_projects, 'More projects ↗')}</sub>", "demo")),
        readme_text,
    )) + "\n"


README_MARKER = "<!-- Generated by scripts/render_svg_cards.py --write-readme -->\n\n"
LIVE_README_MARKER = "<!-- Generated by scripts/render_svg_cards.py --write-readme --live-technology -->\n\n"
PREVIEW_STYLE = """
*{box-sizing:border-box}
html{color-scheme:dark;background:#0b0d15}
body{margin:0;color:#e9e5ef;font:15px/1.55 system-ui,sans-serif}
main{max-width:1184px;margin:auto;padding:12px}
p{margin:0 0 12px}
img{vertical-align:bottom;max-width:100%;height:auto}
.wide img{width:100%}
a{color:#c9a3ff;text-underline-offset:.19em}
a:focus-visible,summary:focus-visible{outline:2px solid #c99fff;outline-offset:4px;border-radius:4px}
.section-group > br{display:none}
.hero{display:block;margin:0 0 7px}
.social-row{text-align:center;margin-bottom:5px}
.social-row a{display:inline-block;vertical-align:middle;margin:0 2px}
.social-row img{width:150px;max-width:45vw;height:auto}
.social-row > img{display:inline-block;vertical-align:middle;margin:0 2px}
.heading{display:block;margin:0 0 5px}
.project-row,.building-row,.pin-row{display:grid;gap:10px}
.project-row,.building-row{grid-template-columns:repeat(3,minmax(0,1fr))}
.pin-row{grid-template-columns:repeat(2,minmax(0,1fr))}
.pin-row br,.contributions br{display:none}
.project-row img,.building-row img,.pin-row img{width:100%}
.project-row{margin:0 0 3px}
.demo{display:block}
.demo sub{font-size:.8em;vertical-align:baseline}
.contributions a{display:block;margin-bottom:5px}
.contributions a:last-child{margin:0}
details{font-size:.84em;color:#bbb4c8;padding:0 6px 8px}
summary{width:fit-content;cursor:pointer}
summary h3{display:inline;margin:0;font-size:1.25rem;font-weight:600}
details p,details ul{margin:7px 0}
@media (max-width:680px){
  main{padding:9px}
  p{margin-bottom:10px}
  .project-row,.pin-row{grid-template-columns:minmax(0,1fr)}
  .building-row{grid-template-columns:minmax(0,1fr)}
  .project-row,.pin-row,.building-row{gap:7px}
}
"""


def preview_markup(svg: dict[str, str], technology_evidence: dict) -> str:
    sources = {name.removesuffix(".svg"): "data:image/svg+xml;base64,"
               + base64.b64encode(xml.encode("utf-8")).decode("ascii") for name, xml in svg.items()}
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            '<meta name="color-scheme" content="dark">\n'
            '<title>Ayman Bounaouj | GitHub profile preview</title>\n'
            f'<style>{PREVIEW_STYLE}</style>\n</head>\n<body>\n<main>\n'
            + profile_markup(local=sources, technology_evidence=technology_evidence) + '</main>\n</body>\n</html>\n')


def verify_svg(xml: str, name: str, static: bool) -> None:
    allowed = {"svg", "title", "desc", "defs", "style", "g", "path", "rect", "circle",
               "ellipse", "linearGradient", "radialGradient", "stop", "clipPath", "text", "image"}
    size_limit = 1_000_000 if name in {"technical", "technical-mobile", "tools", "tools-mobile"} else 140_000
    if (len(xml.encode("utf-8")) > size_limit or re.search(r"<[!?]|@import|javascript:|data:text/", xml, re.I)
            or (static and ("@keyframes" in xml or "animation:" in xml))
            or (not static and "@media (prefers-reduced-motion: reduce)" not in xml)):
        raise ValueError(f"{name}: SVG size, motion or safety validation failed")
    root = ET.fromstring(xml)
    if (root.tag != f"{{{SVG_NS}}}svg" or root.get("role") != "img"
            or not root.findtext(f"{{{SVG_NS}}}title") or not root.findtext(f"{{{SVG_NS}}}desc")):
        raise ValueError(f"{name}: missing SVG accessibility metadata")
    for node in root.iter():
        prefix, _, tag = node.tag.rpartition("}")
        if prefix != "{" + SVG_NS or tag not in allowed:
            raise ValueError(f"{name}: unexpected SVG element")
        for attr, value in node.attrib.items():
            if attr == "href" and tag == "image":
                expected_digest = (TRAIN_SHA256 if name == "project-ab-train-ticket-studio" else
                                   HERO_BG_SHA256 if name in ("hero", "hero-mobile") else None)
                if (expected_digest is not None and value.startswith(TRAIN_URI)
                        and hashlib.sha256(base64.b64decode(value[len(TRAIN_URI):], validate=True)).hexdigest()
                        == expected_digest):
                    continue
            if (attr.lower().startswith(("on", "{")) or attr in {"src", "href"}
                    or re.search(r"(?:https?://|data:|//)", value)):
                raise ValueError(f"{name}: unexpected SVG URL or event handler")
    for url in re.findall(r"url\(([^)]*)\)", xml):
        if not re.fullmatch(r"#[a-zA-Z0-9_-]+|" + re.escape(FONT_URI) + r"[A-Za-z0-9+/=]+", url):
            raise ValueError(f"{name}: unexpected CSS URL")


@lru_cache(maxsize=256)
def uncompressed_font_digest(encoded: str) -> str:
    """Compare the actual WOFF tables independently of the platform's zlib encoder."""
    raw = base64.b64decode(encoded, validate=True)
    if (not 44 <= len(raw) <= 32_768 or raw[:4] != b"wOFF"
            or struct.unpack_from(">I", raw, 8)[0] != len(raw)
            or struct.unpack_from(">I", raw, 16)[0] > 65_536 or any(raw[24:44])):
        raise ValueError("Unexpected WOFF font container")
    digest = hashlib.sha256(raw[4:8] + raw[20:24])  # Flavor and version.
    try:
        with TTFont(io.BytesIO(raw), checkChecksums=2, lazy=True) as font:
            for tag, entry in sorted(font.reader.tables.items()):
                if entry.origLength > 65_536:
                    raise ValueError("Oversized WOFF table")
                table = font.reader[tag]
                digest.update(tag.encode("ascii") + len(table).to_bytes(4, "big") + table)
    except (AssertionError, TTLibError, struct.error) as exc:
        raise ValueError("Invalid WOFF table") from exc
    return digest.hexdigest()


def same_svg(actual: str, expected: str) -> bool:
    if actual == expected:
        return True

    def normalize(xml: str) -> str:
        return FONT_DATA.sub(lambda match: FONT_URI + uncompressed_font_digest(match[1]), xml)

    return normalize(actual) == normalize(expected)


def verify_readme(path: Path = ROOT / "README.md") -> None:
    actual = path.read_text(encoding="utf-8")
    live = actual.startswith(LIVE_README_MARKER)
    if actual != (LIVE_README_MARKER if live else README_MARKER) + profile_markup(live_technology=live):
        raise ValueError("README does not match the generated dashboard markup")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calendar", type=Path, default=ROOT / "data/dashboard-contributions.json")
    parser.add_argument("--public", type=Path, default=ROOT / "data/dashboard-public.json")
    parser.add_argument("--technology", type=Path, default=TECHNOLOGY_SEED)
    parser.add_argument("--output", type=Path, default=ROOT / "cards")
    parser.add_argument("--preview", type=Path, help="write a self-contained offline HTML preview")
    parser.add_argument("--write-readme", action="store_true", help="regenerate README.md from the layout")
    parser.add_argument("--live-technology", action="store_true", help="use published calendar and technology grids in README assembly")
    parser.add_argument("--verify", action="store_true", help="compare generated artwork to existing files")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--dynamic-only", action="store_true", help="render all published live data cards")
    selection.add_argument("--activity-only", action="store_true", help="render live metrics, calendar and activity cards")
    selection.add_argument("--technology-only", action="store_true", help="render the four technology cards independently")
    parser.add_argument("--require-fresh", action="store_true", help="enforce the 36-hour publication window")
    args = parser.parse_args()
    partial = args.dynamic_only or args.activity_only or args.technology_only
    if (partial and args.preview) or (args.verify and (args.preview or args.write_readme)):
        parser.error("Preview and README generation require a full render")
    static = os.getenv("STATIC") == "1"
    if args.write_readme and (static or partial):
        parser.error("README assembly requires the regular animated render")
    if args.live_technology and not args.write_readme:
        parser.error("--live-technology requires --write-readme")
    try:
        technology_evidence = None if args.activity_only else validate_technology(read_json(args.technology))
        if args.technology_only:
            cards = technology_cards(technology_evidence)
        else:
            stats = activity(read_json(args.calendar), fresh=args.require_fresh)
            public = read_json(args.public)
            validate(public, fresh=args.require_fresh)
            cards = artworks(stats, public, technology_evidence)
        svg = {}
        for name, card in cards.items():
            if (args.dynamic_only or args.activity_only) and not dynamic(name):
                continue
            value = card.svg(static)
            verify_svg(value, name, static)
            svg[name + ".svg"] = value
        if args.verify:
            for name, value in svg.items():
                actual = (args.output / name).read_text(encoding="utf-8")
                verify_svg(actual, name.removesuffix(".svg"), static)
                if not same_svg(actual, value):
                    raise ValueError(f"{name}: generated SVG does not match verified data")
        else:
            args.output.mkdir(parents=True, exist_ok=True)
            for name, value in svg.items():
                (args.output / name).write_text(value, encoding="utf-8", newline="\n")
        if args.write_readme:
            readme = ROOT / "README.md"
            live = args.live_technology or (readme.exists()
                                            and readme.read_text(encoding="utf-8").startswith(LIVE_README_MARKER))
            marker = LIVE_README_MARKER if live else README_MARKER
            readme.write_text(marker + profile_markup(technology_evidence=technology_evidence, live_technology=live),
                              encoding="utf-8", newline="\n")
        if args.preview:
            args.preview.parent.mkdir(parents=True, exist_ok=True)
            args.preview.write_text(preview_markup(svg, technology_evidence), encoding="utf-8", newline="\n")
    except (KeyError, OSError, ValueError, ET.ParseError) as exc:
        parser.exit(1, f"Dashboard validation failed: {exc}\n")
    print(f"PASS: {len(svg)} {'static' if static else 'animated'} SVG cards verified")


if __name__ == "__main__":
    main()
