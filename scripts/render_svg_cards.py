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
import os
import re
import struct
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

from fontTools import subset
from fontTools.pens.boundsPen import BoundsPen
from fontTools.svgLib.path import parse_path
from fontTools.ttLib import TTFont, TTLibError

from brand_paths import PURPLE, WHITE
from dashboard_data import (
    CONTRIBUTIONS, MERGED_SEARCH, OWNER, ROOT, activity, contribution_url, read_json, validate,
)

WIDTH = 1160
ASSETS = ROOT / "assets/dashboard"
PROFILE = f"https://github.com/{OWNER}"
LIVE = f"https://raw.githubusercontent.com/{OWNER}/{OWNER}/profile-live/cards/"
SOURCE = f"{PROFILE}/{OWNER}/tree/profile-live/cards"
PORTFOLIO = "https://beacons.ai/aymanbounaouj"
LINKEDIN = "https://www.linkedin.com/in/aymanbounaouj/"
DEMO = f"https://{OWNER}.github.io/ab-train-ticket-studio/"

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

FONT_FILES = {
    400: "Poppins-Regular.ttf",
    500: "Poppins-Medium.ttf",
    600: "Poppins-SemiBold.ttf",
}
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
    "chat": "M4 4h16v13H9l-5 4zm4 5h8m-8 4h5",
    "windows": "M2 5l9-1.6v8H2Zm11-2 9-1.6v10h-9ZM2 13h9v8l-9-1.6Zm11 0h9v10l-9-1.6Z",
}

PROJECTS = {
    "morocco2030": (
        "Morocco2030",
        "Multilingual tournament portal with competition, editorial and staff workflows.",
        ("Laravel", "PHP", "MySQL"),
    ),
    "ab-train-ticket-studio": (
        "AB Train Ticket Studio",
        "Multilingual rail-booking simulation with seat selection, QR tickets and PDF export.",
        ("JavaScript", "Vite", "Playwright"),
    ),
    "PC-Full-Check": (
        "PC Full Check",
        "Read-only Windows diagnostics with privacy controls and local system reports.",
        ("PowerShell", "Windows"),
    ),
    "violetgate": (
        "VioletGate",
        "Responsive authentication UI demo.",
        ("HTML", "CSS", "JavaScript"),
    ),
}
PINS = (
    ("morocco2030", "Tournament portal and staff operations."),
    ("ab-train-ticket-studio", "Rail-booking simulation and sample tickets."),
    ("PC-Full-Check", "Read-only Windows diagnostic reports."),
    ("violetgate", PROJECTS["violetgate"][1]),
)
CURRENT = (
    (OWNER, "Profile automation", "code"),
    ("Understand-Anything", "Understand-Anything", "branch"),
    ("gestion-vaccination", "Gestion Vaccination", "stack"),
)
STACK = ("PHP", "JavaScript", "TypeScript", "Python", "HTML", "CSS",
         "MySQL", "Laravel", "React", "Docker", "Playwright", "Tailwind CSS")
TOOLS = (
    ("Laravel", "Web framework"), ("Vite", "Build tool"), ("Node.js", "JS runtime"),
    ("Composer", "PHP packages"), ("pnpm", "JS packages"), ("Docker", "CI services"),
    ("GitHub Actions", "CI and delivery"),
)
# Optical maximums for the visible paths, in SVG units. Wide and outline marks
# need more room than filled squares to read as part of the same set.
GRID_MARK_SIZES = {
    "PHP": (48, 30), "JavaScript": (35, 35), "TypeScript": (35, 35),
    "Python": (39, 37), "HTML": (34, 38), "CSS": (34, 38),
    "MySQL": (43, 37), "Laravel": (42, 41), "React": (43, 40),
    "Docker": (45, 35), "Playwright": (42, 34), "Tailwind CSS": (44, 32),
    "Vite": (39, 39), "Node.js": (38, 40), "Composer": (39, 42),
    "pnpm": (33, 33), "GitHub Actions": (37, 37),
}
EXTERNAL_COPY = (
    ("Egonex-AI / Understand-Anything", "Apply dashboard filters to the structural code graph."),
    ("OWASP / Cheat Sheet Series", "Contributed to the cheat-sheet revision discussion."),
    ("php / doc-en", "Clarify the distinction between Error and Exception."),
)
HEADERS = {
    "featured": ("Featured Projects", "Selected public software", "rocket"),
    "opensource": ("Open Source & Verified Contributions", "Upstream GitHub work", "branch"),
    "building": ("Currently Building", "Recently updated public work", "target"),
    "pinned": ("Pinned Repositories", "Public source and repository totals", "pin"),
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
    return sum(widths[ord(c)] for c in value) * size / units


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
    mark = legacy["PowerShell"]
    icons["PowerShell"] = {"viewBox": mark["viewBox"], "paths": [{"d": mark["path"], "fill": mark["color"]}]}
    return icons


def icon_paths(icon: dict) -> str:
    return "".join(f'<path d="{esc(p["d"])}" fill="{esc(p["fill"])}"/>' for p in icon["paths"])


def technology(name: str, x: float, y: float, size: float) -> str:
    if name == "Windows":
        return glyph("windows", x, y, size, "#5dbdff")
    icon = brand_icons()[name]
    return group(icon_paths(icon), f'translate({x} {y}) scale({size / icon["viewBox"]:.5f})')


@lru_cache
def grid_mark(name: str) -> tuple[str, tuple[float, float, float, float]]:
    icon = icon_registry()["grid_icons"].get(name) or brand_icons()[name]
    pen = BoundsPen(None)
    for item in icon["paths"]:
        parse_path(item["d"], pen)
    return icon_paths(icon), pen.bounds


def centered_mark(name: str, cx: float, cy: float, *, width: int, height: int) -> str:
    art, (left, top, right, bottom) = grid_mark(name)
    optical_w, optical_h = GRID_MARK_SIZES[name]
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
        self.glyphs.setdefault(weight, set()).update(value)
        return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}"'
                f' text-anchor="{anchor}" letter-spacing="{tracking}">{esc(value)}</text>')

    def heading(self, title, note, symbol, *, x=0, y=0, width=WIDTH) -> str:
        return (glyph(symbol, x + 8, y + 10, 28)
                + self.text(x + 52, y + 34, title, 27, weight=600, tracking="-.55")
                + self.text(x + width - 8, y + 33, note, 16, fill=MUTED, anchor="end"))

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


def laptop() -> str:
    bezel = path("M47 42 263 5q6-1 5 6l-28 177H14L40 51q1-8 7-9Z",
                 "url(#bezel)", "#a28ac3", 1.7)
    display = path("M49 51 256 15 230 177H25Z", "url(#display)", "#27283f", 1.5)
    editor = path("M48 53 79 48 58 173H28Z", "#171829")
    editor += path("M50 63 252 31M65 173 87 50", stroke="#45435c", line=1)
    for index, color in enumerate(("#fa81cc", "#9670ec", "#50cbb8")):
        editor += circle(53 + 6 * index, 56 - index, 1.6, color)
    code = (
        (6, 39, "#bd8dff"), (13, 73, "#7a83e9"), (13, 54, "#71dac1"),
        (22, 94, "#ffd18c"), (22, 61, "#ed9cd7"), (13, 35, "#6bbce5"),
        (6, 58, "#bd8dff"), (15, 94, "#71dac1"), (20, 77, "#9a88f8"),
        (22, 34, "#ffd18c"), (13, 55, "#7193e9"), (6, 22, "#bd8dff"),
    )
    for index, (indent, length, color) in enumerate(code):
        x, y = 91 - index * 1.76 + indent, 63 + index * 8.35
        editor += box(62 - index * 1.42, y + 1, 4, 1, "#5a5b76", radius=.5)
        editor += path(f"M{x:.1f} {y:.1f}l{length * .54:.1f} {-length * .054:.1f}",
                       stroke=color, line=2.3)
        if length > 40:
            editor += path(f"M{x + length * .6:.1f} {y - length * .06:.1f}l{length * .35:.1f} {-length * .035:.1f}",
                           stroke="#8a7f9f", line=1.5)
    lower = (
        path("M14 186h226l39 10q6 2 1 5-7 4-23 4H-14q-18 0-19-6l47-13Z", "url(#metal)", "#6d608b")
        + path("M-28 199h307q-9 7-38 7H-7q-13-1-21-7Z", "#090a19")
        + path("M100 192h64l-6 4h-50Z", "#080915")
        + path("M15 188h225", stroke="#d4b9fa", line=1)
        + path("M252 198h15", stroke="#a596c5", line=1)
    )
    return (
        '<ellipse cx="128" cy="201" rx="185" ry="24" fill="url(#screenlight)"/>'
        + bezel + display + editor + lower
    )


def hero(*, compact=False) -> Card:
    w, h = (680, 234) if compact else (WIDTH, 235)
    card = Card(w, h, "Ayman Bounaouj | Full-Stack Web Developer",
                "Original AB monogram in white and violet beside an illustrated coding laptop.")
    card.defs += [
        gradient("hero", ((0, "#17122b"), (".57", "#0d101d"), (1, "#191133")), axis=(0, 0, 1, 1)),
        gradient("ribbon", ((0, "#21123c"), (".58", "#181633"), (1, "#392061")), axis=(0, 1, 1, 0)),
        gradient("bezel", ((0, "#29253b"), (".6", "#121122"), (1, "#3e2861")), axis=(0, 0, 1, 1)),
        gradient("display", ((0, "#0d1521"), (".67", "#14152a"), (1, "#331755")), axis=(0, 0, 1, 1)),
        gradient("metal", ((0, "#444060"), (".54", "#816da2"), (1, "#211c3a"))),
        light("screenlight", "#954bff", ".49"),
        light("atmosphere", "#6e33f8", ".46"),
    ]
    backdrop = (box(0, 0, w, h, "url(#hero)")
                + f'<ellipse cx="{w - 92}" cy="122" rx="350" ry="173" fill="url(#atmosphere)"/>'
                + '<ellipse cx="72" cy="201" rx="208" ry="87" fill="url(#screenlight)" opacity=".62"/>'
                + path(f"M0 184C155 122 180 246 355 200C515 155 {w-360} 232 {w-240} 169"
                       f"C{w-95} 95 {w-70} 181 {w} 106V{h}H0Z", "url(#ribbon)")
                + path(f"M0 211C123 163 159 251 336 213C521 175 {w-321} 249 {w-172} 178"
                       f"Q{w-49} 124 {w} 139", stroke="#7a47cb", line=".75")
                + path(f"M{w-150} 0l150 150m-109-150 109 109", stroke="#7540b2", line=".65"))
    art = group(laptop(), "translate(864 18) scale(.96)") if not compact else (
        '<g opacity=".41">' + group(laptop(), "translate(532 95) scale(.53)") + "</g>"
    )
    edge, inside = clip("hero-crop", box(0, 0, w, h, radius=20), backdrop + art)
    card.defs.append(edge)
    card.parts.extend((inside, panel(0, 0, w, h, 20, fill="none", stroke="#564574")))
    if compact:
        mark = logo(31, 44, 122) + path("M183 41v151", stroke="#645478", line=1.1)
        copy = (card.text(212, 91, "Ayman Bounaouj", 46, weight=600, tracking="-1.5")
                + card.text(213, 137, "Full-Stack Web Developer", 29, weight=600, fill=VIOLET)
                + card.text(214, 171, "Building practical, secure and", 21, fill=COPY)
                + card.text(214, 199, "scalable digital products.", 21, fill=COPY))
    else:
        mark = logo(73, 67, 140) + path("M248 43v151", stroke="#645478", line=1.15)
        copy = (card.text(288, 95, "Ayman Bounaouj", 55, weight=600, tracking="-1.6")
                + card.text(289, 145, "Full-Stack Web Developer", 36, weight=600, fill=VIOLET, tracking="-.7")
                + card.text(290, 183, "Building practical, secure and scalable digital products.", 21, fill=COPY))
    card.parts.extend((group(mark, motion="glint", delay=80), group(copy, motion="rise")))
    return card


def button(label, symbol, *, primary=False) -> Card:
    w, h = 182, 50
    card = Card(w, h, label, "Opens " + label + " in the linked public profile.")
    ink = "#f9f4ff" if primary else COPY
    card.defs.append(gradient("action", ((0, "#47247c"), (1, "#66349e")), axis=(0, 0, 1, 1)))
    card.parts.append(panel(0, 0, w, h, 12, fill="url(#action)" if primary else "url(#panel)",
                            stroke="#8356bd" if primary else BORDER))
    card.parts.append(glyph(symbol, 13, 15, 20, ink))
    card.parts.append(card.text(43, 31, label, 17, weight=600, fill=ink))
    card.parts.append(glyph("arrow", 151, 17, 16, "#dec6fa" if primary else MUTED))
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
    w, h = (680, 254) if compact else (WIDTH, 233)
    left, top = (64, 96) if compact else (98, 77)
    step = (w - left - 35) / columns
    card = Card(w, h, "Contribution Activity",
                f'{stats["total"]:,} GitHub contributions from {start} to {end}, UTC. '
                "Sunday to Saturday. Violet intensities represent 0, 1 to 3, 4 to 7, 8 to 15 and 16 or more.")
    date_line = f'{stats["total"]:,} contributions  |  {start:%d %b %Y} to {end:%d %b %Y}'
    card.parts.extend((
        panel(0, 0, w, h, 17),
        card.heading("Contribution Activity", "" if compact else date_line, "grid", x=13, y=3, width=w - 26),
    ))
    if compact:
        card.parts.append(card.text(25, 61, date_line, 18, fill=COPY))
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

    shelf = top + 102
    card.parts.append(path(f"M24 {shelf}h{w - 48}", stroke=BORDER))
    card.parts.append(card.text(27, shelf + 31, "Monthly totals", 15, fill=COPY))
    peak = max((n for _, n in stats["months"]), default=0)
    for index, (month, n) in enumerate(stats["months"]):
        x = 163 + index * (19 if compact else 48)
        bw = 15 if compact else 36
        bar = 3 + round(n / max(peak, 1) * 22)
        detail = box(x, shelf + 11, bw, 26, "#242237", radius=3)
        if n:
            detail += group(box(x, shelf + 37 - bar, bw, bar, "#9561d9", radius=3),
                            motion="grow", delay=300 + index * 34)
        card.parts.append(f'<g><title>{month}: {n} contributions</title>{detail}</g>')
    legend = w - (241 if compact else 278)
    card.parts.append(card.text(legend, shelf + 31, "Less", 15, fill=COPY))
    for index, fill in enumerate(HEAT):
        card.parts.append(box(legend + 45 + index * 24, shelf + 19, 18, 14, fill, radius=3))
    card.parts.append(card.text(legend + 212, shelf + 31, "More", 15, fill=COPY, anchor="end"))
    return card


def tech_grid(*, tools=False, compact=False) -> Card:
    title, note, symbol = (("Frameworks / Build Tools", "Frameworks, build and delivery", "tools") if tools
                           else ("Languages & Technical Stack", "Evidence from public work", "stack"))
    items = TOOLS if tools else [(name, "") for name in STACK]
    cols = (2 if tools else 3) if compact else (7 if tools else 6)
    w = 680 if compact else WIDTH
    h = (82 if tools else 62) if compact else (76 if tools else 55)
    rows = (len(items) + cols - 1) // cols
    inset = 10
    top = 54 if compact else 46
    gap = 14 if compact or not tools else 12
    available = w - 2 * inset - (cols - 1) * gap
    extra = (14, 0, 0, 0, 0, 0, 32) if tools and not compact else (0,) * cols
    widths = [(available - sum(extra)) / cols + n for n in extra]
    card = Card(w, top + rows * h + (rows - 1) * gap + 2, title,
                ", ".join(name for name, _ in items) + ". Evidence links in the README.")
    # A translucent text layer avoids colored LCD fringes on small SVG text in Chromium.
    card.styles.append("text{opacity:.98}")
    card.defs.append(gradient("tech-panel", ((0, "#171b26"), (1, "#11151f")), axis=(0, 0, 1, 1)))
    card.parts.extend((
        glyph(symbol, 16, 10, 29 if compact else 26),
        card.text(68, 36 if compact else 32, title, 29 if compact else 24,
                  weight=500, tracking="-.18"),
    ))
    if not compact:
        card.parts.append(card.text(w - inset, 31, note, 15.5, fill=COPY, anchor="end"))

    label_inset = 64 if compact else (56 if tools else 67)
    name_size = (22 if tools else 21.5) if compact else (15.2 if tools else 16)
    caption_size = 17 if compact else 11.6
    for index, (name, caption) in enumerate(items):
        row, col = divmod(index, cols)
        x = round(inset + sum(widths[:col]) + col * gap, 2)
        y = top + row * (h + gap)
        width = round(widths[col], 2)
        center_y = y + h / 2
        body = panel(x, y, width, h, radius=12, fill="url(#tech-panel)", stroke="#373b48")
        broad_slot = compact or not tools
        body += centered_mark(name, x + (32 if broad_slot else 27), center_y,
                              width=48 if broad_slot else 36, height=42)
        baseline = center_y - 4 if tools else center_y + (7.5 if compact else 5.5)
        body += card.text(round(x + label_inset, 2), baseline, name, name_size, weight=500)
        if tools:
            body += card.text(round(x + label_inset, 2), baseline + (23 if compact else 17),
                              caption, caption_size, fill=COPY)
        card.parts.append(group(body, motion="rise", delay=236 + index * 28))
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
        size = 13 if small else 12.5
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


def feature(name: str, repo: dict, index: int) -> Card:
    title, copy, stack = PROJECTS[name]
    card = Card(376, 325, title, f'{copy} {", ".join(stack)}. {repo["stars"]} GitHub stars, '
                                f'{repo["forks"]} forks. Opens the repository.')
    draw = (stadium_scene, train_scene, diagnostics_scene)[index]
    art_height, illustration = clip("art-height", box(0, 0, card.w, 147), draw(card))
    clipping, art = clip("cover", box(0, 0, card.w, card.h, radius=14), illustration)
    card.defs.extend((clipping, art_height))
    content = panel(0, 0, card.w, card.h, fill="url(#panel)") + art
    content += panel(0, 0, card.w, card.h, 14, fill="none")
    content += path("M.6 147h374.8", stroke=BORDER)
    content += card.text(19, 184, title, 24, weight=600, tracking="-.6")
    content += glyph("external", 337, 164, 19, VIOLET)
    lines = wrap(copy, size=15.4, width=330)
    if len(lines) > 3:
        raise ValueError("Featured description exceeds its card")
    for line, words in enumerate(lines):
        content += card.text(20, 209 + line * 19, words, 15.4, fill=COPY)
    content += stack_pills(card, stack, 19, 255)
    content += path("M19 290h338", stroke=BORDER)
    content += counts(card, repo, 20, 313)
    content += card.text(331, 312, "Source", 14.5, weight=600, fill=VIOLET, anchor="end")
    content += glyph("arrow", 337, 299, 16)
    card.parts.append(group(content, motion="rise", delay=340 + index * 55))
    return card


def heading_card(key: str, *, compact=False) -> Card:
    title, note, symbol = HEADERS[key]
    w = 680 if compact else WIDTH
    card = Card(w, 45, title, note)
    card.parts.append(card.heading(title, "" if compact else note, symbol, width=w))
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


def pin(name: str, copy: str, repo: dict) -> Card:
    title, _, stack = PROJECTS[name]
    card = Card(571, 116, name, f'Public repository, {title}. {copy} {", ".join(stack)}. '
                               f'{repo["stars"]} GitHub stars, {repo["forks"]} forks.')
    card.parts.extend((
        panel(0, 0, card.w, card.h, 13), glyph("repo", 17, 14, 22),
        card.text(51, 32, name, 20, weight=600, fill="#d4bbff", tracking="-.25"),
        box(433, 13, 85, 25, "#222134", "#3a344a", 8),
        card.text(475, 30, "Public", 14, fill=COPY, anchor="middle"),
        glyph("arrow", 534, 16, 17),
        card.text(19, 61, copy, 16, fill=COPY),
        stack_pills(card, stack[:2], 19, 77, small=True),
        counts(card, repo, 342, 97),
    ))
    return card


def footer(activity_stamp: dt.datetime, public_stamp: dt.datetime, *, compact=False) -> Card:
    w = 680 if compact else WIDTH
    a, p = activity_stamp.date(), public_stamp.date()
    dates = f"Verified {a:%d %b %Y} UTC" if a == p else f"Calendar {a:%d %b}  |  Repos {p:%d %b %Y} UTC"
    card = Card(w, 82, "Ayman Bounaouj | GitHub sources",
                f"Contribution calendar verified {a.isoformat()} UTC. Public repository metadata verified "
                f"{p.isoformat()} UTC. Opens the source snapshots.")
    card.parts.extend((
        panel(0, 0, w, card.h, 14), logo(19, 21, 72),
        path("M109 14v54", stroke=BORDER), card.text(130, 35, "Ayman Bounaouj", 21, weight=600),
        card.text(130, 60, "GitHub GraphQL + REST", 15, fill=COPY),
        card.text(w - 55, 47, dates, 15 if compact else 18, fill=COPY, anchor="end"),
        glyph("arrow", w - 39, 31, 22),
    ))
    return card


def artworks(stats: dict, public: dict) -> dict[str, Card]:
    repos = public["repositories"]
    files = {
        "link-github": button("GitHub", "code"),
        "link-profile": button("Profile links", "profile", primary=True),
        "link-linkedin": button("LinkedIn", "linkedin"),
    }
    for compact in (False, True):
        suffix = "-mobile" if compact else ""
        files["hero" + suffix] = hero(compact=compact)
        files["metrics" + suffix] = metrics(stats, public, compact=compact)
        files["calendar" + suffix] = contribution_calendar(stats, compact=compact)
        files["technical" + suffix] = tech_grid(compact=compact)
        files["tools" + suffix] = tech_grid(tools=True, compact=compact)
        files["footer" + suffix] = footer(stats["verified_at"], validate(public), compact=compact)
        for key in HEADERS:
            files["heading-" + key + suffix] = heading_card(key, compact=compact)
        for index, record in enumerate(CONTRIBUTIONS):
            url = contribution_url(record)
            files[f"contribution-{record[2]}{suffix}"] = collaboration(
                index, public["contributions"][url], compact=compact)
    for index, name in enumerate(tuple(PROJECTS)[:3]):
        files["project-" + name.lower()] = feature(name, repos[name], index)
    for name, label, symbol in CURRENT:
        files["building-" + name.lower()] = building(label, symbol, repos[name])
    for name, copy in PINS:
        files["pin-" + name.lower()] = pin(name, copy, repos[name])
    return files


def dynamic(name: str) -> bool:
    return name.startswith(("metrics", "calendar", "footer", "contribution-",
                            "project-", "building-", "pin-"))


def link(url: str, label: str) -> str:
    return f'<a href="{esc(url)}">{label}</a>'


def image(name: str, alt: str, width: int = 780, *, mobile=False, href="", local=None) -> str:
    def src(key: str) -> str:
        if local is not None:
            return esc(local[key])
        base = LIVE if dynamic(key) else "./cards/"
        return esc(base + key + ".svg")

    tag = f'<img src="{src(name)}" width="{width}" alt="{esc(alt)}">'
    if mobile:
        tag = f'<picture><source media="(max-width: 680px)" srcset="{src(name + "-mobile")}">{tag}</picture>'
    return link(href, tag) if href else tag


def profile_markup(*, local: dict[str, str] | None = None) -> str:
    def img(*args, **kwargs):
        return image(*args, **kwargs, local=local)

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
        feature_cards.append(img(f"project-{name.lower()}", f"{title}. {copy} View source.",
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
    readme_text = f"""<details>
<summary>Profile text and data sources</summary>
<p><strong>Ayman Bounaouj</strong> · Full-Stack Web Developer. Building practical, secure and scalable digital products.</p>
<ul>
<li>{link(repo_url("morocco2030"), "Morocco2030")}. Independent academic portal for multilingual tournament information and role-based staff workflows. {link(repo_url("morocco2030") + "/releases", "Releases")} · {link(repo_url("morocco2030") + "/actions/workflows/ci.yml", "CI")}</li>
<li>{link(repo_url("ab-train-ticket-studio"), "AB Train Ticket Studio")}. Independent booking simulation with sample tickets. {link(DEMO, "Live demo")}</li>
<li>{link(repo_url("PC-Full-Check"), "PC Full Check")}. Read-only Windows diagnostics and local reports. {link(repo_url("PC-Full-Check") + "/tree/main/tests", "Tests")}</li>
<li>{link(repo_url("violetgate"), "VioletGate")}. Authentication UI demo. {link(f"https://{OWNER}.github.io/violetgate/", "Live demo")} · {link(repo_url("ayman-calc"), "Ayman Calc")}. Browser calculator. {link(f"https://{OWNER}.github.io/ayman-calc/", "Live demo")}</li>
</ul>
<p>GitHub GraphQL supplies the {link(live_json, "daily counts")}. GitHub REST supplies repository totals and the {link("https://github.com/search?" + urlencode({"q": MERGED_SEARCH, "type": "pullrequests"}), "merged public PR search")}. {link(PROFILE, "GitHub’s native contribution graph")} shows current activity.</p>
<p>{link(docs, "Technical evidence and refresh setup")} · {link(archive, "Original artwork and previous profile links")}</p>
<p><sub>© 2026 Ayman Bounaouj. Original AB branding. All rights reserved.</sub></p>
</details>"""
    contacts = "\n".join((
        img("link-github", "GitHub profile", 100, href=PROFILE),
        img("link-profile", "Ayman Bounaouj’s public profile links", 100, href=PORTFOLIO),
        img("link-linkedin", "LinkedIn profile", 100, href=LINKEDIN),
    ))
    identity = img("hero", "Ayman Bounaouj. Full-Stack Web Developer. Building practical, secure and scalable digital products.",
                   mobile=True)
    return "\n\n".join((
        block(span(identity, "wide hero") + "<br>\n" + span(contacts, "contacts"), "section-group"),
        block(img("metrics", "Verified GitHub metrics. Yearly contributions, current streak, merged public pull requests and active days.",
                  mobile=True, href=SOURCE)),
        block(img("calendar", "Violet GitHub contribution calendar with weekday and month labels, monthly totals and intensity legend.",
                  mobile=True, href=PROFILE)),
        block(img("technical", "Languages & Technical Stack. " + ", ".join(STACK), mobile=True)),
        block(img("tools", "Frameworks / Build Tools. " + ", ".join(name for name, _ in TOOLS), mobile=True)),
        section("featured", "\n".join(feature_cards), "project-row",
                "<br>\n" + span(f"<sub>{link(DEMO, 'AB Train Ticket Studio live demo ↗')}</sub>", "demo")),
        section("opensource", "<br>\n".join(highlights), "wide contributions"),
        section("building", "\n".join(tiles), "building-row"),
        section("pinned", "\n".join(pins[:2]) + "<br>\n" + "\n".join(pins[2:]), "pin-row"),
        block(img("footer", "Ayman Bounaouj. GitHub GraphQL and REST sources, with verification dates.",
                  mobile=True, href=SOURCE), "wide footer"),
        readme_text,
    )) + "\n"


README_MARKER = "<!-- Generated by scripts/render_svg_cards.py --write-readme -->\n\n"
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
.contacts{display:flex;justify-content:center;flex-wrap:wrap;gap:8px}
.contacts img{width:clamp(95px,19vw,132px)}
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
.footer{margin-top:16px}
details{font-size:.84em;color:#bbb4c8;padding:0 6px 8px}
summary{width:fit-content;cursor:pointer}
details p,details ul{margin:7px 0}
@media (max-width:680px){
  main{padding:9px}
  p{margin-bottom:10px}
  .project-row,.pin-row{grid-template-columns:minmax(0,1fr)}
  .building-row{grid-template-columns:minmax(0,1fr)}
  .project-row,.pin-row,.building-row{gap:7px}
}
"""


def preview_markup(svg: dict[str, str]) -> str:
    sources = {name.removesuffix(".svg"): "data:image/svg+xml;base64,"
               + base64.b64encode(xml.encode("utf-8")).decode("ascii") for name, xml in svg.items()}
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            '<meta name="color-scheme" content="dark">\n'
            '<title>Ayman Bounaouj | GitHub profile preview</title>\n'
            f'<style>{PREVIEW_STYLE}</style>\n</head>\n<body>\n<main>\n'
            + profile_markup(local=sources) + '</main>\n</body>\n</html>\n')


def verify_svg(xml: str, name: str, static: bool) -> None:
    allowed = {"svg", "title", "desc", "defs", "style", "g", "path", "rect", "circle",
               "ellipse", "linearGradient", "radialGradient", "stop", "clipPath", "text", "image"}
    if (len(xml.encode("utf-8")) > 140_000 or re.search(r"<[!?]|@import|javascript:|data:text/", xml, re.I)
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
            if attr == "href" and tag == "image" and name == "project-ab-train-ticket-studio":
                good = (value.startswith(TRAIN_URI)
                        and hashlib.sha256(base64.b64decode(value[len(TRAIN_URI):], validate=True)).hexdigest()
                        == TRAIN_SHA256)
                if good:
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
    if path.read_text(encoding="utf-8") != README_MARKER + profile_markup():
        raise ValueError("README does not match the generated dashboard markup")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calendar", type=Path, default=ROOT / "data/dashboard-contributions.json")
    parser.add_argument("--public", type=Path, default=ROOT / "data/dashboard-public.json")
    parser.add_argument("--output", type=Path, default=ROOT / "cards")
    parser.add_argument("--preview", type=Path, help="write a self-contained offline HTML preview")
    parser.add_argument("--write-readme", action="store_true", help="regenerate README.md from the layout")
    parser.add_argument("--verify", action="store_true", help="compare generated artwork to existing files")
    parser.add_argument("--dynamic-only", action="store_true", help="render only the published live data cards")
    parser.add_argument("--require-fresh", action="store_true", help="enforce the 36-hour publication window")
    args = parser.parse_args()
    if (args.dynamic_only and args.preview) or (args.verify and (args.preview or args.write_readme)):
        parser.error("Preview and README generation require a full render")
    static = os.getenv("STATIC") == "1"
    if args.write_readme and (static or args.dynamic_only):
        parser.error("README assembly requires the regular animated render")
    try:
        stats = activity(read_json(args.calendar), fresh=args.require_fresh)
        public = read_json(args.public)
        validate(public, fresh=args.require_fresh)
        svg = {}
        for name, card in artworks(stats, public).items():
            if args.dynamic_only and not dynamic(name):
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
            (ROOT / "README.md").write_text(README_MARKER + profile_markup(), encoding="utf-8", newline="\n")
        if args.preview:
            args.preview.parent.mkdir(parents=True, exist_ok=True)
            args.preview.write_text(preview_markup(svg), encoding="utf-8", newline="\n")
    except (KeyError, OSError, ValueError, ET.ParseError) as exc:
        parser.exit(1, f"Dashboard validation failed: {exc}\n")
    print(f"PASS: {len(svg)} {'static' if static else 'animated'} SVG cards verified")


if __name__ == "__main__":
    main()
