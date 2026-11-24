"""Refresh the dashboard grids and reuse the same public evidence for V5."""
from __future__ import annotations

import argparse
import base64
import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from xml.etree import ElementTree as ET

import live_portfolio
from dashboard_data import ROOT, read_json, write_snapshot
from engineering import dependency_names
from live_profile import API, NAME, OWNER, SHA, request_json
from technology_detection import DEPENDENCIES, LOCKFILES, detect, evidence_kind, file_labels, safe_label

SEED = ROOT / "data/dashboard-technology.json"
SOURCE = "github-rest-public-dashboard-technology"
STACK_ORDER = ("PHP", "JavaScript", "TypeScript", "Python", "HTML", "CSS",
               "MySQL", "Laravel", "React", "Docker", "Playwright", "Tailwind CSS", "PowerShell")
TOOL_LABELS = (
    ("Laravel", "Web framework"), ("Vite", "Build tool"), ("Node.js", "JS runtime"),
    ("Composer", "PHP packages"), ("pnpm", "JS packages"), ("Docker", "CI services"),
    ("GitHub Actions", "CI and delivery"), ("Playwright", "Browser testing"),
)
TOOL_CAPTIONS = {name: "Framework" for name in DEPENDENCIES.values() if name not in ("PHP", "TypeScript")}
TOOL_CAPTIONS.update({name: "Package manager" for name in LOCKFILES.values()})
TOOL_CAPTIONS.update({name: "Build tool" for name in ("Gradle", "Maven", "webpack", "Rollup", "Cargo")})
TOOL_CAPTIONS.update({name: "Static checks" for name in ("Biome", "ESLint", "Prettier")})
TOOL_CAPTIONS.update({name: "Testing" for name in ("PHPUnit", "Pest", "pytest", "Vitest", "Jest", "Cypress")})
TOOL_CAPTIONS.update({name: "CI and delivery" for name in ("GitLab CI", "CircleCI", "Azure Pipelines")})
TOOL_CAPTIONS.update({"Docker Compose": "Containers", "Rails": "Web framework", "Bundler": "Ruby packages"})
TOOL_CAPTIONS.update(TOOL_LABELS)

OWNED = "public-owned"
EXTERNAL = "verified-external"
PRIVATE = "private-language-aggregate"
FILE_LIMIT = 256_000
EXTERNAL_REPOSITORY = "Egonex-AI/Understand-Anything"
EXTERNAL_PULL = 794
EXTERNAL_FILES = ("package.json", "understand-anything-plugin/packages/dashboard/package.json")
# Only the historical schema uses the fixed evidence paths and approved grid limits.
LEGACY_FILES = {
    "morocco2030": ("composer.json", "package.json", ".env.example", ".github/workflows/ci.yml"),
    "ab-train-ticket-studio": ("package.json",), "pc-full-check": (), OWNER: (), "aymanbouanouj": (),
    "gestion-vaccination": (".github/workflows/tests.yml", "Dockerfile"),
}
LEGACY_LANGUAGES = {"PHP", "JavaScript", "TypeScript", "Python", "HTML", "CSS", "PowerShell"}
LEGACY_FILE_LABELS = {
    "composer.json": {"PHP", "Composer", "Laravel"},
    "package.json": {"TypeScript", "React", "Vite", "Tailwind CSS", "Playwright", "Node.js", "pnpm"},
    ".env.example": {"MySQL"}, "Dockerfile": {"Docker"},
    "ci.yml": {"GitHub Actions", "Node.js", "Docker"}, "tests.yml": {"GitHub Actions", "Node.js", "Docker"},
}


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


def latest_commit(fetch, url, *, allow_empty=False):
    try:
        commits = fetch(url + "/commits?per_page=1")
    except HTTPError as exc:
        if allow_empty and exc.code == 409:
            exc.close()
            return None  # GitHub reports an empty repository as a conflict on the commits endpoint.
        raise
    if allow_empty and commits == []:
        return None
    if not isinstance(commits, list) or not commits or not isinstance(commits[0], dict):
        raise ValueError("Missing public repository commit")
    ref = commits[0].get("sha")
    if not isinstance(ref, str) or not SHA.fullmatch(ref):
        raise ValueError("Invalid public repository commit")
    return ref


def listed_files(fetch, url, ref):
    response = fetch(f"{url}/git/trees/{ref}?recursive=1")
    if (not isinstance(response, dict) or response.get("truncated") is not False
            or not isinstance(response.get("tree"), list)):
        raise ValueError("Incomplete GitHub repository tree")
    paths = {}
    for entry in response["tree"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise ValueError("Invalid GitHub tree record")
        path = entry["path"]
        kind = evidence_kind(path)
        if kind is None or entry.get("type") != "blob" or entry.get("mode") not in {"100644", "100755"}:
            continue
        size = entry.get("size")
        if path in paths or type(size) is not int or size < 0:
            raise ValueError("Invalid GitHub evidence path")
        if size:
            paths[path] = kind
    return dict(sorted(paths.items()))


def read_file(fetch, url, path, ref):
    return file_contents(fetch(f"{url}/contents/{quote(path)}?ref={ref}"), path)


def record(evidence, labels, **proof):
    for label in sorted(labels):
        if not safe_label(label):
            raise ValueError("Invalid technology label")
        evidence.setdefault(label, []).append(proof.copy())


@dataclass
class OwnedEvidence:
    evidence: dict
    portfolio_repos: list
    portfolio_languages: Counter
    portfolio_frameworks: dict

    def portfolio(self, fetch, private_summary):
        frameworks = [{"name": name, "repositories": sorted(repos, key=str.casefold)}
                      for name, repos in sorted(self.portfolio_frameworks.items())]
        return live_portfolio.portfolio_snapshot(fetch, self.portfolio_repos, self.portfolio_languages,
                                                 frameworks, private_summary)


def discover_owned(fetch) -> OwnedEvidence:
    owned = OwnedEvidence({}, [], Counter(), defaultdict(set))
    for repo in live_portfolio.public_original_repos(fetch, include_profile=True):
        name = repo["name"]
        repository = f"{OWNER}/{name}"
        url = f"{API}/repos/{repository}"
        language_counts = live_portfolio.public_languages(fetch, name)
        if any(not safe_label(language) for language in language_counts):
            raise ValueError("Invalid GitHub Linguist label")
        positive = {language for language, count in language_counts.items() if count > 0}
        record(owned.evidence, positive, scope=OWNED, repository=repository, path="languages")

        is_project = name.casefold() != OWNER.casefold()
        if is_project:
            owned.portfolio_repos.append(repo)
            owned.portfolio_languages.update(language_counts)
        ref = latest_commit(fetch, url, allow_empty=not positive and repo.get("size") == 0)
        if ref is None:
            continue
        for path, kind in listed_files(fetch, url, ref).items():
            if kind == "lock":
                labels = {LOCKFILES[Path(path).name]}
            else:
                content = read_file(fetch, url, path, ref)
                labels = detect(path, content)
                if is_project and path in live_portfolio.MANIFESTS:
                    v5_rules = live_portfolio.FRAMEWORK_DEPENDENCIES
                    for dependency in dependency_names(path, content) & v5_rules.keys():
                        owned.portfolio_frameworks[v5_rules[dependency]].add(name)
            record(owned.evidence, labels, scope=OWNED, repository=repository, path=path, ref=ref)
    return owned


def add_external(fetch, evidence):
    url = f"{API}/repos/{EXTERNAL_REPOSITORY}"
    try:
        metadata = fetch(url)
        name = metadata.get("full_name") if isinstance(metadata, dict) else None
        if not isinstance(name, str) or name.casefold() != EXTERNAL_REPOSITORY.casefold():
            raise ValueError("Unverified external repository")
        if metadata.get("private") is not False or metadata.get("visibility") != "public":
            return
        pull = fetch(f"{url}/pulls/{EXTERNAL_PULL}")
    except HTTPError as exc:
        if exc.code != 404:
            raise
        exc.close()
        return
    if (not isinstance(pull, dict) or pull.get("number") != EXTERNAL_PULL
            or not isinstance(pull.get("user"), dict) or not isinstance(pull.get("base"), dict)):
        raise ValueError("Unverified external pull request")
    author = pull["user"].get("login")
    base_repo = pull["base"].get("repo")
    base_name = base_repo.get("full_name") if isinstance(base_repo, dict) else None
    if not isinstance(author, str) or not isinstance(base_name, str):
        raise ValueError("Missing external pull request identity")
    if author.casefold() != OWNER.casefold() or base_name.casefold() != EXTERNAL_REPOSITORY.casefold():
        return
    ref = latest_commit(fetch, url)
    for path in EXTERNAL_FILES:
        try:
            text = read_file(fetch, url, path, ref)
        except HTTPError as exc:
            if exc.code != 404:
                raise
            exc.close()
            continue
        record(evidence, detect(path, text), scope=EXTERNAL, repository=EXTERNAL_REPOSITORY,
               path=path, ref=ref, pull_request=EXTERNAL_PULL)


def snapshot(fetch, owned, private_summary):
    totals, scope = private_summary
    if scope == "public-only-private-unavailable":
        raise RuntimeError("Authorized private language aggregate unavailable")
    evidence = {label: list(rows) for label, rows in owned.evidence.items()}
    add_external(fetch, evidence)
    record(evidence, (label for label, count in totals.items() if count > 0), scope=PRIVATE)
    return validate({"schema": 2, "source": SOURCE, "evidence": {
        label: sorted(rows, key=lambda proof: (proof["scope"], proof.get("repository", ""), proof.get("path", "")))
        for label, rows in sorted(evidence.items())
    }})


def collect(fetch, *, private_fetch=None):
    owned = discover_owned(fetch)
    return snapshot(fetch, owned, live_portfolio.private_language_summary(private_fetch))


def historical_proof(label, proof):
    repo, path = proof.get("repository"), proof.get("path")
    if not isinstance(repo, str) or not isinstance(path, str) or repo.count("/") != 1:
        return False
    owner, name = repo.lower().split("/")
    files = LEGACY_FILES.get(name) if owner in {OWNER.lower(), "aymanbouanouj"} else None
    if repo == EXTERNAL_REPOSITORY:
        files = EXTERNAL_FILES
    if files is None:
        return False
    if path == "languages":
        return set(proof) == {"repository", "path"} and label in LEGACY_LANGUAGES
    ref = proof.get("ref")
    return (set(proof) == {"repository", "path", "ref"} and path in files
            and label in LEGACY_FILE_LABELS[path.rsplit("/", 1)[-1]]
            and isinstance(ref, str) and SHA.fullmatch(ref) is not None)


def current_proof(label, proof):
    scope = proof.get("scope")
    if scope == PRIVATE:
        return set(proof) == {"scope"}
    repo, path = proof.get("repository"), proof.get("path")
    if not isinstance(repo, str) or not isinstance(path, str) or repo.count("/") != 1:
        return False
    owner, name = repo.split("/")
    if scope == OWNED and (owner != OWNER or not NAME.fullmatch(name) or name in {".", ".."}):
        return False
    if path == "languages":
        return scope == OWNED and set(proof) == {"scope", "repository", "path"}
    ref = proof.get("ref")
    if not isinstance(ref, str) or not SHA.fullmatch(ref) or label not in file_labels(path):
        return False
    fields = {"scope", "repository", "path", "ref"}
    if scope == EXTERNAL:
        return (set(proof) == fields | {"pull_request"} and repo == EXTERNAL_REPOSITORY
                and path in EXTERNAL_FILES and proof["pull_request"] == EXTERNAL_PULL)
    return scope == OWNED and set(proof) == fields


def validate(data: dict) -> dict:
    if (not isinstance(data, dict) or set(data) != {"schema", "source", "evidence"}
            or type(data["schema"]) is not int or data["schema"] not in (1, 2) or data["source"] != SOURCE
            or not isinstance(data["evidence"], dict)):
        raise ValueError("Invalid technology evidence format")
    proof_ok = historical_proof if data["schema"] == 1 else current_proof
    for label, rows in data["evidence"].items():
        if not safe_label(label) or not isinstance(rows, list) or not rows:
            raise ValueError("Each technology needs verified evidence")
        seen = set()
        for proof in rows:
            if not isinstance(proof, dict) or not proof_ok(label, proof):
                raise ValueError("Unverifiable technology evidence")
            identity = (proof.get("scope"), proof.get("repository"), proof.get("path"))
            if identity in seen:
                raise ValueError("Duplicate technology evidence")
            seen.add(identity)
    return data


def grid_items(data: dict, *, tools: bool = False) -> tuple[tuple[str, str], ...]:
    evidence = data["evidence"]
    ordered = dict(TOOL_LABELS) if tools else dict.fromkeys(STACK_ORDER, "")
    if data.get("schema", 1) == 1:
        # Keep already-published v1 snapshots and artwork reproducible during migration and fallback.
        return tuple((name, caption) for name, caption in ordered.items() if name in evidence)[:7 if tools else 12]
    if tools:
        ordered.update({name: TOOL_CAPTIONS[name] for name in sorted(evidence, key=lambda n: (n.casefold(), n))
                        if name in TOOL_CAPTIONS and name not in ordered})
    else:
        ordered.update({name: "" for name in sorted(evidence, key=lambda n: (n.casefold(), n)) if name not in ordered
                        and (name not in TOOL_CAPTIONS or any(row.get("path") == "languages" or row["scope"] == PRIVATE
                                                              for row in evidence[name]))})
    return tuple((name, caption) for name, caption in ordered.items() if name in evidence)


def fallback(previous):
    if previous is not None:
        try:
            return validate(read_json(previous)), "last verified snapshot"
        except (OSError, ValueError):
            pass
    return validate(read_json(SEED)), "checked-in verified snapshot"


def refresh(fetch, previous: Path | None = None, *, require_live=False, private_fetch=None, portfolio_output=None):
    fetch = cache(fetch)
    owned = None
    private_summary = {}, "public-only"
    try:
        owned = discover_owned(fetch)
        private_summary = live_portfolio.private_language_summary(private_fetch)
        result = snapshot(fetch, owned, private_summary), "live GitHub evidence"
    except (OSError, ValueError, RuntimeError, ET.ParseError):
        if require_live:
            raise
        result = fallback(previous)
    if portfolio_output is not None and owned is not None:
        try:
            historical = owned.portfolio(fetch, private_summary)
        except (OSError, ValueError, RuntimeError):
            if require_live:
                raise
            print("Legacy portfolio refresh unavailable. Retaining its verified artifacts.")
        else:
            live_portfolio.write(portfolio_output, historical)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--portfolio-output", type=Path)
    parser.add_argument("--require-live", action="store_true")
    args = parser.parse_args()
    token = os.getenv("GITHUB_TOKEN", "")
    private_token = os.getenv("PRIVATE_LANGUAGE_TOKEN", "")
    private_fetch = (lambda url: request_json(url, private_token)) if private_token else None
    try:
        verified, source = refresh(lambda url: request_json(url, token), args.previous, require_live=args.require_live,
                                   private_fetch=private_fetch, portfolio_output=args.portfolio_output)
        write_snapshot(args.output, verified)
    except (OSError, ValueError, RuntimeError, ET.ParseError) as exc:
        parser.exit(1, f"Technology evidence refresh failed: {exc}\n")
    print(f"Technology evidence: {source}. {len(verified['evidence'])} verified technologies.")


if __name__ == "__main__":
    main()
