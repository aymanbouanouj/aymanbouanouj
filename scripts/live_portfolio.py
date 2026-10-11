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
from urllib.error import HTTPError
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


def collect(fetch, *, now=None):
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
    other = [{"name": r["name"], "url": repository_url(r["name"])}
             for r in repos if r["name"].casefold() not in FEATURED][:TOP]
    clock = now or dt.datetime.now(dt.timezone.utc)
    if clock.tzinfo is None:
        raise ValueError("Naive clock")
    data = {
        "schema": 2, "source": SOURCE, "owner": OWNER,
        "generated_at_utc": clock.astimezone(dt.timezone.utc).isoformat(),
        "public_original_repository_count": len(repos),
        "language_bytes": sorted(languages.items(), key=lambda x: (-x[1], x[0]))[:12],
        "other_repositories": other,
        "verified_collaborations": _external_collaborations(fetch),
    }
    validate(data)
    return data


def validate(data):
    if (not isinstance(data, dict) or data.get("schema") != 2 or data.get("owner") != OWNER
            or data.get("source") != SOURCE):
        raise ValueError("Unverified portfolio snapshot")
    iso_utc(data.get("generated_at_utc"))
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
        "portfolio-tech.svg": _svg("LANGUAGES IN PUBLIC CODE",
                                  "GitHub Linguist · measured bytes, not developer proficiency",
                                  names, data["generated_at_utc"]),
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


def write(folder: Path, data):
    folder.mkdir(parents=True, exist_ok=True)
    for name, svg in draw(data).items():
        (folder / name).write_text(svg, encoding="utf-8")
    (folder / "portfolio.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def verify(folder: Path):
    data = json.loads((folder / "portfolio.json").read_text(encoding="utf-8"))
    for name, svg in draw(data).items():
        if (folder / name).read_text(encoding="utf-8") != svg:
            raise ValueError("Public GitHub portfolio data/art mismatch: " + name)
    return data


def main():
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--build", action="store_true")
    action.add_argument("--verify", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.build:
        token = os.getenv("GITHUB_TOKEN", "")
        write(args.output, collect(lambda url: request_json(url, token)))
    verify(args.output)
    print("PASS: public GitHub languages, repositories and external contributions verified")


if __name__ == "__main__":
    main()
