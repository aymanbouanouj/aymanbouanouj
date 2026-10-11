"""Public-only portfolio source, integrity, automation and discovery regression tests."""
import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from live_portfolio import collect, draw, validate, verify, write, OWNER, API

class PublicPortfolioTests(unittest.TestCase):
    NOW = dt.datetime(2026, 10, 11, 4, 15, tzinfo=dt.timezone.utc)
    def mock(self, extra=False):
        repos = [
            {"name": "morocco2030", "private": False, "fork": False, "archived": False,
             "owner": {"login": OWNER}, "pushed_at": "2026-10-11T03:00:00Z"},
            {"name": "new-public-tool", "private": False, "fork": False, "archived": False,
             "owner": {"login": OWNER}, "pushed_at": "2026-10-11T04:00:00Z"},
            {"name": "secret-app", "private": True, "fork": False, "archived": False,
             "owner": {"login": OWNER}, "pushed_at": "2026-10-11T04:30:00Z"},
            {"name": OWNER, "private": False, "fork": False, "archived": False,
             "owner": {"login": OWNER}, "pushed_at": "2026-10-11T03:00:00Z"},
        ]
        q = ({"items": [{"repository_url": f"{API}/repos/HichamFaska/SGA-BTS",
                         "number": 1}]})
        if extra:
            q["items"].append({"repository_url": f"{API}/repos/OtherOwner/SomeProject", "number": 3})
        def fetch(url):
            if f"/users/{OWNER}/repos?" in url:
                return repos
            if url.endswith("/languages"):
                if "secret-app" in url or "/"+OWNER+"/languages" in url:
                    raise AssertionError("Private/self repo must not be requested")
                return {"PHP": 500} if "morocco2030" in url else {"JavaScript": 300}
            if "/search/issues?" in url:
                return q
            if url == f"{API}/repos/HichamFaska/SGA-BTS":
                return {"private": False, "owner": {"login": "HichamFaska"}, "name": "SGA-BTS"}
            if url == f"{API}/repos/HichamFaska/SGA-BTS/pulls/1":
                return {"user": {"login": OWNER}, "merged_at": "2026-09-26T21:39:03Z", "number": 1}
            if url == f"{API}/repos/OtherOwner/SomeProject":
                return {"private": False, "owner": {"login": "OtherOwner"}, "name": "SomeProject"}
            if url == f"{API}/repos/OtherOwner/SomeProject/pulls/3":
                return {"user": {"login": OWNER}, "merged_at": "2026-10-10T04:00:00Z", "number": 3}
            raise AssertionError("Unexpected endpoint " + url)
        return fetch
    def test_new_public_project_language_and_external_pr_discovered(self):
        data = collect(self.mock(extra=True), now=self.NOW)
        self.assertEqual(data["public_original_repository_count"], 2)
        self.assertEqual(data["other_repositories"][0]["name"], "new-public-tool")
        self.assertNotIn("secret-app", str(data))
        self.assertNotIn(f'"name": "{OWNER}"', str(data["other_repositories"]))
        self.assertIn("JavaScript", draw(data)["portfolio-tech.svg"])
        self.assertIn("new-public-tool", draw(data)["portfolio-projects.svg"])
        self.assertIn("OtherOwner/SomeProject", draw(data)["portfolio-collabs.svg"])
        self.assertEqual(len(data["verified_collaborations"]), 2)
    def test_verified_outputs_and_tamper_rejection(self):
        data = collect(self.mock(), now=self.NOW)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, data)
            self.assertEqual(verify(root), data)
            (root/"portfolio-tech.svg").write_text("tampered", encoding="utf-8")
            with self.assertRaises(ValueError):
                verify(root)
    def test_empty_sets_render_explicit_explanation(self):
        data = collect(self.mock(), now=self.NOW)
        data["language_bytes"] = []
        data["other_repositories"] = []
        data["verified_collaborations"] = []
        art = draw(data)
        self.assertTrue(all("No verified public entries available" in x for x in art.values()))
    def test_untrusted_private_external_pr_is_not_reported(self):
        def fetch(url):
            if url == f"{API}/repos/HichamFaska/SGA-BTS":
                return {"private": True, "owner": {"login": "HichamFaska"}, "name": "SGA-BTS"}
            return self.mock()(url)
        data = collect(fetch, now=self.NOW)
        self.assertEqual(data["verified_collaborations"], [])
    def test_bad_data_rejected(self):
        data = collect(self.mock(), now=self.NOW)
        data["other_repositories"][0]["url"] = "https://evil.example"
        with self.assertRaises(ValueError):
            validate(data)
    def test_workflow_only_writes_data_branch(self):
        workflow = (ROOT / ".github/workflows/profile-live.yml").read_text(encoding="utf-8")
        self.assertIn("live_portfolio.py --build", workflow)
        self.assertIn("live/portfolio-tech.svg", workflow)
        self.assertNotIn("git push origin HEAD:main", workflow)

if __name__ == "__main__":
    unittest.main()
