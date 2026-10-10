"""Offline tests for automatic public Tech Stack generation."""
import datetime as dt
import sys
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from tech_stack import aggregate, collect, verify, render, OWNER
NOW=dt.datetime(2026,10,10,21,0,tzinfo=dt.timezone.utc)

class TechStackTests(unittest.TestCase):
    def repo(self,name,**options):
        return {"name":name,"owner":{"login":OWNER},"fork":False,
                "archived":False,"disabled":False,"private":False,**options}

    def test_language_detected_automatically_across_projects(self):
        projects=[self.repo("php-project"),self.repo("new-project")]
        data={"php-project":{"PHP":300,"JavaScript":100},
              "new-project":{"Rust":123,"PHP":40}}
        result=aggregate(projects,lambda n:data[n])
        self.assertEqual({x["name"] for x in result["languages"]},{"PHP","JavaScript","Rust"})
        self.assertEqual(result["repository_count"],2)
        self.assertEqual(next(x for x in result["languages"] if x["name"]=="PHP")["repositories"],
                         ["new-project","php-project"])

    def test_ignore_forks_private_archived_disabled_profile(self):
        projects=[self.repo("good"),self.repo("forked",fork=True),
                  self.repo("old",archived=True),self.repo("disabled",disabled=True),
                  self.repo("secret",private=True),self.repo(OWNER)]
        seen=[]
        result=aggregate(projects,lambda n:seen.append(n) or {"PowerShell":78})
        self.assertEqual(seen,["good"])
        self.assertEqual(result["repository_count"],1)

    def test_invalid_scan_never_fabricates_zero(self):
        with self.assertRaises(ValueError): aggregate([self.repo("a")],lambda _: {})
        with self.assertRaises(ValueError): aggregate([self.repo("a")],lambda _: None)
        with self.assertRaises(ValueError): aggregate([self.repo("a")],lambda _: {"PHP":True})

    def test_api_pagination_and_evidence(self):
        calls=[]
        def fake(url,token):
            calls.append(url)
            if "/users/" in url: return [self.repo("new-public-repo")]
            return {"Python":55}
        item=collect(getter=fake,now=NOW)
        self.assertEqual(len(calls),2)
        self.assertEqual(item["languages"][0]["repositories"],["new-public-repo"])
        verify(item,now=NOW,max_age_hours=2)

    def test_trust_and_staleness(self):
        item=collect(getter=lambda url,token:
                     [self.repo("first")] if "/users/" in url else {"C++":50},now=NOW)
        for bad in ({"username":"unknown"},{"source":"fixture"},
                    {"scanned_at_utc":"2024-01-01T00:00:00+00:00"}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                verify({**item,**bad},now=NOW,max_age_hours=2)

    def test_svg_integrity_and_motion(self):
        item=collect(getter=lambda url,token:
                     [self.repo("first")] if "/users/" in url else {"TypeScript":44},now=NOW)
        for theme in ("dark","light"):
            for data in (item,None):
                svg=render(theme,data)
                ET.fromstring(svg)
                self.assertIn("prefers-reduced-motion",svg)
                self.assertNotIn("<script",svg.lower())

    def test_profile_references_both_theme_artworks(self):
        content=(ROOT/"README.md").read_text(encoding="utf-8")
        if (ROOT/"assets/mobile/manifest.json").exists():
            self.assertIn('./assets/mobile/tech-stack.png',content)
            self.assertIn('./assets/tech-stack-dark.svg',content)
        else:
            self.assertIn("./assets/tech-stack-dark.svg",content)
            self.assertIn("./assets/tech-stack-light.svg",content)
        self.assertIn("GitHub Linguist",content)

if __name__=="__main__": unittest.main()
