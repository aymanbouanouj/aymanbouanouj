#!/usr/bin/env python3
"""Verified public-only profile portfolio derived from GitHub API and reviewed project choices."""
from __future__ import annotations
import argparse
import datetime as dt
import html
import json
import os
from pathlib import Path
from xml.etree import ElementTree as ET
from live_profile import API, OWNER, SOURCE, collect, request_json, repository_url

FEATURED = {"morocco2030", "pc-full-check", "violetgate", "ayman-calc"}
EXTERNAL = ("HichamFaska", "SGA-BTS", 1)
TOP = 7
OUTPUT = ("portfolio.json", "portfolio-tech.svg", "portfolio-projects.svg", "portfolio-collabs.svg")


def fetch_public(fetch):
    data = collect(fetch)
    repos = data["recent_repositories"]
    all_owned = []
    for page in range(1, 11):
        rows = fetch(f"{API}/users/{OWNER}/repos?type=owner&sort=pushed&direction=desc&per_page=100&page={page}")
        if not isinstance(rows, list):
            raise ValueError("Bad repository listing")
        for r in rows:
            if r.get("private") is False and r.get("fork") is False and r.get("archived") is False and r.get("owner", {}).get("login", "").lower() == OWNER:
                repository_url(r["name"])
                all_owned.append(r)
        if len(rows) < 100:
            break
    all_owned.sort(key=lambda r: r.get("pushed_at") or "", reverse=True)
    totals = {}
    for r in all_owned:
        langs = fetch(f"{API}/repos/{OWNER}/{r['name']}/languages")
        if not isinstance(langs, dict):
            raise ValueError("Invalid language response")
        for language, count in langs.items():
            if not isinstance(language, str) or not 1 <= len(language) <= 50 or type(count) is not int or count < 0:
                raise ValueError("Untrusted language bytes")
            totals[language] = totals.get(language, 0) + count
    other = [{"name": r["name"], "url": repository_url(r["name"])}
             for r in all_owned if r["name"].casefold() not in FEATURED and r["name"] != OWNER][:TOP]
    user, repo, number = EXTERNAL
    external = fetch(f"{API}/repos/{user}/{repo}/pulls/{number}")
    collabs = []
    if isinstance(external, dict) and external.get("user", {}).get("login", "").lower() == OWNER and external.get("merged_at"):
        collabs.append({"name": f"{user}/{repo}", "number": number,
                        "title": str(external.get("title", "Merged contribution"))[:100],
                        "url": f"https://github.com/{user}/{repo}/pull/{number}"})
    langs = sorted(totals.items(), key=lambda row: (-row[1], row[0]))
    result = {"schema": 1, "source": SOURCE, "owner": OWNER,
              "generated_at_utc": data["generated_at_utc"], "language_bytes": langs[:12],
              "other_repositories": other, "verified_collaborations": collabs}
    validate(result)
    return result


def validate(data):
    if data.get("schema") != 1 or data.get("owner") != OWNER or data.get("source") != SOURCE:
        raise ValueError("Untrusted portfolio source")
    dt.datetime.fromisoformat(data["generated_at_utc"].replace("Z", "+00:00"))
    if len(data["other_repositories"]) > TOP or len(data["language_bytes"]) > 12:
        raise ValueError("Unbounded portfolio")
    for row in data["other_repositories"]:
        if row.get("url") != repository_url(row.get("name")) or row["name"].casefold() in FEATURED:
            raise ValueError("Untrusted project")
    for language, count in data["language_bytes"]:
        if type(count) is not int or count < 0 or not isinstance(language, str) or len(language) > 50:
            raise ValueError("Untrusted language")
    for row in data["verified_collaborations"]:
        if row.get("name") != "HichamFaska/SGA-BTS" or row.get("number") != 1 or row.get("url") != "https://github.com/HichamFaska/SGA-BTS/pull/1":
            raise ValueError("Untrusted external evidence")


def render(title, subtitle, rows, stamp):
    escape = lambda s: html.escape(str(s), quote=True)
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="360" viewBox="0 0 1000 360" role="img" aria-labelledby="t d">',
             f'<title id="t">{escape(title)}</title><desc id="d">{escape(subtitle)}. Verified public data.</desc>',
             '<style>@media(prefers-reduced-motion:reduce){*{animation:none!important}}</style>',
             '<rect width="1000" height="360" rx="18" fill="#0d1117"/>',
             '<rect x="1" y="1" width="998" height="358" rx="17" fill="none" stroke="#30363d"/>',
             f'<text x="32" y="57" font-family="Arial,sans-serif" font-size="34" font-weight="bold" fill="#f3f6ff">{escape(title)}</text>',
             f'<text x="34" y="86" font-family="Arial,sans-serif" font-size="17" fill="#b39cfa">{escape(subtitle)}</text>']
    for i, label in enumerate(rows[:7]):
        x=33+(i%2)*485
        y=137+(i//2)*52
        parts.extend([f'<rect x="{x}" y="{y-31}" width="450" height="43" rx="8" fill="#171e2c"/>',
                      f'<text x="{x+15}" y="{y-3}" fill="#e2e8f5" font-size="21" font-family="Arial,sans-serif">{escape(label[:38])}</text>'])
    parts += [f'<text x="32" y="345" font-size="15" fill="#9aa8c1" font-family="monospace">Verified: {escape(stamp[:16].replace("T"," "))} UTC · Public source only · Snapshots are not real-time</text>',
              '</svg>']
    svg="".join(parts)
    ET.fromstring(svg)
    return svg+"\n"


def draw(data):
    validate(data)
    total=sum(n for _,n in data["language_bytes"]) or 1
    language_labels=[f"{name} · {n/total:.1%} of detected bytes" for name,n in data["language_bytes"][:7]]
    return {
        "portfolio-tech.svg": render("LANGUAGES IN PUBLIC CODE","GitHub Linguist · byte share, not skill level",language_labels,data["generated_at_utc"]),
        "portfolio-projects.svg": render("OTHER PUBLIC PROJECTS","Latest original repositories · excludes selected projects",[r["name"] for r in data["other_repositories"]],data["generated_at_utc"]),
        "portfolio-collabs.svg": render("OPEN-SOURCE CONTRIBUTIONS","Only individually verified merged external pull requests",[c["name"]+" · PR #"+str(c["number"]) for c in data["verified_collaborations"]],data["generated_at_utc"])
    }


def write(folder, data):
    folder.mkdir(parents=True, exist_ok=True)
    for name, contents in draw(data).items():
        (folder/name).write_text(contents, encoding="utf-8")
    (folder/"portfolio.json").write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")


def verify(folder):
    data=json.loads((folder/"portfolio.json").read_text(encoding="utf-8"))
    for name, contents in draw(data).items():
        if (folder/name).read_text(encoding="utf-8") != contents:
            raise ValueError("Portfolio artifact mismatch: "+name)
    return data


def main():
    p=argparse.ArgumentParser()
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--build",action="store_true")
    g.add_argument("--verify",action="store_true")
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.build:
        token=os.getenv("GITHUB_TOKEN","")
        write(a.output,fetch_public(lambda url: request_json(url,token)))
    verify(a.output)
    print("PASS: public-only profile portfolio verified")


if __name__=="__main__":
    main()
