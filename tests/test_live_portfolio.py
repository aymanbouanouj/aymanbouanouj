"""Validation of verified public portfolio generation."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from live_portfolio import draw, verify, validate, write

class PortfolioTests(unittest.TestCase):
    def sample(self):
        return {"schema":1,"source":"github-rest-public-repository-activity","owner":"aymanbouanouj",
                "generated_at_utc":"2026-10-11T04:00:00+00:00",
                "language_bytes":[["PHP",900],["JavaScript",100]],
                "other_repositories":[{"name":"GhostTrack","url":"https://github.com/aymanbouanouj/GhostTrack"}],
                "verified_collaborations":[{"name":"HichamFaska/SGA-BTS","number":1,"url":"https://github.com/HichamFaska/SGA-BTS/pull/1"}]}
    def test_portfolio_render_and_tamper_resistance(self):
        d=self.sample()
        art=draw(d)
        self.assertIn("PHP",art["portfolio-tech.svg"])
        self.assertIn("GhostTrack",art["portfolio-projects.svg"])
        self.assertIn("SGA-BTS",art["portfolio-collabs.svg"])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)
            write(path,d)
            self.assertEqual(verify(path),d)
            (path/"portfolio-tech.svg").write_text("tampered",encoding="utf-8")
            with self.assertRaises(ValueError): verify(path)
    def test_private_or_untrusted_external_links_fail(self):
        d=self.sample()
        d["other_repositories"][0]["url"]="https://evil.example/"
        with self.assertRaises(ValueError): validate(d)
    def test_workflow_contains_portfolio_job(self):
        w=(ROOT/".github/workflows/profile-live.yml").read_text(encoding="utf-8")
        self.assertIn("live_portfolio.py --build",w)
        self.assertIn("live/portfolio-tech.svg",w)
        self.assertNotIn("git push origin HEAD:main",w)

if __name__=="__main__":
    unittest.main()
