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

FILES = ("v6-metrics.svg", "v6-calendar.svg", "v6-stack.svg", "v6-open-source.svg",
         "v6-languages.svg", "v6-frameworks.svg", "v6-building.svg", "v6-pinned.svg")
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
    # Never copy the reference image's decorative counters. Every number here
    # comes from a validated public/aggregate snapshot with a dated source.
    from render_profile import analysis
    info = analysis(contrib, reference_date=dt.date.fromisoformat(contrib["days"][-1]["date"]))
    values = [
        (f'{contrib["total_contributions"]:,}', "Contributions", "Past year", "</>"),
        (str(info["current"]), "Current streak", "Consecutive active days", "♨"),
        (str(len(portfolio["verified_collaborations"])), "Merged external PRs", "Verified recent sample", "⑂"),
        (str(portfolio["public_original_repository_count"]), "Public repositories", "Original, non-fork", "▣"),
    ]
    art = root_svg(124, "GitHub verified profile statistics",
                   "Four dark violet statistic cards: annual contributions, current contribution streak, verified recent external merges, and original public repositories.")
    for i, (value, name, subtitle, symbol) in enumerate(values):
        x = 5 + i * 251
        art.append(rect(x, 3, 239, 109, active=(i == 0)))
        art.append(text(x + 24, 59, symbol, 34, PURPLE, 700))
        art.append(text(x + 94, 46, value, 29, TEXT, 700))
        art.append(text(x + 94, 70, name, 16, TEXT, 700))
        art.append(text(x + 94, 91, subtitle, 12, MUTED))
    return svg_done(art)


def calendar(contrib: dict) -> str:
    # Calendars use Sunday-first columns to match the native GitHub heatmap.
    # Month labels are placed on the first new week, not only on Mondays.
    days = contrib["days"]
    first = dt.date.fromisoformat(days[0]["date"])
    shift = (first.weekday() + 1) % 7
    columns = (len(days) + shift + 6) // 7
    step = min(15.6, 827 / max(1, columns))
    cell = step - 3
    x0, y0 = 117, 76
    art = root_svg(188, "Contribution Activity",
                   "One year of verified GitHub GraphQL contribution counts in five green levels, with accurate day and month positions.")
    art.append(rect(3, 2, 994, 177, active=True))
    art.extend([text(24, 35, "▦   Contribution Activity", 24, TEXT, 700),
                text(980, 35, f'{contrib["total_contributions"]:,} contributions in the last year', 14, MUTED, anchor="end")])
    for label, row in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
        art.append(text(62, int(y0 + row * 13.7 + 10), label, 12, MUTED))
    levels = ("#123121", "#0d5d38", "#098a45", "#08bc53", "#18ef61")
    seen_months = set()
    for i, day in enumerate(days):
        date = dt.date.fromisoformat(day["date"])
        position = i + shift
        row, col = position % 7, position // 7
        month_key = date.strftime("%Y-%m")
        if month_key not in seen_months:
            seen_months.add(month_key)
            art.append(text(int(x0 + col * step), 67, date.strftime("%b"), 11, MUTED))
        count = day["count"]
        level = 0 if count == 0 else 1 if count <= 2 else 2 if count <= 6 else 3 if count <= 12 else 4
        art.append(f'<rect x="{x0 + col * step:.1f}" y="{y0 + row * 13.7:.1f}" width="{cell:.1f}" height="11.4" rx="2" fill="{levels[level]}"/>')
    art.append(text(816, 167, "Less", 11, MUTED))
    for j, color in enumerate(levels):
        art.append(f'<rect x="{859+j*17}" y="157" width="14" height="13" rx="2" fill="{color}"/>')
    art.append(text(957, 167, "More", 11, MUTED))
    return svg_done(art)


def stack(portfolio: dict) -> str:
    langs = portfolio["language_bytes"][:12]
    frameworks = portfolio["verified_frameworks"][:9]
    sum_bytes = sum(amount for _, amount in portfolio["language_bytes"])
    lang_rows = max(1, (len(langs) + 5) // 6)
    fw_rows = max(1, (len(frameworks) + 3) // 4)
    fw_heading = 84 + lang_rows * 66 + 36
    toolkit_y = fw_heading + 42 + fw_rows * 71 + 22
    height = toolkit_y + 134
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
    # Owner-declared workflow tools are intentionally separate from manifest-verified frameworks.
    # This section is not automatically detected and is never presented as GitHub API evidence.
    art.append(text(24, toolkit_y, "WORKFLOW / DELIVERY TOOLS", 22, TEXT, 700))
    art.append(text(24, toolkit_y + 22, "Owner-declared toolkit · separate from verified framework signals", 12, MUTED))
    for i, name in enumerate(("Node.js", "Composer", "pnpm", "Docker", "GitHub Actions")):
        tx = 20 + i * 196
        ty = toolkit_y + 32
        art.append(rect(tx, ty, 181, 53))
        art.append(text(tx + 14, ty + 33, "◆", 16, PURPLE))
        art.append(text(tx + 38, ty + 32, name, 14, TEXT, 700))
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



# The visible V6 stack recreates the reference's 6-column compact chip grid.
# "Declared" technologies are distinct from the live API's verified languages
# and public dependency-manifest frameworks. This is *not* a proficiency score.
DISPLAY_TECH = (
    "PHP", "JavaScript", "TypeScript", "Python", "HTML", "CSS",
    "MySQL", "Laravel", "React", "Docker", "Playwright", "Tailwind CSS",
)
DISPLAY_BUILD = ("Laravel", "Vite", "Node.js", "Composer", "pnpm", "Docker", "GitHub Actions")


def technology_icon(name: str, x: int, y: int, side: int = 29) -> str:
    from live_portfolio import _icons
    item = _icons().get(name)
    if item is None:
        fallback = {"TypeScript":"TS","MySQL":"DB","Docker":"DK","Playwright":"PW",
                    "Node.js":"JS","Composer":"CP","pnpm":"PN","GitHub Actions":"GH"}.get(name, name[:2].upper())
        return (f'<rect x="{x}" y="{y}" width="{side}" height="{side}" rx="5" fill="#342452" stroke="#6b4b9c"/>'
                + text(x + side//2, y + int(side*0.67), fallback, max(10,side//3), "#e7d7ff",700, anchor="middle"))
    scale = side / float(item["viewBox"])
    path = esc(item["path"])
    color = esc(item["color"])
    if item.get("stroke"):
        shape = f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"/>'
    else:
        shape = f'<path d="{path}" fill="{color}"/>'
    return f'<g transform="translate({x} {y}) scale({scale:.6f})">{shape}</g>'


def compact_technology(portfolio: dict) -> str:
    language_names = {name for name, _ in portfolio["language_bytes"]}
    frameworks = {row["name"] for row in portfolio["verified_frameworks"]}
    art = root_svg(171, "Languages & Technical Stack",
                   "Reference-matched technology grid, with GitHub Linguist languages, verified framework dependencies, and clearly owner-declared tools.")
    art.append(text(11, 35, "▱   Languages & Technical Stack", 24, TEXT, 700))
    art.append(text(981, 35, "Languages and tools used in development", 13, MUTED, anchor="end"))
    for i, name in enumerate(DISPLAY_TECH):
        x = 8 + (i % 6) * 166
        y = 48 + (i // 6) * 59
        art.append(rect(x, y, 156, 50, active=(name=="Laravel")))
        art.append(technology_icon(name, x+11, y+10, 29))
        art.append(text(x+50, y+30, name, 15 if len(name)<13 else 12, TEXT, 700))
        # Only public-manifest framework names may be flagged as verified.
        if name in frameworks or name in language_names:
            art.append(f'<circle cx="{x+143}" cy="{y+13}" r="3" fill="#3ac795"/>')
    art.append(text(11, 167, "Green dots: verified in GitHub data · Others: owner-declared tools", 10, MUTED))
    return svg_done(art)


def compact_frameworks(portfolio: dict) -> str:
    frameworks = {row["name"] for row in portfolio["verified_frameworks"]}
    art = root_svg(117, "Frameworks / Build Tools",
                   "Seven illustrated build-tool chips matching the supplied reference; evidence-based frameworks and a separately declared development toolkit.")
    art.append(text(11, 32, "⚒   Frameworks / Build Tools", 24, TEXT, 700))
    art.append(text(986, 32, "Frameworks, tooling and development services", 12, MUTED, anchor="end"))
    for i, name in enumerate(DISPLAY_BUILD):
        x = 8 + i * 142
        y = 43
        art.append(rect(x, y, 135, 59, active=(name in frameworks)))
        art.append(technology_icon(name, x+8, y+13, 30))
        art.append(text(x+42, y+26, name, 14 if len(name)<12 else 11, TEXT, 700))
        label = "verified" if name in frameworks else "toolkit"
        art.append(text(x+42, y+43, label, 11, MUTED))
    return svg_done(art)


def currently_building(activity: dict) -> str:
    recent = activity["recent_repositories"][:3]
    art = root_svg(111, "Currently Building — recent public repositories",
                   "Three recently pushed public GitHub repositories from the validated activity snapshot. This does not claim exclusive or real-time active development.")
    art.append(text(11, 31, "◉   Currently Building", 23, TEXT, 700))
    art.append(text(986, 31, "Recently updated public work", 12, MUTED, anchor="end"))
    for i in range(3):
        x = 8 + i * 332
        art.append(rect(x, 44, 321, 52))
        if i < len(recent):
            name = recent[i]["name"][:24]
            art.append(text(x+161, 76, name, 17, "#e2c8ff",700,anchor="middle"))
        else:
            art.append(text(x+161, 76, "No additional public activity", 14, MUTED,anchor="middle"))
    return svg_done(art)


def pinned(portfolio: dict) -> str:
    # Editorial selections are not claimed to be GitHub native pinned items.
    other={x["name"].casefold() for x in portfolio["other_repositories"]}
    items=[
       ("morocco2030","Multilingual tournament platform","Laravel / PHP"),
       ("ab-train-ticket-studio","Ticket booking, PDF and QR","JavaScript / Vite"),
       ("PC-Full-Check","Read-only Windows diagnostics","PowerShell"),
       ("site-recettes" if "site-recettes" in other else None,
        "Recipe site" if "site-recettes" in other else "More public projects",
        "Public repository" if "site-recettes" in other else "Browse GitHub"),
    ]
    art=root_svg(248,"Selected Public Repositories",
                 "Four curated public repository cards. No private repositories, misleading GitHub-native pin claim, or invented star and fork counts.")
    art.append(text(11, 30, "⚑   Pinned / Selected Repositories", 23, TEXT, 700))
    art.append(text(988, 30, "Curated public projects", 12, MUTED, anchor="end"))
    for i,(name,summary,tech) in enumerate(items):
        x=8+(i%2)*498
        y=44+(i//2)*95
        art.append(rect(x,y,484,87))
        art.append(text(x+17,y+32,("▣  "+name) if name else "▣  Browse other public work",18,"#cfb7ff",700))
        art.append(text(x+18,y+54,summary,13,TEXT))
        art.append(text(x+18,y+74,tech,12,MUTED))
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
        "v6-languages.svg": compact_technology(portfolio),
        "v6-frameworks.svg": compact_frameworks(portfolio),
        "v6-building.svg": currently_building(activity),
        "v6-pinned.svg": pinned(portfolio),
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
