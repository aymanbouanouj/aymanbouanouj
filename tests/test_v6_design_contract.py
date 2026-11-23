"""Regression tests for the source-measured V6 profile design contract."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from v6_design_system import (
    REFERENCE_CONTENT_WIDTH,
    REFERENCE_BANDS,
    SVG_PANEL_WIDTH,
    TOKENS,
    VisualTokens,
    reference_panel_height,
    validate_reference_bands,
)


class V6ReferenceContractTests(unittest.TestCase):
    def test_reference_dimensions_are_real_and_ordered(self):
        self.assertEqual(REFERENCE_CONTENT_WIDTH, 780)
        self.assertEqual(SVG_PANEL_WIDTH, 1000)
        self.assertEqual(REFERENCE_BANDS["hero"], (53, 222))
        self.assertEqual(REFERENCE_BANDS["projects"], (696, 950))
        self.assertEqual(len(REFERENCE_BANDS), 9)
        validate_reference_bands()
        self.assertGreater(reference_panel_height("projects"),
                           reference_panel_height("metrics"))
        self.assertLess(reference_panel_height("metrics"), 105)

    def test_palette_and_project_ratio_are_shared(self):
        TOKENS.validate()
        self.assertEqual(TOKENS.background, "#0a0d18")
        self.assertEqual(TOKENS.accent, "#b46aff")
        self.assertLess(abs(TOKENS.project_card_width / TOKENS.project_card_height
                            - 245 / 218), .1)
        with self.assertRaises(ValueError):
            VisualTokens(background="red").validate()
        with self.assertRaises(KeyError):
            reference_panel_height("native-github-header")

    def test_live_renderer_and_project_renderer_use_tokens(self):
        dashboard = (ROOT / "scripts/live_dashboard_v6.py").read_text(encoding="utf-8")
        projects = (ROOT / "scripts/live_project_cards_v6.py").read_text(encoding="utf-8")
        self.assertIn("from v6_design_system import TOKENS", dashboard)
        self.assertIn('reference_panel_height("metrics")', dashboard)
        self.assertIn("from v6_design_system import TOKENS", projects)
        self.assertIn("TOKENS.project_card_width", projects)
        self.assertIn("TOKENS.image_pending", projects)
        self.assertIn("ImageOps.fit", projects)
        self.assertIn("blob_sha(raw)", projects)
        # The raster generator must not use a new external image service.
        self.assertNotIn("unsplash.com", projects)
        self.assertNotIn("images.openai.com", projects)

    def test_interactions_remain_real_and_untrusted_counts_not_hardcoded(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        before = readme.split("v6-metrics.svg", 1)[0]
        self.assertNotIn('src="./assets/link-github.svg"', before)
        self.assertIn('href="https://aymanbouanouj.github.io/portfolio-ayman/"', before)
        self.assertIn('href="https://www.linkedin.com/in/aymanbounaouj/"', before)
        for card in ("morocco", "train", "pc"):
            self.assertIn("profile-live/live/v6-feature-"+card+".png", readme)
        self.assertNotIn("1,082", readme.split("<details>",1)[0])


if __name__ == "__main__":
    unittest.main()
