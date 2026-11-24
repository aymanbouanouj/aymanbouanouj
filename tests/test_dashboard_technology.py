"""Regression coverage for the dashboard's verified technology source."""
from __future__ import annotations

import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import dashboard_technology as tech
from dashboard_data import read_json, write_snapshot

MOROCCO = f"{tech.API}/repos/{tech.OWNER}/morocco2030"
TRAIN = f"{tech.API}/repos/{tech.OWNER}/ab-train-ticket-studio"
REF = "c" * 40


def fixture_file(path, content):
    payload = content.encode("utf-8")
    return {"type": "file", "path": path, "size": len(payload), "encoding": "base64",
            "content": base64.encodebytes(payload).decode("ascii")}


def fixture():
    result = {}
    for url, languages in ((MOROCCO, {"CSS": 412, "PHP": 45, "Python": 0, "Unknown": 683}),
                           (TRAIN, {"JavaScript": 999})):
        result[url] = {"full_name": url.split("/repos/", 1)[1], "private": False, "visibility": "public"}
        result[url + "/languages"] = languages
        result[url + "/commits?per_page=1"] = [{"sha": REF}]
    files = (
        (MOROCCO, "composer.json", '{"require":{"php":"^8.2","laravel/framework":"^12.0"}}'),
        (MOROCCO, ".env.example", "# Local settings\nDB_CONNECTION=mysql\n"),
        (MOROCCO, ".github/workflows/ci.yml", "jobs:\n  tests:\n    services:\n      db:\n"
         "        image: mariadb:10.4\n    steps:\n      - uses: actions/setup-node@v7\n"),
        (TRAIN, "package.json", '{"devDependencies":{"vite":"^8","@playwright/test":"^1.56"},'
         '"packageManager":"pnpm@10.6.2"}'),
    )
    for url, path, content in files:
        result[f"{url}/contents/{path}?ref={REF}"] = fixture_file(path, content)
    return result


def fetch_from(responses):
    def fetch(url):
        if url not in responses:
            raise HTTPError(url, 404, "Not found", {}, None)
        return responses[url]
    return fetch


class DashboardTechnologyTests(unittest.TestCase):
    def test_public_evidence_drives_both_grids_in_stable_order(self):
        responses = fixture()
        snapshot = tech.validate(tech.collect(fetch_from(responses)))
        self.assertEqual(tuple(name for name, _ in tech.grid_items(snapshot)),
                         ("PHP", "JavaScript", "CSS", "MySQL", "Laravel", "Docker", "Playwright"))
        self.assertEqual(tuple(name for name, _ in tech.grid_items(snapshot, tools=True)),
                         ("Laravel", "Vite", "Node.js", "Composer", "pnpm", "Docker", "GitHub Actions"))
        self.assertEqual(snapshot["evidence"]["MySQL"], [
            {"repository": f"{tech.OWNER}/morocco2030", "path": ".env.example", "ref": REF}
        ])
        self.assertNotIn("DB_CONNECTION", json.dumps(snapshot))
        self.assertNotIn("Unknown", snapshot["evidence"])
        for url in (MOROCCO, TRAIN):
            responses[url + "/languages"] = dict(reversed(list(responses[url + "/languages"].items())))
        self.assertEqual(json.dumps(snapshot), json.dumps(tech.collect(fetch_from(responses))))

    def test_successful_removal_changes_the_grids(self):
        responses = fixture()
        del responses[f"{MOROCCO}/contents/.env.example?ref={REF}"]
        responses[TRAIN].update(private=True, visibility="private")
        snapshot = tech.validate(tech.collect(fetch_from(responses)))
        self.assertFalse({"MySQL", "Vite", "Playwright", "pnpm"} & snapshot["evidence"].keys())
        data, source = tech.refresh(fetch_from({}))
        self.assertEqual(data["evidence"], {})
        self.assertEqual(source, "live GitHub evidence")

    def test_malformed_or_misleading_evidence_is_rejected(self):
        self.assertNotIn("MySQL", tech.detect(".env.example", "# DB_CONNECTION=mysql\nDB_CONNECTION=sqlite"))
        self.assertNotIn("Docker", tech.detect(".github/workflows/tests.yml", "jobs:\n  tests:\n"
                                             "    services:\n    env:\n      image: example:123\n"))
        snapshot = tech.collect(fetch_from(fixture()))
        snapshot["evidence"]["MySQL"][0]["path"] = ".env"
        with self.assertRaises(ValueError):
            tech.validate(snapshot)

    def test_transport_and_metadata_failures_use_validated_fallback(self):
        def offline(_):
            raise URLError("API unavailable")

        snapshot = tech.collect(fetch_from(fixture()))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "technology.json"
            write_snapshot(path, snapshot)
            self.assertEqual(tech.refresh(offline, path), (snapshot, "last verified snapshot"))
            responses = fixture()
            responses[MOROCCO + "/languages"] = {"PHP": True}
            self.assertEqual(tech.refresh(fetch_from(responses), path), (snapshot, "last verified snapshot"))
            with self.assertRaises(URLError):
                tech.refresh(offline, path, require_live=True)
            path.write_text('{"evidence":{"Unknown":[]}}', encoding="utf-8")
            seed, source = tech.refresh(offline, path)
            self.assertEqual(seed, tech.validate(read_json(tech.SEED)))
            self.assertEqual(source, "checked-in verified snapshot")


if __name__ == "__main__":
    unittest.main()
