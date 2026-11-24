from __future__ import annotations

import base64
import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import dashboard_technology as tech
import live_portfolio
from dashboard_data import read_json, write_snapshot

REF = "a" * 40
STAMP = "2026-11-24T00:00:00Z"
INVENTORY = (f"{tech.API}/users/{tech.OWNER}/repos?type=owner&sort=pushed&direction=desc"
             "&per_page=100&page=")


def repository(name, **changes):
    return {"name": name, "owner": {"login": tech.OWNER}, "size": 1, "pushed_at": STAMP,
            "private": False, "archived": False, "disabled": False, "fork": False, **changes}


def evidence_file(path, text):
    binary = text.encode()
    return {"type": "file", "path": path, "encoding": "base64", "size": len(binary),
            "content": base64.b64encode(binary).decode()}


class GitHub:
    def __init__(self):
        self.calls = Counter()
        self.responses = {INVENTORY + "1": []}

    def project(self, name, languages, files):
        base = f"{tech.API}/repos/{tech.OWNER}/{name}"
        self.responses[f"{base}/languages"] = languages
        self.responses[f"{base}/commits?per_page=1"] = [{"sha": REF}]
        self.responses[f"{base}/git/trees/{REF}?recursive=1"] = {"truncated": False, "tree": [
            {"path": path, "type": "blob", "mode": "100644", "size": len(text.encode())}
            for path, text in files.items()
        ]}
        for path, text in files.items():
            self.responses[f"{base}/contents/{path}?ref={REF}"] = evidence_file(path, text)
        return base

    def prior_collaboration(self, *, dashboard_external=False):
        prior_owner, prior_repo, prior_id = live_portfolio.KNOWN_PUBLIC_PR
        base = f"{tech.API}/repos/{prior_owner}/{prior_repo}"
        self.responses[base] = {"owner": {"login": prior_owner}, "name": prior_repo, "private": False}
        self.responses[f"{base}/pulls/{prior_id}"] = {
            "user": {"login": tech.OWNER}, "number": prior_id, "merged_at": STAMP,
        }
        upstream = f"{tech.API}/repos/{tech.EXTERNAL_REPOSITORY}"
        self.responses["merged_search"] = ({"items": [{"repository_url": upstream, "number": tech.EXTERNAL_PULL}]}
                                           if dashboard_external else {"items": []})

    def __call__(self, url):
        self.calls[url] += 1
        if url.startswith(f"{tech.API}/search/issues?"):
            return self.responses["merged_search"]
        if url not in self.responses:
            raise HTTPError(url, 404, "Not found", {}, None)
        value = self.responses[url]
        if isinstance(value, Exception):
            raise value
        return value


class DiscoveryTests(unittest.TestCase):
    def test_pagination_new_projects_and_v5_ownership_policy(self):
        api = GitHub()
        rejected = [repository(f"archive-{i}", archived=True) for i in range(97)]
        rejected.extend((repository("upstream-fork", fork=True), repository("disabled", disabled=True),
                         repository("private", private=True)))
        api.responses[INVENTORY + "1"] = rejected
        api.responses[INVENTORY + "2"] = [repository("new-weather-lab")]
        base = api.project("new-weather-lab", {"Kotlin": 150, "Scheme": 100}, {
            "app/package.json": '{"dependencies":{"vue":"^3"},"packageManager":"yarn@4.6.0"}',
            "vendor/package.json": '{"dependencies":{"react":"^18"}}',
        })
        snapshot = tech.collect(api)
        self.assertEqual(tuple(name for name, _ in tech.grid_items(snapshot)), ("Kotlin", "Scheme"))
        self.assertEqual(tuple(name for name, _ in tech.grid_items(snapshot, tools=True)), ("Vue.js", "Yarn"))
        self.assertEqual(api.calls[base + "/languages"], 1)
        self.assertNotIn("React", snapshot["evidence"])
        self.assertFalse(any("upstream-fork/" in url or "/private/" in url or "/archive-" in url for url in api.calls))

    def test_adding_and_removing_the_last_dependency_proof(self):
        api = GitHub()
        api.responses[INVENTORY + "1"] = [repository("space-weather")]
        api.project("space-weather", {"Python": 11}, {"requirements.txt": "Django~=5.1; python_version > '3.9'\n"})
        self.assertIn("Django", tech.collect(api)["evidence"])
        api.project("space-weather", {"Python": 11}, {"requirements.txt": "# Django==5\npytest==8\n"})
        data = tech.collect(api)
        self.assertNotIn("Django", data["evidence"])
        self.assertIn("pytest", data["evidence"])
        api.responses[INVENTORY + "1"] = []
        data, source = tech.refresh(api)
        self.assertEqual(data["evidence"], {})
        self.assertEqual(source, "live GitHub evidence")

    def test_manifest_coverage_and_safe_database_configuration(self):
        cases = (
            ("composer.json", '{"require":{"laravel/sanctum":"^4"},"require-dev":{"phpunit/phpunit":"^12"}}',
             {"Composer", "Laravel Sanctum", "PHPUnit"}),
            ("pyproject.toml", '[project]\ndependencies = ["fastapi[standard]>=1", "Flask>=3"]\n[tool.uv]',
             {"Python", "FastAPI", "Flask", "uv"}),
            ("go.mod", "module example.org/public/work\n", {"Go"}),
            ("Cargo.toml", '[package]\nname="demo"\n', {"Cargo", "Rust"}),
            ("docker/Dockerfile.dev", "FROM alpine:3.22\n", {"Docker"}),
            ("compose.yml", "services:\n  redis:\n    image: redis:8\n", {"Docker", "Docker Compose"}),
            (".github/workflows/ci.yaml", "jobs:\n  test:\n    steps:\n      - uses: actions/setup-node@v5\n",
             {"GitHub Actions", "Node.js"}),
            ("config/.env.example", "# DB_CONNECTION=mysql\n DB_CONNECTION=pgsql\n", {"PostgreSQL"}),
        )
        for path, text, expected in cases:
            with self.subTest(path=path):
                self.assertEqual(tech.detect(path, text), expected)
        self.assertEqual(tech.detect(".env", "DB_CONNECTION=mysql"), set())
        self.assertEqual(tech.detect(".env.example", "DB_CONNECTION=mysql-unsupported"), set())
        self.assertEqual(tech.detect("fixtures/package.json", '{"dependencies":{"vue":"3"}}'), set())
        self.assertEqual(tech.detect("requirements.txt", "react==1.0\n"), set())
        self.assertNotIn("Docker", tech.detect(".github/workflows/ci.yml", "jobs:\n  env:\n    image: dummy:1\n"))

    def test_v5_and_dashboard_share_public_fetches_and_separate_external_proofs(self):
        api = GitHub()
        api.responses[INVENTORY + "1"] = [repository("data-tools")]
        owned = api.project("data-tools", {"TypeScript": 24}, {"package.json": '{"dependencies":{"vite":"8"}}'})
        external = f"{tech.API}/repos/{tech.EXTERNAL_REPOSITORY}"
        owner, name = tech.EXTERNAL_REPOSITORY.split("/")
        api.responses[external] = {"name": name, "owner": {"login": owner}, "full_name": tech.EXTERNAL_REPOSITORY,
                                   "visibility": "public", "private": False}
        api.responses[f"{external}/pulls/{tech.EXTERNAL_PULL}"] = {
            "number": tech.EXTERNAL_PULL, "user": {"login": tech.OWNER}, "merged_at": STAMP,
            "base": {"repo": {"full_name": tech.EXTERNAL_REPOSITORY}},
        }
        api.responses[f"{external}/commits?per_page=1"] = [{"sha": REF}]
        path = tech.EXTERNAL_FILES[-1]
        api.responses[f"{external}/contents/{path}?ref={REF}"] = evidence_file(path, '{"dependencies":{"react":"19"}}')
        api.prior_collaboration(dashboard_external=True)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            result, source = tech.refresh(api, require_live=True, portfolio_output=folder)
            legacy = live_portfolio.verify(folder)
        self.assertEqual(source, "live GitHub evidence")
        self.assertEqual(legacy["verified_frameworks"], [{"name": "Vite", "repositories": ["data-tools"]}])
        self.assertEqual(result["evidence"]["React"][0]["scope"], tech.EXTERNAL)
        self.assertEqual(result["evidence"]["React"][0]["pull_request"], tech.EXTERNAL_PULL)
        self.assertEqual(api.calls[owned + "/languages"], 1)
        self.assertEqual(api.calls[f"{owned}/contents/package.json?ref={REF}"], 1)
        self.assertEqual(api.calls[f"{external}/pulls/{tech.EXTERNAL_PULL}"], 1)

    def test_private_scope_serializes_only_sanitized_label_and_aggregate_for_v5(self):
        api = GitHub()
        api.prior_collaboration()
        calls = []
        name = "confidential-private-project"

        def private(url):
            calls.append(url)
            if "/user/repos?" in url:
                return [repository(name, private=True)]
            if url.endswith(f"/{name}/languages"):
                return {"Rust": 190, "Julia": 0}
            self.fail("Private discovery requested something other than aggregate input")

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            snapshot, _ = tech.refresh(api, private_fetch=private, portfolio_output=folder, require_live=True)
            legacy = live_portfolio.verify(folder)
            self.assertNotIn(name, "".join(file.read_text(encoding="utf-8") for file in folder.iterdir()))
        self.assertEqual(len(calls), 2)
        self.assertEqual(snapshot["evidence"], {"Rust": [{"scope": tech.PRIVATE}]})
        self.assertEqual(legacy["language_bytes"], [["Rust", 190], ["Julia", 0]])
        self.assertNotIn(name, json.dumps(snapshot))
        snapshot["evidence"]["Rust"][0]["repository"] = name
        with self.assertRaises(ValueError):
            tech.validate(snapshot)

    def test_errors_and_truncated_requests_keep_last_verified_data(self):
        api = GitHub()
        api.responses[INVENTORY + "1"] = [repository("app")]
        base = api.project("app", {"Python": 10}, {})
        expected = tech.collect(api)

        def timeout(_):
            raise URLError("no response")

        with tempfile.TemporaryDirectory() as tmp:
            prior = Path(tmp) / "previous.json"
            write_snapshot(prior, expected)
            self.assertEqual(tech.refresh(timeout, prior), (expected, "last verified snapshot"))
            self.assertEqual(tech.refresh(api, prior, private_fetch=timeout), (expected, "last verified snapshot"))
            api.responses[f"{base}/git/trees/{REF}?recursive=1"] = {"truncated": True, "tree": []}
            self.assertEqual(tech.refresh(api, prior), (expected, "last verified snapshot"))
            with self.assertRaises(ValueError):
                tech.refresh(api, prior, require_live=True)
            prior.write_text('{"evidence":{"Unverified":[]}}', encoding="utf-8")
            data, source = tech.refresh(timeout, prior)
            self.assertEqual(data, read_json(tech.SEED))
            self.assertEqual(source, "checked-in verified snapshot")

    def test_shared_publisher_refreshes_technology_before_daily_retention(self):
        workflow = (ROOT / ".github/workflows/profile-live.yml").read_text(encoding="utf-8")
        hourly, daily = workflow.split("- name: Build the daily dashboard", 1)
        self.assertIn("--technology-only", hourly)
        self.assertIn("--previous", hourly)
        self.assertIn("--activity-only --verify", daily)
        staging = daily.index("git add -- cards/")
        self.assertLess(daily.index('technology-build/"*.svg'), staging)
        self.assertLess(daily.index('"$GITHUB_WORKSPACE/scripts/render_svg_cards.py" --dynamic-only --verify'), staging)


if __name__ == "__main__":
    unittest.main()
