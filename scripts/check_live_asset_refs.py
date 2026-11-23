#!/usr/bin/env python3
"""Fail CI if a README references missing profile-live assets.

The first V6 preview used image URLs before their files existed. This release
check prevents that failure from silently recurring. Read-only; no secrets,
tokens or private repository metadata are written to disk or logs.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "https://raw.githubusercontent.com/aymanbouanouj/aymanbouanouj/profile-live/live/"
CONTENT_URL = "https://api.github.com/repos/aymanbouanouj/aymanbouanouj/contents/live?ref=profile-live"
PATTERN = re.compile(r'<img\\b[^>]*\\bsrc\\s*=\\s*["\\']' + re.escape(PREFIX) + r'([^"\\']+)["\\']', re.IGNORECASE)


def referenced_live_files(markdown: str) -> set[str]:
    found = set()
    for name in PATTERN.findall(markdown):
        name = name.split("?", 1)[0]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,150}\\.(?:svg|png|webp|jpg|jpeg)", name):
            raise ValueError("Invalid live-artifact reference in README")
        found.add(name)
    return found


def missing_live_files(markdown: str, available: set[str]) -> list[str]:
    return sorted(referenced_live_files(markdown) - available)


def public_list(token: str) -> set[str]:
    if not token or len(token) < 10:
        raise ValueError("Missing read-only GitHub API token")
    request = Request(CONTENT_URL, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "User-Agent": "ayman-profile-readme-v6-integrity/1.0",
    })
    with urlopen(request, timeout=20) as response:
        content = response.read(200_000)
        if len(content) >= 200_000:
            raise ValueError("Unexpectedly large live-artifact response")
    payload = json.loads(content)
    if not isinstance(payload, list) or len(payload) > 1000:
        raise ValueError("Unexpected GitHub contents list")
    names = set()
    for row in payload:
        if (not isinstance(row, dict) or row.get("type") != "file"
            or not isinstance(row.get("name"), str)
            or not isinstance(row.get("path"), str)
            or row["path"] != "live/" + row["name"]):
            raise ValueError("Untrusted live-asset listing")
        names.add(row["name"])
    return names


def main() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    expected = referenced_live_files(readme)
    if not expected:
        raise ValueError("README has no live SVG or PNG references")
    missing = missing_live_files(readme, public_list(os.environ.get("GITHUB_TOKEN", "")))
    if missing:
        raise ValueError("README references unpublished profile-live images: " + ", ".join(missing))
    print("PASS: all {} referenced profile-live image assets are published".format(len(expected)))


if __name__ == "__main__":
    main()
