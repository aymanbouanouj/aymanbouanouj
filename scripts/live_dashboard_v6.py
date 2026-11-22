#!/usr/bin/env python3
"""Render V6 dark/violet GitHub README panels from *verified* existing snapshots.

No extra GitHub API access. Never renders private repository identifiers.
SVGs are dated snapshots, not real-time counters.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from live_contributions import render as verify_contribution_art
from live_portfolio import validate as validate_portfolio
from live_profile import validate as validate_activity

FILES = ("v6-metrics.svg", "v6-calendar.svg", "v6-stack.svg", "v6-open-source.svg")
BG = "#0a0d18"
CARD = "#151a2b"
EDGE = "#42415d"
PURPLE = "#b46aff"
TEXT = "#f6f7ff"
MUTED = "#bdc2d5"
FONT = "Arial,Helvetica,sans-serif"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def root_svg(height: int, title: str, description: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{height}" viewBox="0 0 1000 {height}" role="img" aria-labelledby="title description">',
        f'<title id="title">{esc(title)}</title><desc id="description">{esc(description)}</desc>',
        '<style>@media(prefers-reduced-motion:reduce){*{animation:none!important}}</style>',
        '<defs><linearGradient id="panel" x1="0" y1="0" x2="1" y2="1">'
        '<stop stop-color="#17162c"/><stop offset="1" stop-color="#101827"/>'
        '</linearGradient><linearGradient id="highlight" x1="0" y1="0" x2="1" y2="0">'
        '<stop stop-color="#7139d4"/><stop offset="1" stop-color="#ce6eff"/>'
        '</linearGradient></defs>',
        f'<rect width="1000" height="{height}" rx="18" fill="{BG}"/>',
    ]


def rect(x: int, y: int, w: int, h: int, *, active=False, radius=15) -> str:
    color = 'url(#panel)' if active else CARD
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
            f'fill="{color}" stroke="{EDGE}" stroke-width="1.4"/>')


def text(x: int, y: int, value: object, size=19, color=TEXT, weight=400,
         anchor="start") -> str:
    return (f'<text x="{x}" y="{y}" fill="{color}" font-family="{FONT}" '
            f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">'
            f'{esc(value)}</text>')


def dated(value: str) -> str:
    return value[:16].replace("T", " ") + " UTC"


def svg_done(pieces: list[str]) -> str:
    pieces.append("</svg>")
    result = "\n".join(pieces) + "\n"
    parsed = ET.fromstring(result)
    if parsed.tag != "{http://www.w3.org/2000/svg}svg":
        raise ValueError("SVG root is invalid")
    if len(result.encode("utf-8")) >= 500_000:
        raise ValueError("V6 SVG exceeds size limit")
    for node in parsed.iter():
        if node.tag.rsplit("}", 1)[-1].lower() in ("script", "foreignobject", "image", "use", "a", "iframe"):
            raise ValueError("Disallowed SVG element")
        for key in node.attrib:
            if key.rsplit("}", 1)[-1].lower().startswith("on"):
                raise ValueError("Disallowed inline SVG event")
    return result


def metrics(contrib: dict, portfolio: dict, activity: dict) -> str:
    days = contrib["days"]
    active_days = sum(1 for day in days if day["count"] > 0)
    values = [
        (f'{contrib["total_contributions"]:,}', "Contributions", "Past 365 calendar days", "◆"),
        (str(active_days), "Active days", "Days with contributions", "▦"),
        (str(len(portfolio["verified_collaborations"])), "Verified merged PRs", "External public repositories", "⑂"),
        (str(portfolio["public_original_repository_count"]), "Public projects", "Original repositories", "◇"),
    ]
    art = root_svg(190, "V6 verified GitHub metrics",
                   "Counts are dated GitHub API snapshots. Merged PR count includes verified external public pull requests only.")
    art.extend([text(24, 37, "ENGINEERING AT A GLANCE", 22, TEXT, 700),
                text(976, 37, dated(contrib["fetched_at_utc"]), 13, MUTED, anchor="end")])
    for i, (value, name, subtitle, symbol) in enumerate(values):
        x = 20 + i * 245
        art.append(rect(x, 52, 225, 113, active=i == 0))
        art.append(text(x + 18, 85, symbol, 25, PURPLE, 700))
        art.append(text(x + 60, 92, value, 33, TEXT, 700))
        art.append(text(x + 18, 120, name, 17, TEXT, 700))
        art.append(text(x + 18, 145, subtitle, 12, MUTED))
    return svg_done(art)


def calendar(contrib: dict) -> str:
    days = contrib["days"]
    first = dt.date.fromisoformat(days[0]["date"])
    columns = (len(days) + first.weekday() + 6) // 7
    step = min(16, int(840 / max(columns, 1)))
    cell = step - 3
    x0, y0 = 100, 83
    art = root_svg(266, "Contribution activity calendar",
                   "365-day contribution calendar. Bright green cells mean more contributions; no fabricated streak values.")
    art.append(rect(18, 16, 964, 232, active=True))
    art.extend([
        text(37, 50, "CONTRIBUTION ACTIVITY", 23, TEXT, 700),
        text(966, 50, f'{contrib["total_contributions"]:,} contributions / 365 days', 14, MUTED, anchor="end")
    ])
    for label, row in (("Mon", 0), ("Wed", 2), ("Fri", 4)):
        art.append(text(63, y0 + row * 21 + 11, label, 12, MUTED))
    levels = ("#163023", "#0c5839", "#058c49", "#04c85c", "#16ff76")
    top = max((day["count"] for day in days), default=0)
    previous_month = None
    for i, day in enumerate(days):
        date = dt.date.fromisoformat(day["date"])
        row = (i + first.weekday()) % 7
        col = (i + first.weekday()) // 7
        if date.month != previous_month and row == 0 and col < columns - 1:
            art.append(text(x0 + col * step, 75, date.strftime("%b"), 11, MUTED))
        previous_month = date.month
        count = day["count"]
        intensity = 0 if count == 0 else min(4, max(1, (count * 4 + max(1, top) - 1) // max(1, top)))
        art.append(f'<rect x="{x0 + col * step}" y="{y0 + row * 21}" width="{cell}" height="15" rx="2.5" fill="{levels[intensity]}"/>')
    art.append(text(40, 232, "GitHub GraphQL · dated snapshot; the native GitHub calendar remains authoritative.", 12, MUTED))
    return svg_done(art)


def stack(portfolio: dict) -> str:
    langs = portfolio["language_bytes"][:12]
    frameworks = portfolio["verified_frameworks"][:9]
    sum_bytes = sum(amount for _, amount in portfolio["language_bytes"])
    lang_rows = max(1, (len(langs) + 5) // 6)
    fw_rows = max(1, (len(frameworks) + 3) // 4)
    fw_heading = 84 + lang_rows * 66 + 36
    height = fw_heading + 42 + fw_rows * 71 + 50
    art = root_svg(height, "Languages and frameworks from verified GitHub data",
                   "Programming languages reflect GitHub Linguist byte counts. Frameworks are verified against public dependency manifests.")
    art.extend([text(24, 40, "LANGUAGES & TECHNICAL STACK", 25, TEXT, 700),
                text(24, 65, "LANGUAGES · GitHub Linguist code bytes, not proficiency scores", 13, MUTED)])
    for i, (name, amount) in enumerate(langs):
        x = 20 + (i % 6) * 164
        y = 82 + (i // 6) * 66
        art.append(rect(x, y, 152, 56))
        art.append(f'<circle cx="{x + 22}" cy="{y + 28}" r="15" fill="#493172" stroke="#b46aff" stroke-width="1"/>')
        art.append(text(x + 22, y + 33, name[:2].upper(), 12, TEXT, 700, anchor="middle"))
        art.append(text(x + 44, y + 25, name[:13], 14, TEXT, 700))
        share = f'{amount / sum_bytes:.1%}' if sum_bytes else "0%"
        art.append(text(x + 44, y + 44, share, 11, MUTED))
    art.append(text(24, fw_heading, "FRAMEWORKS / BUILD TOOLS", 24, TEXT, 700))
    art.append(text(24, fw_heading + 24, "Verified in public dependency manifests", 13, MUTED))
    for i, framework in enumerate(frameworks):
        x = 20 + (i % 4) * 245
        y = fw_heading + 36 + (i // 4) * 71
        name = framework["name"]
        art.append(rect(x, y, 225, 62, active=(i == 0)))
        art.append(text(x + 17, y + 26, "⬡", 24, PURPLE, 700))
        art.append(text(x + 48, y + 27, name[:19], 17, TEXT, 700))
        art.append(text(x + 48, y + 47, f'{len(framework["repositories"])} source repos', 12, MUTED))
    if not frameworks:
        art.append(text(36, fw_heading + 74, "No frameworks verified in the available public manifests.", 16, MUTED))
    scope = ("Public + selected private aggregates" if portfolio["language_scope"] == "public-plus-private"
             else "Public-only; private data unavailable" if portfolio["language_scope"] == "public-only-private-unavailable"
             else "Public repositories only")
    art.append(text(24, height - 18, f'{scope} · {dated(portfolio["generated_at_utc"])}', 12, MUTED))
    return svg_done(art)


def open_source(portfolio: dict) -> str:
    collabs = portfolio["verified_collaborations"][:5]
    height = 98 + max(1, len(collabs)) * 60 + 30
    art = root_svg(height, "Verified open-source contributions",
                   "Only external merged pull requests confirmed via public GitHub API. Open requests are not misrepresented as merged.")
    art.append(text(24, 40, "OPEN SOURCE & VERIFIED CONTRIBUTIONS", 24, TEXT, 700))
    art.append(text(24, 65, "Merged external pull requests · each destination is public and verified", 13, MUTED))
    if not collabs:
        art.append(rect(20, 80, 960, 57))
        art.append(text(35, 112, "No verified public merged external pull requests in this snapshot.", 16, MUTED))
    for i, row in enumerate(collabs):
        y = 80 + i * 60
        art.append(rect(20, y, 960, 53))
        art.append(text(40, y + 34, "⑂", 21, PURPLE, 700))
        art.append(text(80, y + 29, row["name"][:50], 18, TEXT, 700))
        art.append(text(80, y + 45, "Merged public pull request", 11, MUTED))
        art.append(text(954, y + 33, f'PR #{row["number"]} · MERGED', 14, "#6bdfad", 700, anchor="end"))
    art.append(text(24, height - 15, "Source: GitHub public merged-PR verification · " + dated(portfolio["generated_at_utc"]), 12, MUTED))
    return svg_done(art)


def render(contributions: dict, portfolio: dict, activity: dict) -> dict[str, str]:
    # Reuse the source validators. No API calls or private repo identifiers.
    verify_contribution_art(contributions)
    validate_portfolio(portfolio)
    validate_activity(activity)
    results = {
        "v6-metrics.svg": metrics(contributions, portfolio, activity),
        "v6-calendar.svg": calendar(contributions),
        "v6-stack.svg": stack(portfolio),
        "v6-open-source.svg": open_source(portfolio),
    }
    return results


def read_sources(folder: Path) -> tuple[dict, dict, dict]:
    return tuple(json.loads((folder / name).read_text(encoding="utf-8")) for name
                 in ("contributions.json", "portfolio.json", "activity.json"))


def build(folder: Path) -> dict[str, str]:
    content = render(*read_sources(folder))
    for name, value in content.items():
        (folder / name).write_text(value, encoding="utf-8")
    return content


def verify(folder: Path) -> None:
    expected = render(*read_sources(folder))
    for name, value in expected.items():
        if (folder / name).read_text(encoding="utf-8") != value:
            raise ValueError("V6 panel does not match final validated snapshot: " + name)


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build", action="store_true")
    mode.add_argument("--verify", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.build:
        build(args.output)
    verify(args.output)
    print("PASS: V6 SVG dashboard reflects validated, dated GitHub snapshots")


if __name__ == "__main__":
    main()
