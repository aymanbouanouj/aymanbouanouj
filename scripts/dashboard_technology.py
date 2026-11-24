"""Collect public evidence for the two dashboard technology grids."""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote

from dashboard_data import ROOT, read_json, write_snapshot
from engineering import dependency_names
from live_profile import API, OWNER, SHA, request_json

SEED = ROOT / "data/dashboard-technology.json"
SOURCE = "github-rest-public-dashboard-technology"
STACK_ORDER = ("PHP", "JavaScript", "TypeScript", "Python", "HTML", "CSS",
               "MySQL", "Laravel", "React", "Docker", "Playwright", "Tailwind CSS", "PowerShell")
TOOL_LABELS = (
    ("Laravel", "Web framework"), ("Vite", "Build tool"), ("Node.js", "JS runtime"),
    ("Composer", "PHP packages"), ("pnpm", "JS packages"), ("Docker", "CI services"),
    ("GitHub Actions", "CI and delivery"), ("Playwright", "Browser testing"),
)
LANGUAGES = {"PHP", "JavaScript", "TypeScript", "Python", "HTML", "CSS", "PowerShell"}
NODE_PACKAGES = {"typescript": "TypeScript", "react": "React", "vite": "Vite",
                 "tailwindcss": "Tailwind CSS", "@playwright/test": "Playwright",
                 "playwright": "Playwright"}

# Same public projects and reviewed upstream work as the dashboard. Only these
# paths are read, and file contents never become part of the public snapshot.
REPOSITORIES = {
    f"{OWNER}/morocco2030": ("composer.json", "package.json", ".env.example", ".github/workflows/ci.yml"),
    f"{OWNER}/ab-train-ticket-studio": ("package.json",),
    f"{OWNER}/PC-Full-Check": (),
    f"{OWNER}/{OWNER}": (),
    f"{OWNER}/gestion-vaccination": (".github/workflows/tests.yml", "Dockerfile"),
    "Egonex-AI/Understand-Anything": ("understand-anything-plugin/packages/dashboard/package.json", "package.json"),
}
FILE_TECHNOLOGIES = {
    "composer.json": {"PHP", "Composer", "Laravel"},
    "package.json": {*NODE_PACKAGES.values(), "Node.js", "pnpm"},
    ".env.example": {"MySQL"},
    "Dockerfile": {"Docker"},
    "ci.yml": {"GitHub Actions", "Node.js", "Docker"},
    "tests.yml": {"GitHub Actions", "Node.js", "Docker"},
}
FILE_LIMIT = 128_000


def optional(fetch, url: str):
    try:
        return fetch(url)
    except HTTPError as exc:
        exc.close()
        if exc.code != 404:
            raise
        return None


def file_contents(data: dict, path: str) -> str:
    if (not isinstance(data, dict) or data.get("type") != "file" or data.get("path") != path
            or data.get("encoding") != "base64" or type(data.get("size")) is not int
            or not 0 <= data["size"] <= FILE_LIMIT or not isinstance(data.get("content"), str)
            or len(data["content"]) > FILE_LIMIT * 2):
        raise ValueError("Invalid GitHub evidence file")
    raw = base64.b64decode("".join(data["content"].splitlines()), validate=True)
    if len(raw) != data["size"]:
        raise ValueError("GitHub evidence file is incomplete")
    return raw.decode("utf-8")


def has_container_service(text: str) -> bool:
    for services in re.finditer(r"(?m)^( +)services:[ \t]*(?:#.*)?$", text):
        indent = len(services[1])
        for line in text[services.end():].splitlines():
            value = line.lstrip(" ")
            if not value or value.startswith("#"):
                continue
            if len(line) - len(value) <= indent:
                break
            if re.fullmatch(r"image:[ \t]+['\"]?[\w./-]+:[\w.-]+['\"]?[ \t]*(?:#.*)?", value):
                return True
    return False


def detect(path: str, text: str) -> set[str]:
    name = path.rsplit("/", 1)[-1]
    if name == "composer.json":
        requires = dependency_names(name, text)
        return {"Composer"} | {tech for package, tech in (("php", "PHP"), ("laravel/framework", "Laravel"))
                               if package in requires}
    if name == "package.json":
        declared = dependency_names(name, text)
        detected = {tech for package, tech in NODE_PACKAGES.items() if package in declared}
        metadata = json.loads(text)
        engines = metadata.get("engines")
        if isinstance(engines, dict) and isinstance(engines.get("node"), str) and engines["node"].strip():
            detected.add("Node.js")
        manager = metadata.get("packageManager")
        if isinstance(manager, str) and re.fullmatch(r"pnpm@\d[^\s]*", manager):
            detected.add("pnpm")
        return detected
    if name == ".env.example":
        return {"MySQL"} if re.search(r"(?mi)^DB_CONNECTION\s*=[ \t]*mysql[ \t]*(?:#.*)?$", text) else set()
    if name == "Dockerfile":
        return {"Docker"} if re.search(r"(?mi)^FROM[ \t]+\S+", text) else set()
    if re.search(r"(?m)^jobs:[ \t]*(?:#.*)?$", text):
        detected = {"GitHub Actions"}
        if re.search(r"(?m)^\s*-?\s*uses:[ \t]+['\"]?actions/setup-node@[^\s'\"]+", text):
            detected.add("Node.js")
        if has_container_service(text):
            detected.add("Docker")
        return detected
    return set()


def collect(fetch) -> dict:
    evidence: dict[str, list[dict]] = {}

    def record(technologies, repository, path, **extra):
        for name in sorted(technologies):
            evidence.setdefault(name, []).append({"repository": repository, "path": path, **extra})

    for repository, files in REPOSITORIES.items():
        url = f"{API}/repos/{repository}"
        meta = optional(fetch, url)
        if meta is None:
            continue
        if (not isinstance(meta, dict) or not isinstance(meta.get("full_name"), str)
                or meta["full_name"].casefold() != repository.casefold()
                or type(meta.get("private")) is not bool
                or meta.get("visibility") not in ("public", "private", "internal")):
            raise ValueError("Invalid GitHub evidence repository")
        if meta["private"] or meta["visibility"] != "public":
            continue
        languages = fetch(url + "/languages")
        if not isinstance(languages, dict) or any(type(n) is not int or n < 0 for n in languages.values()):
            raise ValueError("Invalid GitHub language breakdown")
        record((name for name in LANGUAGES if languages.get(name, 0) > 0), repository, "languages")
        if not files:
            continue
        commits = fetch(url + "/commits?per_page=1")
        if not isinstance(commits, list) or not commits or not isinstance(commits[0], dict):
            raise ValueError("Missing public repository commit")
        ref = commits[0].get("sha")
        if not isinstance(ref, str) or not SHA.fullmatch(ref):
            raise ValueError("Invalid public repository commit")
        for path in files:
            file = optional(fetch, f"{url}/contents/{quote(path)}?ref={ref}")
            if file is not None:
                record(detect(path, file_contents(file, path)), repository, path, ref=ref)

    return {"schema": 1, "source": SOURCE,
            "evidence": {name: sorted(entries, key=lambda row: (row["repository"], row["path"]))
                         for name, entries in sorted(evidence.items())}}


def validate(data: dict) -> dict:
    if (not isinstance(data, dict) or set(data) != {"schema", "source", "evidence"}
            or type(data["schema"]) is not int or data["schema"] != 1 or data["source"] != SOURCE
            or not isinstance(data["evidence"], dict)):
        raise ValueError("Invalid technology evidence format")
    for name, rows in data["evidence"].items():
        if not isinstance(rows, list) or not rows:
            raise ValueError("Each technology needs public evidence")
        seen = set()
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Invalid technology evidence record")
            repo, path = row.get("repository"), row.get("path")
            if not isinstance(repo, str) or repo not in REPOSITORIES or not isinstance(path, str):
                raise ValueError("Unknown technology evidence source")
            if path == "languages":
                valid = set(row) == {"repository", "path"} and name in LANGUAGES
            else:
                ref = row.get("ref")
                valid = (set(row) == {"repository", "path", "ref"} and path in REPOSITORIES[repo]
                         and name in FILE_TECHNOLOGIES[path.rsplit("/", 1)[-1]]
                         and isinstance(ref, str) and SHA.fullmatch(ref))
            if not valid or (repo, path) in seen:
                raise ValueError("Unverifiable or duplicate technology evidence")
            seen.add((repo, path))
    return data


def grid_items(data: dict, *, tools: bool = False) -> tuple[tuple[str, str], ...]:
    evidence = data["evidence"]
    choices = TOOL_LABELS if tools else tuple((name, "") for name in STACK_ORDER)
    return tuple(item for item in choices if item[0] in evidence)[:7 if tools else 12]


def refresh(fetch, previous: Path | None = None, *, require_live: bool = False) -> tuple[dict, str]:
    try:
        return validate(collect(fetch)), "live GitHub evidence"
    except (OSError, ValueError, RuntimeError):
        if require_live:
            raise
        if previous is not None:
            try:
                return validate(read_json(previous)), "last verified snapshot"
            except (OSError, ValueError):
                pass
        return validate(read_json(SEED)), "checked-in verified snapshot"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--require-live", action="store_true")
    args = parser.parse_args()
    token = os.getenv("GITHUB_TOKEN", "")
    try:
        snapshot, source = refresh(lambda url: request_json(url, token), args.previous,
                                   require_live=args.require_live)
        write_snapshot(args.output, snapshot)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"Technology evidence refresh failed: {exc}\n")
    print(f"Technology evidence: {source}. {len(snapshot['evidence'])} verified technologies.")


if __name__ == "__main__":
    main()
