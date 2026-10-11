"""Contribution live publishing uses only verified GraphQL aggregate counters."""
import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from live_contributions import render, verify
from render_profile import validate_live_snapshot


class LiveContributionsTests(unittest.TestCase):
    def fixture(self):
        data = json.loads((ROOT / "tests/fixtures/demo-data.json").read_text())
        # Fixture is only for offline tests; no demo data is ever published.
        data["source"] = "github-graphql-contributionCalendar"
        data["fetched_at_utc"] = "2026-10-11T03:00:00+00:00"
        return data

    def test_deterministic_verified_art(self):
        data = self.fixture()
        svg = render(data)
        self.assertIn("contributions.svg", svg)
        self.assertIn("stats.svg", svg)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, body in svg.items():
                (root / name).write_text(body, encoding="utf-8")
            self.assertEqual(verify(root)["total_contributions"], data["total_contributions"])
            (root / "stats.svg").write_text("tampered", encoding="utf-8")
            with self.assertRaises(ValueError):
                verify(root)

    def test_fake_sources_and_totals_rejected(self):
        data = self.fixture()
        for fake in (
            {**data, "source": "fixture"},
            {**data, "total_contributions": 123456789},
            {**data, "username": "someone-else"},
        ):
            with self.assertRaises(ValueError):
                render(fake)

    def test_live_workflow_does_not_push_main(self):
        w = (ROOT / ".github/workflows/profile-live.yml").read_text(encoding="utf-8")
        self.assertIn("live_contributions.py --build", w)
        self.assertIn("live_contributions.py", w)
        self.assertIn("live/contributions.svg", w)
        self.assertIn("live/stats.svg", w)
        self.assertNotIn("git push origin HEAD:main", w)
        self.assertNotIn("pull_request_target:", w)
        self.assertIn("refs/heads/profile-live", w)


if __name__ == "__main__":
    unittest.main()
