"""Offline tests for the automatically published public GitHub activity card."""
import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from live_profile import OWNER, collect, draw, validate, verify, write_snapshot


class LiveProfileTests(unittest.TestCase):
    NOW = dt.datetime(2026, 10, 11, tzinfo=dt.timezone.utc)
    SHA = "0123456789abcdef" * 2 + "01234567"

    def fixture(self, *, private=False, events=True):
        repo = {"name": "new-public-project", "private": private, "disabled": False,
                "owner": {"login": OWNER}, "default_branch": "main",
                "pushed_at": "2026-10-11T10:00:00Z"}
        def fetch(url):
            if "/users/" in url and "/repos?" in url:
                return [repo]
            if "/commits?" in url:
                return [{"sha": self.SHA}]
            if "/events/public?" in url:
                return ([{"type": "PushEvent", "created_at": "2026-10-11T10:03:00Z",
                          "repo": {"name": OWNER + "/new-public-project"}}] if events else [])
            raise AssertionError("Unexpected API request: " + url)
        return fetch

    def test_public_repo_push_and_new_commit_appear(self):
        data = collect(self.fixture(), now=self.NOW)
        self.assertEqual(data["public_repository_count"], 1)
        self.assertEqual(data["recent_repositories"][0]["commit_sha"], self.SHA)
        self.assertEqual(data["recent_events"][0]["type"], "PushEvent")
        self.assertIn("new-public-project", draw(data))
        self.assertIn(self.SHA[:9], draw(data))
        self.assertNotIn("<script", draw(data).lower())
        self.assertIn('height="405"', draw(data))
        self.assertIn("LATEST PUBLIC WORK", draw(data))
        self.assertNotIn('height="715"', draw(data))

    def test_private_repository_cannot_leak(self):
        data = collect(self.fixture(private=True), now=self.NOW)
        self.assertEqual(data["public_repository_count"], 0)
        self.assertEqual(data["recent_repositories"], [])
        self.assertEqual(len(data["recent_events"]), 1)
        # In real usage GitHub's /events/public endpoint only supplies public
        # events. This test rejects an injected private repository record.
        # We must not use a private flag from the wrong API endpoint.

    def test_no_secret_or_untrusted_markup_in_svg(self):
        malicious = self.fixture()
        def fetch(url):
            data = malicious(url)
            if "/users/" in url and "/repos?" in url:
                data[0]["name"] = "bad<script>"
            return data
        with self.assertRaises(ValueError):
            collect(fetch, now=self.NOW)

    def test_provenance_and_deterministic_output(self):
        data = collect(self.fixture(events=False), now=self.NOW)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            write_snapshot(folder, data)
            self.assertEqual(verify(folder), data)
            svg = folder / "activity.svg"
            svg.write_text(svg.read_text(encoding="utf-8").replace("PUBLIC", "PRIVATE"), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify(folder)
        ET.fromstring(draw(data))

    def test_broken_repository_url_is_rejected(self):
        data = collect(self.fixture(), now=self.NOW)
        data["recent_repositories"][0]["url"] = "https://malicious.example/"
        with self.assertRaises(ValueError):
            validate(data)

    def test_live_profile_refreshes_automatically_on_schedule_and_main_merge(self):
        workflow = (ROOT / ".github/workflows/profile-live.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "37 * * * *"', workflow)
        self.assertIn("  push:\n    branches:\n      - main\n", workflow)
        self.assertIn("'README.md'", workflow)
        self.assertIn("'scripts/live_*.py'", workflow)
        self.assertIn("'scripts/tech_icon_paths.json'", workflow)
        self.assertIn("github.ref == 'refs/heads/main'", workflow)
        self.assertIn("HEAD:refs/heads/profile-live", workflow)
        self.assertNotIn("pull_request_target", workflow)
        self.assertNotIn("HEAD:refs/heads/main", workflow)

    def test_workflow_scopes_generated_branch_only(self):
        workflow = (ROOT / ".github/workflows/profile-live.yml").read_text(encoding="utf-8")
        self.assertIn("refs/heads/main", workflow)
        self.assertIn("refs/heads/profile-live", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertNotIn("git push origin HEAD:main", workflow)
        self.assertNotIn("pull_request_target", workflow)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("raw.githubusercontent.com/aymanbouanouj/aymanbouanouj/profile-live/live/activity.svg", readme)
        self.assertIn("GitHub's native contribution graph", readme)


if __name__ == "__main__":
    unittest.main()
