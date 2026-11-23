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
from v6_design_system import TOKENS, reference_panel_height

FILES = ("v6-metrics.svg", "v6-calendar.svg", "v6-stack.svg", "v6-open-source.svg",
         "v6-languages.svg", "v6-frameworks.svg", "v6-building.svg", "v6-pinned.svg",
         "v6-pin-morocco.svg", "v6-pin-train.svg", "v6-pin-pc.svg", "v6-pin-recettes.svg")
BG = TOKENS.background
CARD = TOKENS.card
EDGE = TOKENS.border
PURPLE = TOKENS.accent
TEXT = TOKENS.text
MUTED = TOKENS.muted
FONT = TOKENS.font_stack


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



def line_icon(name: str, x: float, y: float, size: int = 31, color: str = PURPLE) -> str:
    """Draw known icons as geometry: avoid missing Unicode glyphs on SVG renderers."""
    paths = {
        "code": '<path d="M8 9 2 15l6 6 M22 9l6 6-6 6 M18 5l-5 20"/>',
        "flame": '<path d="M16 2c-1 7 5 9 4 15 4-2 4-6 3-8 7 9 4 20-7 20S4 23 6 16c1-4 4-7 5-9-1 6 3 6 5 8 2-5 0-7 0-13Z"/>',
        "git": '<circle cx="7" cy="7" r="3"/><circle cx="23" cy="7" r="3"/><circle cx="23" cy="24" r="3"/><path d="M7 10v10a4 4 0 0 0 4 4h9 M23 10v11"/>',
        "repo": '<rect x="5" y="3" width="20" height="25" rx="3"/><path d="M10 3v25 M14 9h7 M14 14h7"/>',
        "calendar": '<rect x="3" y="4" width="24" height="23" rx="3"/><path d="M3 11h24 M10 2v5 M20 2v5 M10 16h4 M18 16h4 M10 22h4 M18 22h4"/>',
        "layers": '<path d="m15 3 12 7-12 7L3 10Z M3 15l12 7 12-7 M3 20l12 7 12-7"/>',
        "tools": '<path d="M6 7l17 17 M19 5a6 6 0 0 1 6 8l-6-3-4 4 3 6a6 6 0 0 1-8-6L4 20a3 3 0 0 0 4 4l6-6 M4 2v7 M1 5h7"/>',
        "contribute": '<path d="M8 5h12 M8 10h8 M4 3v24 M7 24h18 M22 20l3 4-3 4"/>',
        "target": '<circle cx="15" cy="15" r="12"/><circle cx="15" cy="15" r="7"/><circle cx="15" cy="15" r="2"/>',
        "pin": '<path d="M10 3h10l-2 10 5 5v3H7v-3l5-5Z M15 21v8"/>',
    }
    if name not in paths:
        raise ValueError("Unknown semantic SVG icon: " + name)
    return (f'<g transform="translate({x} {y}) scale({size / 30:.4f})" '
            f'fill="none" stroke="{esc(color)}" stroke-width="2.5" stroke-linecap="round" '
            f'stroke-linejoin="round">{paths[name]}</g>')


def metrics(contrib: dict, portfolio: dict, activity: dict) -> str:
    # The reference shows decorative numbers; these counters use validated data.
    from render_profile import analysis
    info = analysis(contrib, reference_date=dt.date.fromisoformat(contrib["days"][-1]["date"]))
    values = [
        (f'{contrib["total_contributions"]:,}', "Contributions", "Past year", "code"),
        (str(info["current"]), "Current streak", "Consecutive active days", "flame"),
        (str(len(portfolio["verified_collaborations"])), "Merged external PRs", "Verified recent sample", "git"),
        (str(portfolio["public_original_repository_count"]), "Public repositories", "Original, non-fork", "repo"),
    ]
    art = root_svg(reference_panel_height("metrics") + 5, "GitHub verified profile statistics",
                   "Four visual metric cards: verified contributions, current streak, confirmed external merges and original public repositories.")
    for i, (value, name, subtitle, icon_name) in enumerate(values):
        x = 5 + i * 251
        art.append(rect(x, 2, 239, 93, active=(i == 0), radius=TOKENS.card_radius))
        art.append(line_icon(icon_name, x + 19, 30, 34))
        art.append(text(x + 86, 40, value, 29, TEXT, 700))
        art.append(text(x + 86, 63, name, 14 if len(name) > 18 else 15, TEXT, 700))
        art.append(text(x + 86, 83, subtitle, 11, MUTED))
    return svg_done(art)


def calendar(contrib: dict) -> str:
    """GitHub Sunday-first week columns; no overlapping month or legend labels."""
    days = contrib["days"]
    first = dt.date.fromisoformat(days[0]["date"])
    shift = (first.weekday() + 1) % 7
    columns = (len(days) + shift + 6) // 7
    step = min(15.6, 820 / max(1, columns))
    cell = step - 3
    x0, y0 = 112, 77
    art = root_svg(215, "Contribution Activity",
                   "One-year GitHub contribution calendar, with collision-free month labels and an isolated five-color legend.")
    art.append(rect(3, 2, 994, 205, active=True))
    art.append(line_icon("calendar", 23, 13, 23))
    art.append(text(61, 36, "Contribution Activity", 24, TEXT, 700))
    art.append(text(980, 35, f'{contrib["total_contributions"]:,} contributions in the last year', 14, MUTED, anchor="end"))
    for label, row in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
        art.append(text(62, round(y0 + row * 13.7 + 10), label, 12, MUTED))
    levels = ("#123121", "#0d5d38", "#098a45", "#08bc53", "#18ef61")
    months = []
    for i, day in enumerate(days):
        date = dt.date.fromisoformat(day["date"])
        position = i + shift
        row, col = position % 7, position // 7
        month_key = date.strftime("%Y-%m")
        if not months or month_key != months[-1][0]:
            months.append((month_key, col, date.strftime("%b")))
        count = day["count"]
        level = 0 if count == 0 else 1 if count <= 2 else 2 if count <= 6 else 3 if count <= 12 else 4
        art.append(f'<rect x="{x0 + col * step:.1f}" y="{y0 + row * 13.7:.1f}" width="{cell:.1f}" height="11.4" rx="2" fill="{levels[level]}"/>')
    # The first and last partial months can sit less than one week apart from
    # adjacent labels. Only draw a label when enough pixel space remains.
    last_x = -1_000
    for index, (_month, col, label) in enumerate(months):
        next_col = months[index + 1][1] if index + 1 < len(months) else columns
        x = x0 + col * step
        if x - last_x < 38 or (next_col - col) * step < 35 or x > 920:
            continue
        art.append(text(round(x), 69, label, 11, MUTED))
        last_x = x
    art.append(text(795, 198, "Less", 11, MUTED))
    for j, color in enumerate(levels):
        art.append(f'<rect x="{832+j*17}" y="187" width="14" height="13" rx="2" fill="{color}"/>')
    art.append(text(933, 198, "More", 11, MUTED))
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
        art.append(line_icon("contribute", 36, y + 15, 25))
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


def _brand_icons() -> dict:
    """Local, source-licensed vector assets; no outbound requests or executable SVG."""
    path = Path(__file__).with_name("v6_brand_icons.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not isinstance(data.get("icons"), dict):
        raise ValueError("Invalid vendored SVG icon manifest")
    return data["icons"]


def technology_icon(name: str, x: float, y: float, side: int = 37) -> str:
    icon = _brand_icons().get(name)
    if not icon:
        raise ValueError("No verified licensed SVG path for " + name)
    view_box = icon["viewBox"]
    if view_box not in (24, 128):
        raise ValueError("Unexpected icon coordinate system")
    artwork = []
    for path in icon["paths"]:
        d, fill = path["d"], path["fill"]
        if not isinstance(d, str) or not d or len(d) > 100_000:
            raise ValueError("Invalid icon path data")
        if not isinstance(fill, str) or len(fill) != 7 or not fill.startswith("#"):
            raise ValueError("Invalid icon palette")
        artwork.append(f'<path d="{esc(d)}" fill="{esc(fill)}"/>')
    scale = side / view_box
    return f'<g transform="translate({x} {y}) scale({scale:.6f})">{"".join(artwork)}</g>'


def compact_technology(portfolio: dict) -> str:
    language_names = {name for name, _ in portfolio["language_bytes"]}
    frameworks = {row["name"] for row in portfolio["verified_frameworks"]}
    art = root_svg(166, "Languages & Technical Stack",
                   "Twelve branded technology tiles arranged in two rows, faithfully following the supplied profile reference.")
    art.append(line_icon("layers", 12, 12, 24))
    art.append(text(50, 36, "Languages & Technical Stack", 25, TEXT, 700))
    art.append(text(984, 35, "The technologies I use to build, test and deploy", 13, MUTED, anchor="end"))
    for i, name in enumerate(DISPLAY_TECH):
        x, y = 7 + (i % 6) * 166, 43 + (i // 6) * 57
        art.append(rect(x, y, 158, 50, radius=TOKENS.card_radius))
        art.append(technology_icon(name, x + 11, y + 9, 32))
        art.append(text(x + 53, y + 32, name, 15 if len(name) <= 11 else 12, TEXT, 700))
        # Distinguish evidence subtly without inventing source support.
        if name in language_names or name in frameworks:
            art.append(f'<circle cx="{x+149}" cy="{y+12}" r="2.5" fill="#5acf95"/>')
    return svg_done(art)


def compact_frameworks(portfolio: dict) -> str:
    frameworks = {row["name"] for row in portfolio["verified_frameworks"]}
    art = root_svg(112, "Frameworks / Build Tools",
                   "Seven illustrated framework, runtime, package manager, container, and CI cards.")
    art.append(line_icon("tools", 12, 10, 24))
    art.append(text(50, 34, "Frameworks / Build Tools", 25, TEXT, 700))
    art.append(text(987, 33, "Frameworks, tooling and services for development and delivery", 12, MUTED, anchor="end"))
    descriptions = {
        "Laravel":"Web framework",
        "Vite":"Build tool (fast)",
        "Node.js":"Runtime & tools",
        "Composer":"PHP dependency",
        "pnpm":"Package manager",
        "Docker":"Containers",
        "GitHub Actions":"CI/CD & Automation",
    }
    for i, name in enumerate(DISPLAY_BUILD):
        x, y = 7 + i * 142, 40
        art.append(rect(x, y, 136, 65, radius=TOKENS.card_radius))
        art.append(technology_icon(name, x + 9, y + 16, 34))
        art.append(text(x + 49, y + 28, name, 14 if len(name) <= 9 else 11, TEXT, 700))
        art.append(text(x + 49, y + 47, descriptions[name], 9, MUTED))
        if name in frameworks:
            art.append(f'<rect x="{x+124}" y="{y+6}" width="5" height="5" rx="2" fill="#58cc8f"/>')
    return svg_done(art)


def currently_building(activity: dict) -> str:
    recent = activity["recent_repositories"][:3]
    art = root_svg(111, "Currently Building — recent public repositories",
                   "Three recently pushed public GitHub repositories from the validated activity snapshot. This does not claim exclusive or real-time active development.")
    art.append(line_icon("target", 11, 9, 24))
    art.append(text(49, 31, "Currently Building", 23, TEXT, 700))
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
    art.append(line_icon("pin", 11, 8, 24))
    art.append(text(49, 30, "Pinned / Selected Repositories", 23, TEXT, 700))
    art.append(text(988, 30, "Curated public projects", 12, MUTED, anchor="end"))
    for i,(name,summary,tech) in enumerate(items):
        x=8+(i%2)*498
        y=44+(i//2)*95
        art.append(rect(x,y,484,87))
        art.append(line_icon("repo", x+15, y+13, 23))
        art.append(text(x+49,y+32,name if name else "Browse other public work",18,"#cfb7ff",700))
        art.append(text(x+18,y+54,summary,13,TEXT))
        art.append(text(x+18,y+74,tech,12,MUTED))
    return svg_done(art)


def pinned_cards(portfolio: dict) -> dict[str, str]:
    """Four individually linkable public repository cards; README owns the links."""
    public_extra = {item["name"].casefold() for item in portfolio["other_repositories"]}
    options = [
        ("morocco", "morocco2030", "Multilingual tournament platform", "Laravel   ·   React"),
        ("train", "ab-train-ticket-studio", "Train ticket booking, QR / PDF", "JavaScript   ·   Vite"),
        ("pc", "PC-Full-Check", "Privacy-first Windows diagnostics", "PowerShell   ·   Windows"),
        ("recettes", "site-recettes" if "site-recettes" in public_extra else None,
         "Public web recipe project" if "site-recettes" in public_extra else "Other public work",
         "Web development" if "site-recettes" in public_extra else "Browse repositories"),
    ]
    output = {}
    for slug, name, summary, technologies in options:
        art = [
            '<svg xmlns="http://www.w3.org/2000/svg" width="490" height="110" viewBox="0 0 490 110" role="img" aria-labelledby="title desc">',
            f'<title id="title">{esc(name or "More public repositories")}</title>',
            f'<desc id="desc">{esc(summary)}. Click the card in README to open its public repository.</desc>',
            '<style>@media(prefers-reduced-motion:reduce){*{animation:none!important}}</style>',
            '<rect x="1" y="1" width="488" height="108" rx="14" fill="#171b2a" stroke="#5b526e" stroke-width="1.6"/>',
            '<path d="M19 25h18v20H19z M19 33h18" stroke="#9f89d8" stroke-width="2" fill="none"/>',
            text(49, 38, name or "More public repositories", 19, "#c9aeff", 700),
            '<rect x="393" y="18" width="75" height="27" rx="13" fill="#25263a" stroke="#49435c"/>',
            text(431, 36, "Public", 13, TEXT, 700, anchor="middle"),
            text(18, 70, summary, 15, TEXT),
            text(18, 94, technologies, 13, MUTED),
        ]
        art.append("</svg>")
        output[f"v6-pin-{slug}.svg"] = svg_done(art[:-1])
    return output


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
        **pinned_cards(portfolio),
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
