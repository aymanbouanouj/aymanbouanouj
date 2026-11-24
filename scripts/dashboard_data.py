"""Public REST metadata for the dashboard. The calendar comes from live_contributions."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

from live_profile import API, OWNER, iso_utc, request_json
from render_profile import analysis, validate_live_snapshot

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "github-rest-public-dashboard"
REPOS = (
    "morocco2030", "ab-train-ticket-studio", "PC-Full-Check", "violetgate",
    OWNER, "Understand-Anything", "gestion-vaccination",
)
CONTRIBUTIONS = (
    ("Egonex-AI/Understand-Anything", "pull", 794),
    ("OWASP/CheatSheetSeries", "issue", 2792),
    ("php/doc-en", "pull", 5930),
)
OWASP_COMMENT = 6633108162
MERGED_SEARCH = "is:pr is:merged is:public author:" + OWNER
STATUSES = {"Merged", "Open", "Closed", "Draft"}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def write_snapshot(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent,
                                     prefix=".dashboard-", delete=False) as stream:
        temporary = Path(stream.name)
    try:
        temporary.write_text(canonical_json(data), encoding="utf-8", newline="\n")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def count(value) -> int:
    if type(value) is not int or not 0 <= value <= 1_000_000_000:
        raise ValueError("Invalid GitHub count")
    return value


def contribution_url(record: tuple[str, str, int]) -> str:
    repo, kind, number = record
    if kind == "issue":
        return f"https://github.com/{repo}/issues/{number}#issuecomment-{OWASP_COMMENT}"
    return f"https://github.com/{repo}/pull/{number}"


def public_repo(fetch, full_name: str) -> dict:
    item = fetch(f"{API}/repos/{full_name}")
    if (item.get("full_name", "").casefold() != full_name.casefold()
            or item.get("private") is not False or item.get("visibility") != "public"):
        raise ValueError("Expected the canonical public GitHub repository")
    return item


def contribution_status(fetch, record: tuple[str, str, int]) -> str:
    repo, kind, number = record
    public_repo(fetch, repo)
    if kind == "issue":
        issue = fetch(f"{API}/repos/{repo}/issues/{number}")
        comment = fetch(f"{API}/repos/{repo}/issues/comments/{OWASP_COMMENT}")
        if (issue.get("number") != number or issue.get("pull_request") is not None
                or comment.get("id") != OWASP_COMMENT
                or comment.get("issue_url", "").casefold() != f"{API}/repos/{repo}/issues/{number}".casefold()
                or comment.get("user", {}).get("login", "").casefold() != OWNER):
            raise ValueError("Could not verify the author's public issue comment")
        states = {"open": "Open", "closed": "Closed"}
        if issue.get("state") not in states:
            raise ValueError("Unexpected issue state")
        return states[issue["state"]]
    pr = fetch(f"{API}/repos/{repo}/pulls/{number}")
    if (pr.get("number") != number or pr.get("user", {}).get("login", "").casefold() != OWNER
            or pr.get("state") not in {"open", "closed"} or type(pr.get("merged")) is not bool
            or (pr.get("base") or {}).get("repo", {}).get("private") is not False):
        raise ValueError("Could not verify the author's public pull request")
    if pr["merged"]:
        if pr["state"] != "closed":
            raise ValueError("GitHub returned conflicting pull request states")
        iso_utc(pr.get("merged_at"))
        return "Merged"
    if pr.get("merged_at") is not None:
        raise ValueError("GitHub returned conflicting merge evidence")
    if pr["state"] == "closed":
        return "Closed"
    return "Draft" if pr.get("draft") is True else "Open"


def collect(fetch, *, now: dt.datetime | None = None) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Snapshot clock must have a timezone")
    repositories = {}
    for name in REPOS:
        repo = public_repo(fetch, f"{OWNER}/{name}")
        repositories[name] = {
            "visibility": "public",
            "stars": count(repo.get("stargazers_count")),
            "forks": count(repo.get("forks_count")),
            "pushed_at": iso_utc(repo.get("pushed_at")).isoformat(timespec="seconds"),
        }
    search = fetch(f"{API}/search/issues?" + urlencode({"q": MERGED_SEARCH, "per_page": 1}))
    if search.get("incomplete_results") is not False:
        raise ValueError("GitHub returned an incomplete public PR search")
    data = {
        "schema": 1,
        "username": OWNER,
        "source": SOURCE,
        "fetched_at_utc": now.astimezone(dt.timezone.utc).isoformat(timespec="seconds"),
        "merged_public_prs": count(search.get("total_count")),
        "repositories": repositories,
        "contributions": {contribution_url(record): contribution_status(fetch, record)
                          for record in CONTRIBUTIONS},
    }
    validate(data, now=now)
    return data


def verified_time(value, now: dt.datetime) -> dt.datetime:
    stamp = iso_utc(value)
    if stamp > now + dt.timedelta(minutes=5) or dt.datetime.fromisoformat(value.replace("Z", "+00:00")).utcoffset() != dt.timedelta(0):
        raise ValueError("Expected a verified UTC timestamp")
    return stamp


def validate(data: dict, *, now: dt.datetime | None = None, fresh: bool = False) -> dt.datetime:
    now = now or dt.datetime.now(dt.timezone.utc)
    fields = {"schema", "username", "source", "fetched_at_utc",
              "merged_public_prs", "repositories", "contributions"}
    if (not isinstance(data, dict) or data.keys() != fields or type(data["schema"]) is not int
            or data["schema"] != 1 or data["username"] != OWNER or data["source"] != SOURCE):
        raise ValueError("Unexpected public dashboard snapshot")
    stamp = verified_time(data["fetched_at_utc"], now)
    if fresh and now - stamp > dt.timedelta(hours=36):
        raise ValueError("Public dashboard snapshot is stale")
    count(data["merged_public_prs"])
    repos = data["repositories"]
    if not isinstance(repos, dict) or repos.keys() != set(REPOS):
        raise ValueError("Public dashboard repository list does not match the approved list")
    for repo in repos.values():
        if (not isinstance(repo, dict) or repo.keys() != {"visibility", "stars", "forks", "pushed_at"}
                or repo["visibility"] != "public"):
            raise ValueError("Only public repository metadata is allowed")
        count(repo["stars"])
        count(repo["forks"])
        verified_time(repo["pushed_at"], stamp)
    statuses = data["contributions"]
    if not isinstance(statuses, dict) or statuses.keys() != {contribution_url(r) for r in CONTRIBUTIONS}:
        raise ValueError("Unexpected external contribution")
    for record in CONTRIBUTIONS:
        allowed = {"Open", "Closed"} if record[1] == "issue" else STATUSES
        value = statuses[contribution_url(record)]
        if not isinstance(value, str) or value not in allowed:
            raise ValueError("Invalid external contribution status")
    return stamp


def activity(data: dict, *, now: dt.datetime | None = None, fresh: bool = False) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    if not isinstance(data, dict) or data.keys() != {
        "username", "total_contributions", "days", "source", "fetched_at_utc",
    }:
        raise ValueError("Unexpected contribution data fields")
    for row in data["days"] if isinstance(data["days"], list) else ():
        if not isinstance(row, dict) or row.keys() != {"date", "count"}:
            raise ValueError("Only dated contribution counts may be published")
    days = validate_live_snapshot(data, now=now, require_fresh=fresh)
    stamp = verified_time(data["fetched_at_utc"], now)
    if days[-1]["date"] > stamp.date() or (stamp.date() - days[-1]["date"]).days > 1:
        raise ValueError("The calendar must end on the verification date or the day before")
    stats = analysis(data, reference_date=stamp.date())
    # Include both partial boundary months when the range crosses 13 months.
    months: dict[str, int] = {}
    for day in days:
        month = day["date"].isoformat()[:7]
        months[month] = months.get(month, 0) + day["count"]
    stats["months"] = list(months.items())
    peak = max(days, key=lambda day: (day["count"], day["date"]))
    stats["peak"] = peak if peak["count"] else None
    stats["verified_at"] = stamp
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--is-today", action="store_true", help="exit successfully for today's validated REST snapshot")
    args = parser.parse_args()
    try:
        if args.verify or args.is_today:
            now = dt.datetime.now(dt.timezone.utc)
            stamp = validate(read_json(args.output), now=now)
            if args.is_today and stamp.date() != now.date():
                parser.exit(1, "The retained dashboard was verified on an earlier UTC day.\n")
        else:
            token = os.getenv("GITHUB_TOKEN", "")
            write_snapshot(args.output, collect(lambda url: request_json(url, token)))
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, TypeError, AttributeError) as exc:
        # Response bodies and headers may contain private data or credentials.
        parser.exit(1, f"Dashboard metadata failed validation or retrieval ({type(exc).__name__}).\n")
    print("PASS: verified public repository and contribution metadata")


if __name__ == "__main__":
    main()
