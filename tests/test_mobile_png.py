"""Mobile PNG migration contracts; no network or rasterizer needed to test."""
import json
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from mobile_png import (COMPONENTS, DARK, LIGHT, dimensions,
                        replace_readme, verify, stamp_image_versions, PNG_HEADER)


class MobilePngTests(unittest.TestCase):
    def test_source_markdown_migrates_six_sections_atomically(self):
        current = (ROOT / "README.md").read_text(encoding="utf-8")
        if all(f'./assets/mobile/{item}.png' in current for item in COMPONENTS):
            self.assertEqual(current, replace_readme(current))
            return
        migrated = replace_readme(current)
        self.assertNotIn("#gh-dark-mode-only", migrated)
        self.assertNotIn("#gh-light-mode-only", migrated)
        self.assertIn("Original scalable SVGs:", migrated)
        for name in COMPONENTS:
            with self.subTest(name=name):
                self.assertEqual(
                    migrated.count(f'src="./assets/mobile/{name}.png?v=') if (ROOT / "assets/mobile/manifest.json").exists() else migrated.count(f'src="./assets/mobile/{name}.png"'), 1
                )
        self.assertEqual(migrated, replace_readme(migrated))

    def test_image_cache_keys_match_current_verified_hashes(self):
        manifest_path = ROOT / "assets/mobile/manifest.json"
        if not manifest_path.exists():
            return
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for name in COMPONENTS:
            digest = manifest["images"][name]["png_sha256"][:12]
            self.assertEqual(readme.count(f'./assets/mobile/{name}.png?v={digest}"'), 1)
        self.assertEqual(stamp_image_versions(readme), readme)
        hero_digest = manifest["images"]["hero"]["png_sha256"][:12]
        stale = readme.replace(f'hero.png?v={hero_digest}', 'hero.png?v=000000000000')
        self.assertNotEqual(stale, readme)
        self.assertEqual(stamp_image_versions(stale), readme)

    def test_partial_migration_is_not_accepted(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        if "assets/mobile/hero.png" in readme:
            with self.assertRaises(ValueError):
                replace_readme(readme.replace(
                    "./assets/mobile/hero.png", "./assets/mobile/missing.png"
                ))
        else:
            with self.assertRaises(ValueError):
                replace_readme(readme.replace(
                    "./assets/hero-light.svg#gh-light-mode-only",
                    "./assets/other-light.svg#gh-light-mode-only",
                    1,
                ))

    def test_png_header_checks(self):
        good = PNG_HEADER + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 20, 30) + b"\x08\x06\x00\x00\x00" + b"\x00\x00\x00\x00"
        self.assertEqual(dimensions(good), (20, 30))
        with self.assertRaises(ValueError):
            dimensions(b"broken")
        with self.assertRaises(ValueError):
            dimensions(good.replace(struct.pack(">II", 20, 30), struct.pack(">II", 9999, 10)))

    def test_published_assets_are_verified_if_present(self):
        manifest = ROOT / "assets" / "mobile" / "manifest.json"
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        if manifest.exists():
            verify()
            for name in COMPONENTS:
                self.assertIn(f'./assets/mobile/{name}.png', readme)
        else:
            self.assertNotIn('./assets/mobile/hero.png', readme)


if __name__ == "__main__":
    unittest.main()
