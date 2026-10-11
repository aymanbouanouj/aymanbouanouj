#!/usr/bin/env python3
"""Build a safe, self-hosted snapshot of publicly visible GitHub activity.

Only public GitHub REST data is used. No scraping, user PAT, or private
repository names. Designed for a generated branch, never for direct main pushes.
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
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

OWNER = "aymanbouanouj"
API = "https://api.github.com"
SOURCE = "github-rest-public-repository-activity"
REPO_LIMIT = 6
EVENT_LIMIT = 4
NAME = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
SHA = re.compile(r"^[a-fA-F0-9]{40}$")
ALLOWED_EVENTS = {
    "PushEvent": "Pushed commits",
    "CreateEvent": "Created ref or repository",
    "PullRequestEvent": "Pull request activity",
    "ReleaseEvent": "Published release",
    "IssuesEvent": "Issue activity",
}


def iso_utc(value: str) -> dt.datetime:
    if not isinstance(value, str):
        raise ValueError("Missing event date")
    date = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if date.tzinfo is None:
        raise ValueError("Event date has no timezone")
    return date.astimezone(dt.timezone.utc)


def request_json(url: str, token: str, opener=urlopen):
    if not url.startswith(API + "/"):
        raise ValueError("Refusing non-GitHub API request")
    if not token or len(token.strip()) < 10:
        raise RuntimeError("An ephemeral GITHUB_TOKEN is required")
    request = Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "User-Agent": "AB-Profile-PublicActivity/4.0",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with opener(request, timeout=25) as response:
        return json.load(response)


def repository_url(name: str) -> str:
    if not isinstance(name, str) or not NAME.fullmatch(name) or name == OWNER:
        raise ValueError("Invalid public repository name")
    return "https://github.com/" + OWNER + "/" + quote(name, safe="")


def collect(fetch, *, now=None):
    repos = []
    for page in range(1, 11):
        data = fetch(f"{API}/users/{OWNER}/repos?type=owner&sort=pushed&direction=desc&per_page=100&page={page}")
        if not isinstance(data, list):
            raise ValueError("Repository API did not return a list")
        repos.extend(data)
        if len(data) < 100:
            break
    else:
        raise ValueError("Incomplete public repository pagination")
    seen = set()
    public = []
    for repo in repos:
        if not isinstance(repo, dict):
            raise ValueError("Unexpected repository record")
        name = repo.get("name")
        if repo.get("private") is not False or repo.get("disabled") is True:
            continue
        if not isinstance(repo.get("owner"), dict) or repo["owner"].get("login", "").lower() != OWNER.lower():
            continue
        if name == OWNER:
            continue
        url = repository_url(name)
        if name.casefold() in seen:
            raise ValueError("Duplicate public repository")
        seen.add(name.casefold())
        stamp = repo.get("pushed_at") or repo.get("created_at")
        when = iso_utc(stamp)
        branch = repo.get("default_branch") or "main"
        if not isinstance(branch, str) or len(branch) > 140 or not re.fullmatch(r"[A-Za-z0-9_./-]+", branch):
            raise ValueError("Untrusted default branch")
        public.append({"name": name, "url": url, "last_push": when.isoformat(),
                       "branch": branch})
    public.sort(key=lambda repo: (repo["last_push"], repo["name"].lower()), reverse=True)
    for repo in public[:REPO_LIMIT]:
        name = repo["name"]
        path = f"{API}/repos/{OWNER}/{quote(name, safe='')}/commits?sha={quote(repo['branch'], safe='')}&per_page=1"
        try:
            commits = fetch(path)
        except HTTPError as exc:
            if exc.code in (404, 409):  # An empty public repository can have no commit.
                commits = []
            else:
                raise
        if not isinstance(commits, list):
            raise ValueError("Invalid public commit result")
        if commits:
            commit_sha = commits[0].get("sha") if isinstance(commits[0], dict) else None
            if not isinstance(commit_sha, str) or not SHA.fullmatch(commit_sha):
                raise ValueError("Invalid commit SHA")
            repo["commit_sha"] = commit_sha.lower()
            repo["commit_url"] = repo["url"] + "/commit/" + repo["commit_sha"]
    events = fetch(f"{API}/users/{OWNER}/events/public?per_page=100")
    if not isinstance(events, list):
        raise ValueError("Public event API returned invalid data")
    activity = []
    for event in events:
        if not isinstance(event, dict) or event.get("type") not in ALLOWED_EVENTS:
            continue
        full = (event.get("repo") or {}).get("name")
        if not isinstance(full, str) or "/" not in full:
            continue
        owner, name = full.split("/", 1)
        if owner.lower() != OWNER.lower() or not NAME.fullmatch(name) or name == OWNER:
            continue
        stamp = iso_utc(event.get("created_at")).isoformat()
        activity.append({"type": event["type"], "repository": name,
                         "url": repository_url(name), "at": stamp})
        if len(activity) >= EVENT_LIMIT:
            break
    clock = now or dt.datetime.now(dt.timezone.utc)
    if clock.tzinfo is None:
        raise ValueError("Naive clock")
    output = {"schema": 1, "source": SOURCE, "owner": OWNER,
              "generated_at_utc": clock.astimezone(dt.timezone.utc).isoformat(),
              "public_repository_count": len(public),
              "recent_repositories": public[:REPO_LIMIT],
              "recent_events": activity}
    validate(output)
    return output


def validate(data):
    if not isinstance(data, dict) or data.get("schema") != 1 or data.get("source") != SOURCE or data.get("owner") != OWNER:
        raise ValueError("Unverified activity snapshot")
    iso_utc(data["generated_at_utc"])
    repos = data.get("recent_repositories")
    events = data.get("recent_events")
    if type(data.get("public_repository_count")) is not int or not 0 <= data["public_repository_count"] <= 1000:
        raise ValueError("Impossible repository count")
    if not isinstance(repos, list) or len(repos) > REPO_LIMIT or not isinstance(events, list) or len(events) > EVENT_LIMIT:
        raise ValueError("Invalid result sizes")
    if data["public_repository_count"] < len(repos):
        raise ValueError("Invalid count")
    for row in repos:
        if row.get("url") != repository_url(row.get("name")):
            raise ValueError("Untrusted URL")
        iso_utc(row.get("last_push"))
        if row.get("commit_sha") is not None:
            if not SHA.fullmatch(row["commit_sha"]) or row.get("commit_url") != row["url"] + "/commit/" + row["commit_sha"]:
                raise ValueError("Invalid commit provenance")
    for event in events:
        if event.get("type") not in ALLOWED_EVENTS or event.get("url") != repository_url(event.get("repository")):
            raise ValueError("Invalid public event")
        iso_utc(event.get("at"))


def draw(snapshot):
    validate(snapshot)
    esc = lambda value: html.escape(str(value), quote=True)
    pieces = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="715" viewBox="0 0 1000 715" role="img" aria-labelledby="title desc">',
        '<title id="title">Automatically refreshed public GitHub development activity</title>',
        '<desc id="desc">Recent public repositories, latest public commits and events. A dated snapshot, not real-time data.</desc>',
        '<style>@keyframes fade{from{opacity:0}to{opacity:1}}.line{animation:fade .4s ease both}@media(prefers-reduced-motion:reduce){.line{animation:none!important}}</style>',
        '<rect width="1000" height="715" rx="18" fill="#0d1117"/>',
        '<rect x="1" y="1" width="998" height="713" rx="17" fill="none" stroke="#30363d"/>',
        '<text x="32" y="56" font-size="30" font-weight="bold" fill="#f0f6fc" font-family="Arial,sans-serif">RECENT PUBLIC DEVELOPMENT</text>',
        f'<text x="32" y="88" font-size="17" fill="#b392f0" font-family="monospace">{snapshot["public_repository_count"]} public original/fork repos · GitHub REST verified</text>',
        '<text x="32" y="130" font-size="23" font-weight="bold" fill="#e6edf3" font-family="Arial,sans-serif">Recently pushed repositories</text>',
    ]
    repos = snapshot["recent_repositories"]
    for i, row in enumerate(repos):
        y = 171 + i * 50
        short = row.get("commit_sha", "")[:9] or "empty"
        date = row["last_push"][:10]
        pieces.append(f'<g class="line" style="animation-delay:{i*0.04:.2f}s">'
                      f'<rect x="25" y="{y-25}" width="950" height="44" rx="8" fill="#161b22"/>'
                      f'<text x="43" y="{y+3}" font-size="21" fill="#e6edf3" font-family="Arial,sans-serif">{esc(row["name"][:36])}</text>'
                      f'<text x="645" y="{y+3}" font-size="18" fill="#a8b3c5" font-family="monospace">{date} · {short}</text></g>')
    if not repos:
        pieces.append('<text x="43" y="184" font-size="20" fill="#a8b3c5">No public repositories available</text>')
    pieces.append('<path d="M25 495 H975" stroke="#30363d"/>')
    pieces.append('<text x="32" y="530" font-size="23" font-weight="bold" fill="#e6edf3" font-family="Arial,sans-serif">Recent public events</text>')
    for i, row in enumerate(snapshot["recent_events"][:3]):
        y = 567 + i * 35
        label = ALLOWED_EVENTS[row["type"]]
        pieces.append(f'<text x="43" y="{y}" font-size="19" fill="#b392f0" font-family="Arial,sans-serif">{esc(label)} · {esc(row["repository"][:36])} · {row["at"][:10]}</text>')
    if not snapshot["recent_events"]:
        pieces.append('<text x="43" y="567" font-size="19" fill="#a8b3c5">No recent public events in the available GitHub feed</text>')
    when = esc(snapshot["generated_at_utc"][:16].replace("T", " ") + " UTC")
    pieces.append(f'<text x="32" y="692" font-size="17" fill="#a8b3c5" font-family="monospace">Snapshot: {when} · GitHub/CDN cache may delay display · Public data only</text>')
    pieces.append('</svg>')
    svg = "".join(pieces)
    ET.fromstring(svg)
    if len(svg.encode("utf-8")) >= 75_000:
        raise ValueError("Activity card too large")
    return svg


def write_snapshot(folder: Path, snapshot):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "activity.json").write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (folder / "activity.svg").write_text(draw(snapshot) + "\n", encoding="utf-8")


def verify(folder: Path):
    snap = json.loads((folder / "activity.json").read_text(encoding="utf-8"))
    expected = draw(snap) + "\n"
    svg = (folder / "activity.svg").read_text(encoding="utf-8")
    if svg != expected:
        raise ValueError("Generated SVG does not correspond to verified GitHub snapshot")
    return snap


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build", action="store_true")
    mode.add_argument("--verify", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.build:
        token = os.environ.get("GITHUB_TOKEN", "")
        write_snapshot(args.output, collect(lambda url: request_json(url, token)))
    verify(args.output)
    print("PASS: verified public activity data and deterministic SVG")


if __name__ == "__main__":
    main()
