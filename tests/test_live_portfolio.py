"""Public-only portfolio source, integrity, automation and discovery regression tests."""
import datetime as dt
import base64
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from live_portfolio import collect, draw, validate, verify, write, render_markdown, repair_markdown, OWNER, API

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
            if "/contents/" in url:
                if "morocco2030" in url and url.endswith("composer.json"):
                    raw=b'{"require":{"laravel/framework":"^12.0"}}'
                elif "new-public-tool" in url and url.endswith("package.json"):
                    raw=b'{"devDependencies":{"vite":"^8.0"}}'
                else:
                    from urllib.error import HTTPError
                    raise HTTPError(url,404,"missing",{},None)
                return {"type":"file","encoding":"base64","size":len(raw),"content":base64.b64encode(raw).decode()}
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
        self.assertIn("Laravel", draw(data)["portfolio-tech.svg"])
        self.assertIn("Vite", draw(data)["portfolio-tech.svg"])
        self.assertIn('scale(', draw(data)["portfolio-tech.svg"])
        self.assertEqual([r["name"] for r in data["verified_frameworks"]],["Laravel","Vite"])
        self.assertIn("new-public-tool", draw(data)["portfolio-projects.svg"])
        self.assertIn("OtherOwner/SomeProject", draw(data)["portfolio-collabs.svg"])
        self.assertEqual(len(data["verified_collaborations"]), 2)
        self.assertIn("OtherOwner/SomeProject",render_markdown(data))
        self.assertNotIn("secret-app",render_markdown(data))
    def test_all_detected_languages_render_without_six_item_cutoff(self):
        data = collect(self.mock(), now=self.NOW)
        data["language_bytes"] = [[f"Lang{i}", 100 + i] for i in range(12)]
        art = draw(data)["portfolio-tech.svg"]
        from xml.etree import ElementTree
        root = ElementTree.fromstring(art)
        self.assertGreater(int(root.attrib["height"]), 590)
        for i in range(12):
            self.assertIn(f"Lang{i}", art)
        self.assertIn("FRAMEWORKS / BUILD TOOLS", art)
        self.assertIn("Laravel", art)

    def test_private_languages_are_aggregated_without_private_metadata_leak(self):
        from live_portfolio import render_markdown
        private_name = "sensitive-hidden-project"
        calls = []
        def private_fetch(url):
            calls.append(url)
            if "/user/repos?" in url:
                return [{"name": private_name, "private": True, "fork": False,
                         "archived": False, "disabled": False,
                         "owner": {"login": OWNER}}]
            if url == f"{API}/repos/{OWNER}/{private_name}/languages":
                return {"Python": 700, "PHP": 200}
            raise AssertionError("Private fetch must read only metadata/language endpoints")
        data = collect(self.mock(), now=self.NOW, private_fetch=private_fetch)
        languages = dict(data["language_bytes"])
        self.assertEqual(data["language_scope"], "public-plus-private")
        self.assertEqual(languages["Python"], 700)
        self.assertEqual(languages["PHP"], 700)
        self.assertEqual(languages["JavaScript"], 300)
        self.assertTrue(any("/languages" in url for url in calls))
        from json import dumps
        exposed = dumps(data) + render_markdown(data) + "".join(draw(data).values())
        self.assertNotIn(private_name, exposed)
        self.assertNotIn("/contents/", " ".join(calls))
        self.assertIn("private", render_markdown(data))
        self.assertEqual([r["name"] for r in data["verified_frameworks"]], ["Laravel", "Vite"])

    def test_private_api_failure_never_silently_publishes_false_zero(self):
        from urllib.error import HTTPError
        def denied(url):
            raise HTTPError(url, 403, "Forbidden", {}, None)
        data = collect(self.mock(), now=self.NOW, private_fetch=denied)
        self.assertEqual(data["language_scope"], "public-only-private-unavailable")
        self.assertEqual(dict(data["language_bytes"]), {"PHP": 500, "JavaScript": 300})
        output = render_markdown(data) + "".join(draw(data).values())
        self.assertIn("unavailable", output)
        self.assertNotIn("Forbidden", output)
        self.assertNotIn("secret-app", output)

    def test_partial_private_scan_does_not_publish_partial_totals(self):
        from urllib.error import HTTPError
        hidden = "confidential-repo-name"
        def private_fetch(url):
            if "/user/repos?" in url:
                return [{"name": hidden, "private": True, "fork": False,
                         "archived": False, "disabled": False,
                         "owner": {"login": OWNER}}]
            raise HTTPError(url, 403, "blocked", {}, None)
        data = collect(self.mock(), now=self.NOW, private_fetch=private_fetch)
        self.assertEqual(data["language_scope"], "public-only-private-unavailable")
        published = __import__("json").dumps(data) + render_markdown(data) + "".join(draw(data).values())
        self.assertNotIn(hidden, published)
        self.assertNotIn("blocked", published)

    def test_verified_outputs_and_tamper_rejection(self):
        data = collect(self.mock(), now=self.NOW)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, data)
            self.assertEqual(verify(root), data)
            (root/"portfolio.md").write_text("tampered",encoding="utf-8")
            with self.assertRaises(ValueError): verify(root)
            (root/"portfolio.md").write_text(render_markdown(data),encoding="utf-8")
            (root/"portfolio-tech.svg").write_text("tampered", encoding="utf-8")
            with self.assertRaises(ValueError):
                verify(root)
    def test_repair_stale_markdown_after_retaining_old_snapshot(self):
        data = collect(self.mock(), now=self.NOW)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, data)
            original_json = (root/"portfolio.json").read_bytes()
            original_svg = (root/"portfolio-tech.svg").read_bytes()
            expected = (root/"portfolio.md").read_text(encoding="utf-8")
            (root/"portfolio.md").write_text(expected.replace(
                "2026-10-11T04:15", "2026-10-11T05:38"), encoding="utf-8")
            with self.assertRaises(ValueError): verify(root)
            self.assertTrue(repair_markdown(root))
            self.assertEqual(verify(root), data)
            self.assertEqual((root/"portfolio.json").read_bytes(), original_json)
            self.assertEqual((root/"portfolio-tech.svg").read_bytes(), original_svg)
            self.assertEqual((root/"portfolio.md").read_text(encoding="utf-8"), expected)
            self.assertFalse(repair_markdown(root))

    def test_repair_rejects_invalid_input_and_does_not_hide_bad_svg(self):
        data = collect(self.mock(), now=self.NOW)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            write(root, data)
            (root/"portfolio-tech.svg").write_text("tampered", encoding="utf-8")
            repair_markdown(root)
            with self.assertRaises(ValueError): verify(root)
            (root/"portfolio.json").write_text('{"schema":0}', encoding="utf-8")
            with self.assertRaises((ValueError, KeyError)): repair_markdown(root)

    def test_workflow_rechecks_after_restoration_before_publishing(self):
        workflow=(ROOT/".github/workflows/profile-live.yml").read_text(encoding="utf-8")
        restore=workflow.index("Portfolio data unchanged: preserving approved illustrations")
        repair=workflow.index('live_portfolio.py" --repair-markdown --output live')
        stage=workflow.index("git add -- live/activity.svg")
        self.assertLess(restore,repair)
        self.assertLess(repair,stage)
        for script in ("live_profile.py","live_contributions.py","live_portfolio.py"):
            self.assertIn(f'{script}" --verify --output live',workflow[repair:stage])

    def test_empty_sets_render_explicit_explanation(self):
        data = collect(self.mock(), now=self.NOW)
        data["language_bytes"] = []
        data["verified_frameworks"] = []
        data["other_repositories"] = []
        data["verified_collaborations"] = []
        art = draw(data)
        self.assertIn("No verified public language data",art["portfolio-tech.svg"])
        self.assertIn("No recognized public framework manifest found",art["portfolio-tech.svg"])
        self.assertTrue(all("No verified public entries available" in art[name]
             for name in ("portfolio-projects.svg","portfolio-collabs.svg")))
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
