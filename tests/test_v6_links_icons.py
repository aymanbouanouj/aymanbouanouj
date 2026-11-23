"""V6 UI contract: truthful clickable actions and vendored official brand icons."""
from __future__ import annotations
import json
import re
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
LIVE_PREFIX = "https://raw.githubusercontent.com/aymanbouanouj/aymanbouanouj/profile-live/live/"


class V6ClickableLinksAndIcons(unittest.TestCase):
    def test_hero_buttons_are_real_independent_links(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        hero = readme.split("v6-metrics.svg", 1)[0]
        self.assertIn('href="https://aymanbouanouj.github.io/portfolio-ayman/"', hero)
        self.assertIn('href="https://www.linkedin.com/in/aymanbounaouj/"', hero)
        self.assertIn('href="https://github.com/aymanbouanouj?tab=repositories"', hero)
        for name in ("portfolio", "linkedin", "projects"):
            self.assertIn('src="./assets/v6-cta-' + name + '.svg"', hero)
        self.assertNotIn('src="./assets/link-github.svg"', hero)
        self.assertNotIn('href="https://github.com/aymanbouanouj"', hero)
        art = (ROOT / "assets/brand-v6.svg").read_text(encoding="utf-8")
        for forbidden in (">GitHub</text>", ">LinkedIn</text>",
                          ">Portfolio</text>", ">Email</text>"):
            self.assertNotIn(forbidden, art)

    def test_v6_pinned_repositories_have_four_distinct_real_targets(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        scope = readme.split('<h3 align="left">Pinned / Selected Repositories</h3>', 1)[1]
        scope = scope.split("<details>", 1)[0]
        choices = {
            "morocco":"morocco2030",
            "train":"ab-train-ticket-studio",
            "pc":"PC-Full-Check",
            "recettes":"site-recettes",
        }
        for slug, name in choices.items():
            self.assertIn('href="https://github.com/aymanbouanouj/'+name+'"', scope)
            self.assertIn("profile-live/live/v6-pin-"+slug+".svg", scope)
        self.assertEqual(scope.count("<a href="), 4)
        self.assertEqual(scope.count("</a>"), 4)

    def test_vendor_icons_are_local_validated_paths(self):
        icons = json.loads((ROOT / "scripts/v6_brand_icons.json").read_text(encoding="utf-8"))
        self.assertEqual(icons["version"], 1)
        expected = ("PHP", "JavaScript", "TypeScript", "Python", "HTML", "CSS",
                    "MySQL", "Laravel", "React", "Docker", "Playwright",
                    "Tailwind CSS", "Vite", "Node.js", "Composer", "pnpm",
                    "GitHub Actions")
        for name in expected:
            item = icons["icons"][name]
            self.assertIn(item["viewBox"], (24,128))
            self.assertTrue(item["paths"])
            for path in item["paths"]:
                self.assertRegex(path["fill"], r"^#[0-9a-fA-F]{6}$")
                self.assertTrue(path["d"])
                self.assertNotIn("<", path["d"])
        self.assertGreaterEqual(len(icons["icons"]["Playwright"]["paths"]), 3)

    def test_live_workflow_tracks_four_pin_outputs_and_image_fallback(self):
        workflow = (ROOT / ".github/workflows/profile-live.yml").read_text(encoding="utf-8")
        renderer = (ROOT / "scripts/live_dashboard_v6.py").read_text(encoding="utf-8")
        preview = (ROOT / "scripts/live_project_cards_v6.py").read_text(encoding="utf-8")
        for slug in ("morocco","train","pc","recettes"):
            self.assertIn("live/v6-pin-"+slug+".svg", workflow)
            self.assertIn('"v6-pin-'+slug+'.svg"', renderer)
        self.assertIn("v6_brand_icons.json", renderer)
        self.assertIn("PROJECT IMAGE PENDING", preview)
        self.assertIn("ImageOps.fit", preview)
        self.assertIn('Image.Resampling.LANCZOS', preview)


if __name__ == "__main__":
    unittest.main()
