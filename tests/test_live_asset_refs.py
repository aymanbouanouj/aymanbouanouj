"""Checks the regression guard for published image references."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from check_live_asset_refs import referenced_live_files, missing_live_files, PREFIX

class LiveAssetReferenceTests(unittest.TestCase):
    def test_detects_missing_dynamic_image_before_merge(self):
        s='<img src="'+PREFIX+'v6-metrics.svg" /><img src="'+PREFIX+'v6-feature-pc.png" />'
        self.assertEqual(referenced_live_files(s),{"v6-metrics.svg","v6-feature-pc.png"})
        self.assertEqual(missing_live_files(s,{"v6-metrics.svg"}),["v6-feature-pc.png"])

    def test_rejects_traversal_in_live_image_reference(self):
        with self.assertRaises(ValueError):
            referenced_live_files('<img src="'+PREFIX+'../private/file.png" />')

    def test_ignores_other_external_and_local_images(self):
        self.assertEqual(referenced_live_files('<img src="./assets/brand-v6.svg" /><img src="https://example.com/img.svg" />'),set())

    def test_real_readme_references_multiple_published_images(self):
        text=(ROOT/"README.md").read_text(encoding="utf-8")
        files=referenced_live_files(text)
        self.assertIn("v6-metrics.svg",files)
        self.assertIn("v6-feature-pc.png",files)
        self.assertGreaterEqual(len(files),10)

if __name__=="__main__":
    unittest.main()
