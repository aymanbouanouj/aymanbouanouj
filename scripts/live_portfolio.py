#!/usr/bin/env python3
"""Publish independently verified public GitHub languages, projects and merged PRs.

Only content already public on GitHub is eligible. A GitHub API error aborts
publication rather than replacing previously verified output with empty cards.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from xml.etree import ElementTree as ET

from live_profile import API, OWNER, SOURCE, NAME, iso_utc, request_json, repository_url

FEATURED = {"morocco2030", "pc-full-check", "violetgate", "ayman-calc"}
KNOWN_PUBLIC_PR = ("HichamFaska", "SGA-BTS", 1)
TOP = 7
COLLAB_LIMIT = 5
OUTPUT = ("portfolio.json", "portfolio-tech.svg", "portfolio-projects.svg",
          "portfolio-collabs.svg")
TARGET = re.compile(r"^https://api\.github\.com/repos/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)$")


def _public_original_repos(fetch):
    found = []
    for page in range(1, 11):
        address = f"{API}/users/{OWNER}/repos?type=owner&sort=pushed&direction=desc&per_page=100&page={page}"
        data = fetch(address)
        if not isinstance(data, list):
            raise ValueError("Expected public repository listing")
        for repo in data:
            if not isinstance(repo, dict):
                raise ValueError("Malformed public repository")
            if (repo.get("private") is not False or repo.get("fork") is not False
                    or repo.get("archived") is not False
                    or repo.get("disabled") is True):
                continue
            if (repo.get("owner") or {}).get("login", "").casefold() != OWNER.casefold():
                continue
            name = repo.get("name")
            if name == OWNER:
                continue  # This README's own Python shouldn't dominate project language ratios.
            repository_url(name)  # Canonical URL is recomputed; never trusts API HTML URLs.
            iso_utc(repo.get("pushed_at") or repo.get("created_at"))
            found.append(repo)
        if len(data) < 100:
            break
    else:
        raise ValueError("More than 1000 repositories; refusing truncated results")
    names = [r["name"].casefold() for r in found]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate public repositories")
    return sorted(found, key=lambda r: (r.get("pushed_at") or "", r["name"]), reverse=True)


def _verified_external_pr(fetch, owner, repo, number, checked):
    if (not NAME.fullmatch(owner) or not NAME.fullmatch(repo)
            or owner.casefold() == OWNER.casefold()
            or type(number) is not int or not 1 <= number <= 1_000_000_000):
        return None
    full = f"{owner}/{repo}"
    if full not in checked:
        details = fetch(f"{API}/repos/{full}")
        if not isinstance(details, dict) or details.get("private") is not False:
            checked[full] = False
        else:
            checked[full] = ((details.get("owner") or {}).get("login", "").casefold() == owner.casefold()
                             and details.get("name", "").casefold() == repo.casefold())
    if not checked[full]:
        return None
    info = fetch(f"{API}/repos/{full}/pulls/{number}")
    if not isinstance(info, dict):
        raise ValueError("Invalid external PR response")
    if (not info.get("merged_at") or
            (info.get("user") or {}).get("login", "").casefold() != OWNER.casefold() or
            info.get("number") != number):
        return None
    iso_utc(info["merged_at"])
    return {"name": full, "number": number,
            "url": f"https://github.com/{full}/pull/{number}",
            "merged_at": iso_utc(info["merged_at"]).isoformat()}


def _external_collaborations(fetch):
    search = urlencode({"q": f"type:pr is:merged author:{OWNER}", "sort": "updated",
                        "order": "desc", "per_page": 50})
    query = fetch(f"{API}/search/issues?{search}")
    if not isinstance(query, dict) or not isinstance(query.get("items"), list):
        raise ValueError("Incomplete merged pull request search")
    candidates = [KNOWN_PUBLIC_PR]  # independently verified, even if search index lags
    for item in query["items"]:
        if not isinstance(item, dict):
            raise ValueError("Invalid PR search entry")
        ref = TARGET.fullmatch(str(item.get("repository_url", "")))
        number = item.get("number")
        if ref and type(number) is int:
            candidates.append((ref.group(1), ref.group(2), number))
    checked, found, seen = {}, [], set()
    for owner, repo, number in candidates:
        key = (owner.casefold(), repo.casefold(), number)
        if key in seen:
            continue
        seen.add(key)
        record = _verified_external_pr(fetch, owner, repo, number, checked)
        if record is not None:
            found.append(record)
    found.sort(key=lambda r: (r["merged_at"], r["name"].casefold(), r["number"]), reverse=True)
    return found[:COLLAB_LIMIT]


FRAMEWORK_DEPENDENCIES = {
    "laravel/framework": "Laravel",
    "tailwindcss": "Tailwind CSS",
    "vite": "Vite",
    "react": "React",
}
MANIFESTS = ("composer.json", "package.json")
ICONS = Path(__file__).with_name("tech_icon_paths.json")


def _manifest_frameworks(fetch, repos):
    """Return frameworks that are actually declared in public dependency manifests."""
    import base64
    verified = {}
    for repo in repos:
        name = quote(repo["name"], safe="")
        for manifest in MANIFESTS:
            try:
                response = fetch(f"{API}/repos/{OWNER}/{name}/contents/{manifest}")
            except HTTPError as exc:
                if exc.code == 404:
                    continue
                raise
            if (not isinstance(response, dict) or response.get("type") != "file"
                    or response.get("encoding") != "base64"
                    or type(response.get("size")) is not int
                    or response["size"] > 256000):
                raise ValueError("Invalid manifest metadata")
            content = base64.b64decode(response.get("content", ""), validate=False)
            if len(content) > 256000:
                raise ValueError("Oversized manifest")
            data = json.loads(content.decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Invalid dependency manifest")
            fields = ("require",) if manifest == "composer.json" else ("dependencies", "devDependencies")
            for field in fields:
                values = data.get(field, {})
                if not isinstance(values, dict):
                    raise ValueError("Invalid dependencies")
                for dependency in values:
                    framework = FRAMEWORK_DEPENDENCIES.get(str(dependency).lower())
                    if framework:
                        verified.setdefault(framework, set()).add(repo["name"])
    return [{"name": name, "repositories": sorted(repos, key=str.casefold)}
            for name, repos in sorted(verified.items())]


def _icons():
    content = json.loads(ICONS.read_text(encoding="utf-8"))["icons"]
    if not isinstance(content, dict):
        raise ValueError("Icon registry invalid")
    return content



def _technology_svg(data):
    def esc(value):
        return (str(value)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', '&quot;'))

    def short_label(name):
        specials = {
            "JavaScript": "JS",
            "PowerShell": "PS",
            "Tailwind CSS": "TW",
            "Laravel": "LV",
            "Python": "PY",
            "Blade": "BL",
            "HTML": "HT",
            "Hack": "HK",
            "CSS": "CSS",
            "PHP": "PHP",
            "Vite": "VT",
        }
        if name in specials:
            return specials[name]
        raw = "".join(ch for ch in str(name) if ch.isalnum())
        return (raw[:3] or "NA").upper()

    def color_for(name, is_framework=False):
        palette = {
            "PHP": "#a993ff",
            "Blade": "#ff7a90",
            "Python": "#ffd24a",
            "PowerShell": "#6ea2ff",
            "CSS": "#9a8cff",
            "JavaScript": "#f3e341",
            "HTML": "#ff8a65",
            "Hack": "#a1ff72",
            "Laravel": "#ff735c",
            "Tailwind CSS": "#45d7ff",
            "Vite": "#c4a2ff",
        }
        return palette.get(name, '#8b949e' if is_framework else '#58a6ff')

    langs = list(data.get("language_bytes") or [])
    frameworks = list(data.get("verified_frameworks") or [])
    total = sum(int(count) for _, count in langs if type(count) is int and count >= 0)
    language_scope = data.get("language_scope")
    scope_line = (
        "GitHub Linguist · public + selected private language aggregates"
        if language_scope == "public-plus-private"
        else "GitHub Linguist + verified public dependency manifests"
    )

    lang_cols = 4
    lang_card_w = 220
    lang_card_h = 76
    lang_gap_x = 16
    lang_gap_y = 14
    lang_rows = max(1, (len(langs) + lang_cols - 1) // lang_cols)
    lang_y = 118
    fw_title_y = lang_y + lang_rows * (lang_card_h + lang_gap_y) + 36

    fw_cols = 3
    fw_card_w = 288
    fw_card_h = 66
    fw_gap_x = 16
    fw_gap_y = 14
    fw_y = fw_title_y + 36
    fw_rows = max(1, (len(frameworks) + fw_cols - 1) // fw_cols)
    footer_y = fw_y + fw_rows * (fw_card_h + fw_gap_y) + 24
    height = footer_y + 40

    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{height}" viewBox="0 0 1000 {height}" role="img" aria-labelledby="t d">',
        '<title id="t">Verified programming languages and frameworks with adaptive layout</title>',
        '<desc id="d">All detected programming languages and verified frameworks rendered from the latest portfolio snapshot. Byte shares are descriptive, not skill ratings.</desc>',
        '<style>@media(prefers-reduced-motion:reduce){*{animation:none!important}}</style>',
        f'<rect width="1000" height="{height}" rx="18" fill="#0d1117"/>',
        f'<rect x="1" y="1" width="998" height="{height-2}" rx="17" fill="none" stroke="#30363d"/>',
        '<text x="32" y="50" fill="#f0f6fc" font-size="32" font-weight="bold" font-family="Arial,sans-serif">LANGUAGES &amp; FRAMEWORKS</text>',
        f'<text x="32" y="78" fill="#b39cfa" font-size="18" font-family="Arial,sans-serif">{esc(scope_line)}</text>',
        '<text x="32" y="112" fill="#f4f5fa" font-size="21" font-weight="bold" font-family="Arial,sans-serif">PROGRAMMING LANGUAGES</text>',
    ]

    x0 = 32
    if langs:
        for i, (name, count) in enumerate(langs):
            col = i % lang_cols
            row = i // lang_cols
            x = x0 + col * (lang_card_w + lang_gap_x)
            y = lang_y + row * (lang_card_h + lang_gap_y)
            share = f"{(count / total if total else 0):.1%} of detected bytes"
            accent = color_for(name)
            label = short_label(name)
            pieces.extend([
                f'<rect x="{x}" y="{y}" width="{lang_card_w}" height="{lang_card_h}" rx="16" fill="#111b31"/>',
                f'<rect x="{x+14}" y="{y+16}" width="46" height="46" rx="12" fill="{accent}" fill-opacity="0.22" stroke="{accent}" stroke-opacity="0.45"/>',
                f'<text x="{x+37}" y="{y+44}" text-anchor="middle" fill="{accent}" font-size="17" font-weight="bold" font-family="Arial,sans-serif">{esc(label)}</text>',
                f'<text x="{x+76}" y="{y+31}" fill="#f0f6fc" font-size="21" font-weight="bold" font-family="Arial,sans-serif">{esc(name)}</text>',
                f'<text x="{x+76}" y="{y+56}" fill="#b8c5d9" font-size="14" font-family="Arial,sans-serif">{esc(share)}</text>',
            ])
    else:
        pieces.append('<text x="32" y="150" fill="#b8c5d9" font-size="16" font-family="Arial,sans-serif">No detected languages available in the verified snapshot.</text>')

    pieces.append(f'<text x="32" y="{fw_title_y}" fill="#f4f5fa" font-size="21" font-weight="bold" font-family="Arial,sans-serif">FRAMEWORKS / BUILD TOOLS</text>')
    if frameworks:
        for i, framework in enumerate(frameworks):
            name = framework.get("name", "Unknown")
            count = len(framework["repositories"])
            col = i % fw_cols
            row = i // fw_cols
            x = x0 + col * (fw_card_w + fw_gap_x)
            y = fw_y + row * (fw_card_h + fw_gap_y)
            accent = color_for(name, True)
            label = short_label(name)
            subtitle = f"{count} verified public repository(s)"
            pieces.extend([
                f'<rect x="{x}" y="{y}" width="{fw_card_w}" height="{fw_card_h}" rx="16" fill="#111b31"/>',
                f'<rect x="{x+14}" y="{y+15}" width="42" height="42" rx="12" fill="{accent}" fill-opacity="0.22" stroke="{accent}" stroke-opacity="0.45"/>',
                f'<text x="{x+35}" y="{y+41}" text-anchor="middle" fill="{accent}" font-size="15" font-weight="bold" font-family="Arial,sans-serif">{esc(label)}</text>',
                f'<text x="{x+72}" y="{y+29}" fill="#f0f6fc" font-size="18" font-weight="bold" font-family="Arial,sans-serif">{esc(name)}</text>',
                f'<text x="{x+72}" y="{y+52}" fill="#b8c5d9" font-size="14" font-family="Arial,sans-serif">{esc(subtitle)}</text>',
            ])
    else:
        pieces.append(f'<text x="32" y="{fw_y+20}" fill="#b8c5d9" font-size="16" font-family="Arial,sans-serif">No verified public frameworks detected.</text>')

    footer = f'Checked {data.get("generated_at_utc", "")[:16]} UTC · Adaptive layout · Data are dated snapshots'
    pieces.append(f'<text x="32" y="{footer_y}" fill="#b8c5d9" font-size="13" font-family="Courier New,monospace">{esc(footer)}</text>')
    pieces.append('</svg>')
    return "".join(pieces) + "\n"

def _private_language_totals(fetch):
    """Aggregate GitHub Linguist byte counts; never return private repo identity."""
    totals = {}
    for page in range(1, 11):
        url = (f"{API}/user/repos?visibility=private&affiliation=owner"
               f"&per_page=100&page={page}")
        repos = fetch(url)
        if not isinstance(repos, list):
            raise ValueError("Invalid private repository listing")
        for repo in repos:
            if not isinstance(repo, dict):
                raise ValueError("Invalid private repository record")
            if (repo.get("private") is not True or repo.get("fork") is not False
                    or repo.get("archived") is not False or repo.get("disabled") is True
                    or (repo.get("owner") or {}).get("login", "").casefold() != OWNER.casefold()):
                continue
            name = repo.get("name")
            if not isinstance(name, str) or not NAME.fullmatch(name):
                raise ValueError("Invalid private repository identifier")
            values = fetch(f"{API}/repos/{OWNER}/{quote(name, safe='')}/languages")
            if not isinstance(values, dict):
                raise ValueError("Invalid private language totals")
            for language, count in values.items():
                if (not isinstance(language, str) or not 1 <= len(language) <= 50
                        or any(ord(char) < 32 for char in language)
                        or type(count) is not int or count < 0):
                    raise ValueError("Invalid private language byte count")
                totals[language] = totals.get(language, 0) + count
        if len(repos) < 100:
            break
    else:
        raise ValueError("Private repository listing exceeds 1000 entries")
    return totals


def collect(fetch, *, now=None, private_fetch=None):
    repos = _public_original_repos(fetch)
    languages = {}
    for repo in repos:
        name = repo["name"]
        # Trusted names are validated before being used as URL path components.
        values = fetch(f"{API}/repos/{OWNER}/{quote(name, safe='')}/languages")
        if not isinstance(values, dict):
            raise ValueError("Incomplete language scan")
        for language, n in values.items():
            if (not isinstance(language, str) or not 1 <= len(language) <= 50
                    or any(ord(ch) < 32 for ch in language)
                    or type(n) is not int or n < 0):
                raise ValueError("Untrusted GitHub Linguist data")
            languages[language] = languages.get(language, 0) + n
    # Isolate private metadata/API failures from public activity refresh.
    # Never print exception details: HTTPError URLs may contain private names.
    language_scope = "public-only"
    if private_fetch is not None:
        try:
            private_totals = _private_language_totals(private_fetch)
        except (HTTPError, URLError, ValueError, TimeoutError, OSError):
            language_scope = "public-only-private-unavailable"
        else:
            language_scope = "public-plus-private"
            for language, count in private_totals.items():
                languages[language] = languages.get(language, 0) + count
    frameworks = _manifest_frameworks(fetch, repos)
    other = [{"name": r["name"], "url": repository_url(r["name"])}
             for r in repos if r["name"].casefold() not in FEATURED][:TOP]
    clock = now or dt.datetime.now(dt.timezone.utc)
    if clock.tzinfo is None:
        raise ValueError("Naive clock")
    data = {
        "schema": 2, "source": SOURCE, "owner": OWNER,
        "generated_at_utc": clock.astimezone(dt.timezone.utc).isoformat(),
        "public_original_repository_count": len(repos),
        "language_scope": language_scope,
        "language_bytes": [[name, count] for name, count in sorted(languages.items(), key=lambda x: (-x[1], x[0]))[:12]],
        "other_repositories": other,
        "verified_frameworks": frameworks,
        "verified_collaborations": _external_collaborations(fetch),
    }
    validate(data)
    return data


def validate(data):
    if (not isinstance(data, dict) or data.get("schema") != 2 or data.get("owner") != OWNER
            or data.get("source") != SOURCE):
        raise ValueError("Unverified portfolio snapshot")
    iso_utc(data.get("generated_at_utc"))
    if data.get("language_scope", "public-only") not in (
            "public-only", "public-plus-private", "public-only-private-unavailable"):
        raise ValueError("Invalid language scope")
    n = data.get("public_original_repository_count")
    if type(n) is not int or not 0 <= n <= 1000:
        raise ValueError("Bad verified repository count")
    repos, langs, collabs = (data.get("other_repositories"),
                             data.get("language_bytes"), data.get("verified_collaborations"))
    if (not isinstance(repos, list) or len(repos) > TOP or
            not isinstance(langs, list) or len(langs) > 12 or
            not isinstance(collabs, list) or len(collabs) > COLLAB_LIMIT or len(repos) > n):
        raise ValueError("Invalid portfolio list sizes")
    seen = set()
    for entry in repos:
        if not isinstance(entry, dict):
            raise ValueError("Invalid repository entry")
        name = entry.get("name")
        if (entry.get("url") != repository_url(name) or name.casefold() in FEATURED or
                name.casefold() in seen):
            raise ValueError("Noncanonical or duplicated repository")
        seen.add(name.casefold())
    framework_rows = data.get("verified_frameworks")
    if not isinstance(framework_rows, list) or len(framework_rows)>len(FRAMEWORK_DEPENDENCIES):
        raise ValueError("Invalid framework evidence")
    framework_names=set()
    for row in framework_rows:
        if not isinstance(row,dict) or row.get("name") not in FRAMEWORK_DEPENDENCIES.values():
            raise ValueError("Unsupported framework")
        refs=row.get("repositories")
        if not isinstance(refs,list) or not refs or len(refs)>1000 or any(not isinstance(r,str) or not NAME.fullmatch(r) for r in refs):
            raise ValueError("Bad framework repository evidence")
        if row["name"] in framework_names:
            raise ValueError("Duplicated framework")
        framework_names.add(row["name"])
    for row in langs:
        if (not isinstance(row, (list, tuple)) or len(row) != 2 or
                not isinstance(row[0], str) or not 1 <= len(row[0]) <= 50 or
                any(ord(ch) < 32 for ch in row[0]) or
                type(row[1]) is not int or row[1] < 0):
            raise ValueError("Invalid language information")
    unique = set()
    for c in collabs:
        if not isinstance(c, dict):
            raise ValueError("Invalid collaboration")
        target = TARGET.fullmatch(f"{API}/repos/{c.get('name', '')}")
        number = c.get("number")
        if (not target or target.group(1).casefold() == OWNER.casefold() or
                type(number) is not int or number <= 0 or
                c.get("url") != f"https://github.com/{c['name']}/pull/{number}"):
            raise ValueError("Unverified contribution destination")
        iso_utc(c.get("merged_at"))
        if (c["name"].casefold(), number) in unique:
            raise ValueError("Duplicate collaboration")
        unique.add((c["name"].casefold(), number))


def _svg(title, subtitle, rows, stamp):
    esc = lambda value: html.escape(str(value), quote=True)
    rows = rows[:TOP] if rows else ["No verified public entries available"]
    pieces = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="360" viewBox="0 0 1000 360" role="img" aria-labelledby="t d">',
        f'<title id="t">{esc(title)}</title><desc id="d">{esc(subtitle)}. Public GitHub API snapshot.</desc>',
        '<style>@media(prefers-reduced-motion:reduce){*{animation:none!important}}</style>',
        '<rect width="1000" height="360" rx="18" fill="#0d1117"/>',
        '<rect x="1" y="1" width="998" height="358" rx="17" fill="none" stroke="#30363d"/>',
        f'<text x="32" y="55" fill="#f3f6ff" font-size="32" font-weight="bold" font-family="Arial,sans-serif">{esc(title)}</text>',
        f'<text x="32" y="88" fill="#b39cfa" font-size="18" font-family="Arial,sans-serif">{esc(subtitle)}</text>',
    ]
    for i, line in enumerate(rows):
        x, y = 33 + (i % 2) * 485, 137 + (i // 2) * 52
        pieces.append(f'<rect x="{x}" y="{y-30}" width="450" height="43" rx="8" fill="#171e2c"/>')
        pieces.append(f'<text x="{x+15}" y="{y-3}" fill="#e2e8f5" font-size="21" font-family="Arial,sans-serif">{esc(str(line)[:38])}</text>')
    pieces.append(f'<text x="32" y="345" font-size="15" fill="#9aa8c1" font-family="monospace">Snapshot {esc(stamp[:16].replace("T", " "))} UTC · GitHub public sources · cached periodically</text>')
    pieces.append('</svg>')
    svg = "".join(pieces)
    root = ET.fromstring(svg)
    if root.tag != "{http://www.w3.org/2000/svg}svg" or len(svg.encode("utf-8")) > 80_000:
        raise ValueError("Invalid generated image")
    return svg + "\n"


def draw(data):
    validate(data)
    total = sum(amount for _, amount in data["language_bytes"])
    names = ([f"{name} · {amount / total:.1%} of code bytes" for name, amount in data["language_bytes"][:7]]
             if total else [])
    return {
        "portfolio-tech.svg": _technology_svg(data),
        "portfolio-projects.svg": _svg("OTHER PUBLIC PROJECTS",
                                      f"{data['public_original_repository_count']} public originals · latest non-featured projects",
                                      [r["name"] for r in data["other_repositories"]],
                                      data["generated_at_utc"]),
        "portfolio-collabs.svg": _svg("VERIFIED OPEN-SOURCE WORK",
                                     "Merged external pull requests · source verified",
                                     [f"{r['name']} · PR #{r['number']}"
                                      for r in data["verified_collaborations"]],
                                     data["generated_at_utc"]),
    }


def render_markdown(data):
    """Deterministic linked text snapshot for GitHub, not an in-README JavaScript widget."""
    validate(data)
    from urllib.parse import quote
    def clean(value):
        return "".join(c if c.isalnum() or c in " ._-/+" else " " for c in str(value))[:80]
    n = sum(v for _, v in data["language_bytes"])
    private_mode = data.get("language_scope") == "public-plus-private"
    lines = ["# Verified Public Development Inventory", "",
             "Automatically generated from public GitHub sources at " + data["generated_at_utc"][:16] + " UTC.",
             "Refreshed hourly (best effort), not a real-time counter.", "",
             "## Programming Languages", "",
             "| Language | Detected bytes | Share | Public code |",
             "| --- | ---: | ---: | --- |"]
    if private_mode:
        lines += ["The language distribution includes aggregated statistics from accessible, selected private repositories. Private repository names and source code are not published.", ""]
    elif data.get("language_scope") == "public-only-private-unavailable":
        lines += ["Private language statistics were unavailable during this refresh; the figures below include public repositories only.", ""]
    for name, amount in data["language_bytes"]:
        search = "https://github.com/search?q=" + quote("user:" + OWNER + " language:" + name, safe="") + "&type=repositories"
        source = "[Public examples](" + search + "); private portion not publicly verifiable" if private_mode else "[Source](" + search + ")"
        lines.append("| " + clean(name) + " | " + str(amount) + " | " + format(amount/n if n else 0, ".1%") + " | " + source + " |")
    if not data["language_bytes"]:
        lines.append("| No public languages detected | — | — | — |")
    lines += ["", "## Verified Frameworks and Build Tools", ""]
    for item in data["verified_frameworks"]:
        links = ", ".join("[" + clean(repo) + "](https://github.com/" + OWNER + "/" + quote(repo, safe="") + ")" for repo in item["repositories"])
        lines.append("- " + clean(item["name"]) + " — " + links)
    if not data["verified_frameworks"]:
        lines.append("No verified public dependency manifests.")
    lines += ["", "## Other Public Projects", ""]
    for item in data["other_repositories"]:
        lines.append("- [" + clean(item["name"]) + "](" + item["url"] + ")")
    if not data["other_repositories"]:
        lines.append("No additional public projects detected.")
    lines += ["", "## Verified External Contributions", ""]
    for item in data["verified_collaborations"]:
        lines.append("- [" + clean(item["name"]) + " PR #" + str(item["number"]) + "](" + item["url"] + ") — merged")
    if not data["verified_collaborations"]:
        lines.append("No independently verified external merged PRs found.")
    lines += ["", "---", "",
              "[Public repositories](https://github.com/" + OWNER + "?tab=repositories) · [GitHub profile](https://github.com/" + OWNER + ")", "",
              "No private repository metadata or fabricated proficiency ratings.", ""]
    value = "\n".join(lines)
    if len(value.encode("utf-8")) > 80000:
        raise ValueError("Oversized Markdown")
    return value


def write(folder: Path, data):
    folder.mkdir(parents=True, exist_ok=True)
    for name, svg in draw(data).items():
        (folder / name).write_text(svg, encoding="utf-8")
    (folder / "portfolio.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    (folder / "portfolio.md").write_text(render_markdown(data), encoding="utf-8")

def repair_markdown(folder: Path) -> bool:
    """Synchronize markdown with the final JSON after a no-change restore."""
    data = json.loads((folder / "portfolio.json").read_text(encoding="utf-8"))
    expected = render_markdown(data)
    path = folder / "portfolio.md"
    if path.exists() and path.read_text(encoding="utf-8") == expected:
        return False
    path.write_text(expected, encoding="utf-8")
    return True


def verify(folder: Path):
    data = json.loads((folder / "portfolio.json").read_text(encoding="utf-8"))
    for name, svg in draw(data).items():
        if (folder / name).read_text(encoding="utf-8") != svg:
            raise ValueError("Public GitHub portfolio data/art mismatch: " + name)
    if (folder / "portfolio.md").read_text(encoding="utf-8") != render_markdown(data):
        raise ValueError("Generated Markdown does not match verified API snapshot")
    return data


def main():
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--build", action="store_true")
    action.add_argument("--verify", action="store_true")
    action.add_argument("--repair-markdown", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.build:
        token = os.getenv("GITHUB_TOKEN", "")
        private_token = os.getenv("PRIVATE_LANGUAGE_TOKEN", "")
        private_fetch = (lambda url: request_json(url, private_token)) if private_token else None
        write(args.output, collect(lambda url: request_json(url, token),
                                   private_fetch=private_fetch))
    if args.repair_markdown:
        repair_markdown(args.output)
    verify(args.output)
    print("PASS: public GitHub languages, repositories and external contributions verified")


if __name__ == "__main__":
    main()
