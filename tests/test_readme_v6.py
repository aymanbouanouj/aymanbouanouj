"""V6 README presentation, provenance and accessible artwork regression checks."""
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class V6ReadmeContract(unittest.TestCase):
    def test_primary_navigation_and_evidence(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for fragment in (
            'src="./assets/brand-v6.svg"',
            'href="#featured-projects"',
            'href="#languages--technical-stack"',
            'href="#open-source--collaborations"',
            "## Engineering Focus",
            "AB Train Ticket Studio",
            "private repository names and files are not published",
        ):
            self.assertIn(fragment, text)
        self.assertEqual(text.count("#### ["), 4)

    def test_self_hosted_brand_svg_is_safe_and_described(self):
        svg = (ROOT / "assets/brand-v6.svg").read_text(encoding="utf-8")
        root = ET.fromstring(svg)
        ns = {"svg": "http://www.w3.org/2000/svg"}
        self.assertIsNotNone(root.find("svg:title", ns))
        self.assertIsNotNone(root.find("svg:desc", ns))
        self.assertIn("prefers-reduced-motion", svg)
        self.assertIn("AYMAN BOUNAOUJ", svg)
        self.assertNotIn("<script", svg.lower())
        self.assertNotIn("https://", svg)
        self.assertNotIn("javascript:", svg.lower())
        for node in root.iter():
            for key in node.attrib:
                self.assertFalse(key.rsplit("}", 1)[-1].lower().startswith("on"))

    def test_live_data_pipeline_references_preserved(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("profile-live/live/contributions.svg", text)
        self.assertIn("profile-live/live/portfolio-tech.svg", text)
        self.assertIn("profile-live/live/portfolio-collabs.svg", text)
        self.assertIn("profile-live/live/activity.svg", text)
        self.assertIn("GitHub Linguist", text)
        self.assertNotIn("<script", text.lower())
        self.assertNotIn("http://", text)
        self.assertEqual(text.count("<details>"), text.count("</details>"))


if __name__ == "__main__":
    unittest.main()
