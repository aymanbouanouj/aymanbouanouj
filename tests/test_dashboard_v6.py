"""V6 dashboard: real source schema, privacy, provenance and tamper regression."""
import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from live_dashboard_v6 import FILES, build, render, verify
from live_portfolio import SOURCE as PORTFOLIO_SOURCE
from live_profile import SOURCE as ACTIVITY_SOURCE


class VerifiedV6DashboardTests(unittest.TestCase):
    def fixture(self):
        ending = dt.date(2026, 11, 22)
        start = ending - dt.timedelta(days=364)
        days = [
            {"date": (start + dt.timedelta(days=i)).isoformat(), "count": i % 4}
            for i in range(365)
        ]
        contribution = {
            "username": "aymanbouanouj",
            "source": "github-graphql-contributionCalendar",
            "days": days,
            "total_contributions": sum(item["count"] for item in days),
            "fetched_at_utc": "2026-11-22T20:00:00+00:00",
        }
        portfolio = {
            "schema": 2, "source": PORTFOLIO_SOURCE, "owner": "aymanbouanouj",
            "generated_at_utc": "2026-11-22T21:00:00+00:00",
            "public_original_repository_count": 2,
            "language_scope": "public-plus-private",
            "language_bytes": [["PHP", 200], ["Python", 100], ["JavaScript", 50]],
            "other_repositories": [],
            "verified_frameworks": [
                {"name": "Laravel", "repositories": ["morocco2030"]},
                {"name": "Vite", "repositories": ["ab-train-ticket-studio"]},
            ],
            "verified_collaborations": [
                {"name": "php/doc-en", "number": 5930,
                 "url": "https://github.com/php/doc-en/pull/5930",
                 "merged_at": "2026-10-12T21:01:48+00:00"},
            ],
        }
        activity = {
            "schema": 1, "source": ACTIVITY_SOURCE, "owner": "aymanbouanouj",
            "generated_at_utc": "2026-11-22T21:00:00+00:00",
            "public_repository_count": 2, "recent_repositories": [],
            "recent_events": [],
        }
        return contribution, portfolio, activity

    def test_output_is_xml_deterministic_and_privacy_preserving(self):
        c, p, a = self.fixture()
        first = render(c, p, a)
        self.assertEqual(first, render(c, p, a))
        self.assertEqual(set(first), set(FILES))
        for name, svg in first.items():
            self.assertEqual(ET.fromstring(svg).tag,
                             "{http://www.w3.org/2000/svg}svg")
            self.assertIn("prefers-reduced-motion", svg)
            self.assertNotIn("<script", svg.lower())
            self.assertNotIn("confidential-repo-xyz", svg)
        self.assertIn("FRAMEWORKS / BUILD TOOLS", first["v6-stack.svg"])
        self.assertIn("Laravel", first["v6-stack.svg"])
        self.assertIn("Python", first["v6-stack.svg"])
        self.assertIn("PR #5930", first["v6-open-source.svg"])
        self.assertIn("Verified recent sample", first["v6-metrics.svg"])
        self.assertIn("Public + selected private aggregates", first["v6-stack.svg"])

    def test_calendar_labels_do_not_overlap_cells_or_legend(self):
        c, p, a = self.fixture()
        root = ET.fromstring(render(c, p, a)["v6-calendar.svg"])
        ns = {"svg":"http://www.w3.org/2000/svg"}
        labels = []
        for node in root.findall("svg:text", ns):
            if node.text in ("Jan","Feb","Mar","Apr","May","Jun",
                             "Jul","Aug","Sep","Oct","Nov","Dec"):
                labels.append(float(node.attrib["x"]))
        self.assertGreaterEqual(len(labels), 10)
        self.assertTrue(all(b - a >= 38 for a, b in zip(labels, labels[1:])))
        legend = [node for node in root.findall("svg:text", ns) if node.text == "Less"]
        self.assertEqual(len(legend), 1)
        self.assertGreaterEqual(float(legend[0].attrib["y"]), 190)
        squares = [
            node for node in root.findall("svg:rect", ns)
            if node.attrib.get("height") == "11.4"
        ]
        self.assertEqual(len(squares), 365)
        self.assertLess(max(float(el.attrib["y"])+float(el.attrib["height"]) for el in squares), 185)

    def test_semantic_icons_are_paths_not_missing_unicode_glyphs(self):
        c, p, a = self.fixture()
        out = render(c, p, a)
        for name in ("v6-metrics.svg", "v6-calendar.svg", "v6-open-source.svg",
                     "v6-building.svg", "v6-languages.svg", "v6-frameworks.svg"):
            self.assertTrue("<path d=" in out[name] or "<circle cx=" in out[name], name)
        for glyph in ("♨", "⑂", "▣", "▦", "⬡", "⚒"):
            self.assertNotIn(glyph, out["v6-metrics.svg"])
            self.assertNotIn(glyph, out["v6-calendar.svg"])

    def test_manifests_only_not_unverified_frameworks(self):
        c, p, a = self.fixture()
        p["verified_frameworks"] = []
        result = render(c, p, a)["v6-stack.svg"]
        self.assertNotIn("Laravel", result)
        self.assertIn("No frameworks verified", result)

    def test_invalid_source_and_tamper_are_rejected(self):
        c, p, a = self.fixture()
        c["total_contributions"] += 99
        with self.assertRaises(ValueError):
            render(c, p, a)
        c["total_contributions"] -= 99
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            for name, data in (("contributions.json", c), ("portfolio.json", p),
                               ("activity.json", a)):
                (path / name).write_text(json.dumps(data), encoding="utf-8")
            build(path)
            verify(path)
            file = path / "v6-metrics.svg"
            file.write_text(file.read_text(encoding="utf-8").replace(
                "Contributions", "FICTION"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not match"):
                verify(path)

    def test_readme_new_panels_are_wired_without_losing_original_feeds(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/profile-live.yml").read_text(encoding="utf-8")
        for filename in FILES:
            self.assertIn("profile-live/live/" + filename, readme)
            self.assertIn("live/" + filename, workflow)
        self.assertIn("live_dashboard_v6.py\" --build --output live", workflow)
        self.assertIn("live_dashboard_v6.py\" --verify --output live", workflow)
        self.assertIn("profile-live/live/portfolio-tech.svg", readme)
        self.assertIn("profile-live/live/portfolio-collabs.svg", readme)
        self.assertNotIn("HEAD:refs/heads/main", workflow)


if __name__ == "__main__":
    unittest.main()
