"""Regression checks for public dashboard data, SVG output and README assembly."""
from __future__ import annotations

import base64
import copy
import hashlib
import datetime as dt
import io
import re
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

from fontTools.ttLib import TTFont, sfnt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import dashboard_data as data
import dashboard_technology as technology
import render_svg_cards as render

FIXTURE = ROOT / "data"
NS = {"svg": render.SVG_NS}


def calendar_fixture(today, counts=None, *, yesterday=False):
    end = today - dt.timedelta(days=int(yesterday))
    counts = counts or {}
    days = []
    for days_ago in reversed(range(366)):
        day = end - dt.timedelta(days=days_ago)
        days.append({"date": day.isoformat(), "count": counts.get(day, 0)})
    stamp = dt.datetime.combine(today, dt.time(12), tzinfo=dt.timezone.utc)
    return {"username": data.OWNER, "source": "github-graphql-contributionCalendar",
            "fetched_at_utc": stamp.isoformat(), "days": days,
            "total_contributions": sum(day["count"] for day in days)}, stamp


class SnapshotTests(unittest.TestCase):
    def test_empty_leap_date_and_snapshot_ending_yesterday(self):
        today = dt.date(2024, 3, 1)
        snapshot, now = calendar_fixture(today, yesterday=True)
        stats = data.activity(snapshot, now=now, fresh=True)
        self.assertEqual(stats["range"][1], dt.date(2024, 2, 29))
        self.assertEqual((stats["active"], stats["current"], stats["total"]), (0, 0, 0))
        self.assertIsNone(stats["peak"])
        self.assertEqual(sum(n for _, n in stats["months"]), 0)

        snapshot, now = calendar_fixture(today, {today - dt.timedelta(1): 4, today - dt.timedelta(2): 2})
        stats = data.activity(snapshot, now=now, fresh=True)
        self.assertEqual((stats["active"], stats["current"], stats["total"], stats["longest"]), (2, 2, 6, 2))
        self.assertEqual(stats["peak"]["date"], dt.date(2024, 2, 29))
        yesterday, _ = calendar_fixture(today, {today - dt.timedelta(1): 4}, yesterday=True)
        self.assertEqual(data.activity(yesterday, now=now)["current"], 1)

    def test_invalid_ranges_duplicates_counts_and_foreign_fields_fail_closed(self):
        snapshot, now = calendar_fixture(dt.date(2024, 1, 2))
        for mutation in (
            lambda s: s["days"].pop(17),
            lambda s: s["days"].insert(3, s["days"][3]),
            lambda s: s["days"][-1].update(date="2024-01-03"),
            lambda s: s["days"][4].update(count=True),
            lambda s: s["days"][4].update(count=-1),
            lambda s: s["days"][4].update(count=13),
            lambda s: s["days"][4].update(extra="unexpected field"),
        ):
            broken = copy.deepcopy(snapshot)
            mutation(broken)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                data.activity(broken, now=now)
        # A legitimate historical snapshot stays reproducible, but cannot publish as fresh.
        with self.assertRaisesRegex(ValueError, "stale"):
            data.activity(snapshot, now=now + dt.timedelta(days=2), fresh=True)
        self.assertEqual(data.activity(snapshot, now=now + dt.timedelta(days=2))["active"], 0)
        with self.assertRaisesRegex(ValueError, "timestamp"):
            data.activity(snapshot, now=now - dt.timedelta(days=1))

    def test_public_schema_rejects_private_metadata(self):
        snapshot = data.read_json(FIXTURE / "dashboard-public.json")
        data.validate(snapshot)
        key = data.REPOS[0]
        for field, value in (("visibility", "private"), ("stars", True), ("forks", -1), ("extra", 12)):
            broken = copy.deepcopy(snapshot)
            broken["repositories"][key][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                data.validate(broken)

    def test_merge_status_requires_github_confirmation(self):
        record = data.CONTRIBUTIONS[0]
        repo, _, number = record
        repo_data = {"full_name": repo, "private": False, "visibility": "public"}
        pr = {"number": number, "user": {"login": data.OWNER}, "state": "open", "merged": False,
              "base": {"repo": {"private": False}}, "merged_at": None}

        def fetch(url):
            return pr if "/pulls/" in url else repo_data

        self.assertEqual(data.contribution_status(fetch, record), "Open")
        pr["draft"] = True
        self.assertEqual(data.contribution_status(fetch, record), "Draft")
        pr.update(state="closed", draft=False)
        self.assertEqual(data.contribution_status(fetch, record), "Closed")
        pr.update(merged=True, merged_at="2026-11-01T18:20:30Z")
        self.assertEqual(data.contribution_status(fetch, record), "Merged")
        pr["merged_at"] = None
        with self.assertRaises(ValueError):
            data.contribution_status(fetch, record)
        pr["base"]["repo"]["private"] = True
        with self.assertRaises(ValueError):
            data.contribution_status(fetch, record)

    def test_failed_api_request_preserves_existing_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "public.json"
            path.write_text("previous verified snapshot", encoding="utf-8")
            with patch("sys.argv", ["dashboard_data", "--output", str(path)]), \
                    patch.object(data, "request_json", side_effect=URLError("unavailable")), \
                    patch("sys.stderr", new_callable=io.StringIO) as err, self.assertRaises(SystemExit) as caught:
                data.main()
            self.assertEqual(caught.exception.code, 1)
            self.assertIn("failed validation or retrieval", err.getvalue())
            self.assertEqual(path.read_text(encoding="utf-8"), "previous verified snapshot")


class SVGTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calendar = data.read_json(FIXTURE / "dashboard-contributions.json")
        cls.public = data.read_json(FIXTURE / "dashboard-public.json")
        cls.stats = data.activity(cls.calendar)
        cls.technology = technology.validate(data.read_json(technology.SEED))
        cls.cards = render.artworks(cls.stats, cls.public, cls.technology)

    def test_every_svg_is_safe_reproducible_and_static_geometry_matches(self):
        for name, card in self.cards.items():
            with self.subTest(card=name):
                animated, static = card.svg(False), card.svg(True)
                render.verify_svg(animated, name, False)
                render.verify_svg(static, name, True)
                checked_in = (ROOT / "cards" / (name + ".svg")).read_text(encoding="utf-8")
                render.verify_svg(checked_in, name, False)
                self.assertTrue(render.same_svg(checked_in, animated), f"{name}: checked-in artwork differs")
                self.assertIn("animation:none!important;opacity:1!important;transform:none!important", animated)
                self.assertEqual(re.sub(r"<style>.*?</style>", "", animated, flags=re.S),
                                 re.sub(r"<style>.*?</style>", "", static, flags=re.S))
                self.assertNotIn("@keyframes", static)

    def test_each_font_contains_the_visible_glyphs(self):
        for name, card in self.cards.items():
            xml = ET.fromstring(card.svg(True))
            style = xml.findtext("svg:style", namespaces=NS)
            fonts = dict(re.findall(r"font-weight:(\d+);src:url\(data:font/woff;base64,([A-Za-z0-9+/=]+)\)", style))
            glyphs_by_weight = {}
            for element in xml.findall(".//svg:text", NS):
                if element.text:
                    glyphs_by_weight.setdefault(element.get("font-weight"), set()).update(map(ord, element.text))
            self.assertEqual(fonts.keys(), glyphs_by_weight.keys(), name)
            for weight, encoded in fonts.items():
                with self.subTest(card=name, weight=weight), TTFont(io.BytesIO(base64.b64decode(encoded))) as font:
                    self.assertEqual(font.flavor, "woff")
                    self.assertEqual(font["OS/2"].usWeightClass, int(weight))
                    self.assertEqual(set(font.getBestCmap()), glyphs_by_weight[weight])

    def test_technology_grid_keeps_each_badge_and_its_row(self):
        stack = ("PHP", "JavaScript", "TypeScript", "Python", "HTML", "CSS", "MySQL", "Laravel",
                 "React", "Docker", "Playwright", "Tailwind CSS")
        tools = ("Laravel", "Vite", "Node.js", "Composer", "pnpm", "Docker", "GitHub Actions")
        for name, labels, columns in (
            ("technical", stack, 6), ("technical-mobile", stack, 3),
            ("tools", tools, 7), ("tools-mobile", tools, 2),
        ):
            with self.subTest(card=name):
                root = ET.fromstring(self.cards[name].svg(True))
                tiles = root.findall("svg:g[@class='rise']", NS)
                self.assertEqual(tuple(tile.findtext("svg:text", namespaces=NS) for tile in tiles), labels)
                rows = {}
                for tile in tiles:
                    y = tile.find("svg:rect", NS).get("y")
                    rows[y] = rows.get(y, 0) + 1
                self.assertEqual(list(rows.values()), [
                    min(columns, len(labels) - start) for start in range(0, len(labels), columns)
                ])

    def test_technology_cards_render_sparse_and_empty_evidence(self):
        sample = {"schema": 1, "source": technology.SOURCE, "evidence": {
            name: self.technology["evidence"][name] for name in ("PowerShell", "Playwright", "Node.js")
        }}
        technology.validate(sample)
        markup = render.profile_markup(technology_evidence=sample)
        self.assertIn('alt="Languages &amp; Technical Stack. Playwright, PowerShell"', markup)
        self.assertIn('alt="Frameworks / Build Tools. Node.js, Playwright"', markup)
        for tools, expected in ((False, ["Playwright", "PowerShell"]), (True, ["Node.js", "Playwright"])):
            for compact in (False, True):
                card = render.tech_grid(sample, tools=tools, compact=compact)
                root = ET.fromstring(card.svg(True))
                self.assertEqual([tile.findtext("svg:text", namespaces=NS)
                                  for tile in root.findall("svg:g[@class='rise']", NS)], expected)
                empty = render.tech_grid({"evidence": {}}, tools=tools, compact=compact).svg(True)
                self.assertIn("No verified public evidence available.", empty)

    def test_verification_ignores_only_woff_compression_differences(self):
        svg = self.cards["hero"].svg(True)
        original = render.FONT_DATA.search(svg)[1]
        buffer = io.BytesIO()
        with TTFont(io.BytesIO(base64.b64decode(original)), recalcTimestamp=False) as font:
            with patch.object(sfnt, "ZLIB_COMPRESSION_LEVEL", 0):
                font.save(buffer)
        alternate = base64.b64encode(buffer.getvalue()).decode("ascii")
        self.assertNotEqual(original, alternate)
        repacked = svg.replace(original, alternate, 1)
        self.assertTrue(render.same_svg(svg, repacked))
        self.assertFalse(render.same_svg(svg, repacked.replace(">Ayman Bounaouj</text>", ">Other title</text>")))

    def test_calendar_cells_match_every_day_count_and_heat_bin(self):
        first = dt.date.fromisoformat(self.calendar["days"][0]["date"])
        sunday = first - dt.timedelta(days=(first.weekday() + 1) % 7)
        for name in ("calendar", "calendar-mobile"):
            with self.subTest(card=name):
                root = ET.fromstring(self.cards[name].svg(True))
                cells = {cell.get("data-date"): cell for cell in root.findall(".//svg:rect", NS)
                         if cell.get("data-date")}
                self.assertEqual(set(cells), {day["date"] for day in self.calendar["days"]})
                top = min(int(cell.get("y")) for cell in cells.values())
                for day in self.calendar["days"]:
                    cell = cells[day["date"]]
                    self.assertEqual(int(cell.get("data-count")), day["count"])
                    row = (dt.date.fromisoformat(day["date"]) - sunday).days % 7
                    self.assertEqual(int(cell.get("y")), top + 13 * row)
                    self.assertEqual(cell.get("fill"), render.HEAT[render.heat_level(day["count"])])
                self.assertEqual(sum(int(cell.get("data-count")) for cell in cells.values()),
                                 self.calendar["total_contributions"])
                labels = {node.text for node in root.findall(".//svg:text", NS)}
                self.assertTrue({"Dec", "Less", "More"} <= labels)
                self.assertNotIn("Monthly totals", labels)
                self.assertFalse(root.findall(".//svg:g[@class='grow']", NS))

    def test_unapproved_svg_content_is_rejected(self):
        valid = self.cards["hero"].svg(False)
        for extra in ('<script/>', '<foreignObject/>', '<g onclick="broken"/>',
                      '<image href="https://example.com/outside.jpg"/>',
                      '<style>.x{fill:url(//example.com/pixel)}</style>'):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                render.verify_svg(valid.replace("</svg>", extra + "</svg>"), "hero", False)

    def test_two_cta_buttons_and_portfolio_link_placeholder(self):
        self.assertEqual({name for name in self.cards if name.startswith("link-")},
                         {"link-profile", "link-portfolio"})
        for name in ("profile", "portfolio"):
            xml = self.cards["link-" + name].svg(True)
            root = ET.fromstring(xml)
            self.assertEqual(root.get("width"), "182")
            self.assertEqual(root.get("height"), "50")
            pending = name == "portfolio" and not render.PORTFOLIO_SITE_URL
            self.assertIn("#302044" if pending else "url(#action)" if name == "portfolio" else "url(#panel)", xml)
            labels = [node.text for node in root.findall(".//svg:text", NS)]
            self.assertEqual(len(labels), 2 if pending else 1)
            if pending:
                self.assertIn("Coming soon", labels)
        self.assertIn("href=\"https://beacons.ai/aymanbounaouj\"", render.profile_markup())
        self.assertNotIn("<a href=\"\"><img src=\"./cards/link-portfolio.svg\"", render.profile_markup())
        if not render.PORTFOLIO_SITE_URL:
            self.assertIn("website not launched yet", render.profile_markup())
        with patch.object(render, "PORTFOLIO_SITE_URL", "https://portfolio.example.org/"):
            self.assertIn('<a href="https://portfolio.example.org/"><img src="./cards/link-portfolio.svg"',
                          render.profile_markup())
        with patch.object(render, "PORTFOLIO_SITE_URL", "http://invalid.example/"):
            with self.assertRaises(ValueError):
                render.profile_markup()

    def test_featured_and_additional_repositories_are_distinct(self):
        featured = set(tuple(render.PROJECTS)[:3])
        additional = {name for name, _ in render.PINS}
        self.assertFalse(featured & additional)
        self.assertEqual(additional, {"violetgate", "ayman-calc"})
        for name in featured:
            card = self.cards["project-" + name.lower()]
            self.assertFalse(render.dynamic("project-" + name.lower()))
            self.assertIn(render.PROJECT_EVIDENCE[name], card.svg(True))
        self.assertEqual(render.HEADERS["building"][0], "Recently Updated Projects")

    def test_only_two_svg_ctas_are_generated(self):
        names = {name for name in self.cards if name.startswith("link-")}
        self.assertEqual(names, {"link-profile", "link-portfolio"})
        markup = render.profile_markup()
        self.assertIn('<img src="./cards/link-portfolio.svg"', markup)
        self.assertNotIn('href=""', markup)

    def test_approved_hero_background_is_embedded_in_both_sizes(self):
        for name in ("hero", "hero-mobile"):
            root = ET.fromstring(self.cards[name].svg(True))
            picture = root.find(".//svg:image", NS)
            self.assertIsNotNone(picture)
            uri = picture.get("href")
            self.assertTrue(uri.startswith(render.TRAIN_URI))
            self.assertEqual(hashlib.sha256(base64.b64decode(uri[len(render.TRAIN_URI):])).hexdigest(),
                             render.HERO_BG_SHA256)

    def test_hero_uses_system_illustration_in_the_original_bounds(self):
        for name, dimensions in (("hero", ("1160", "235")), ("hero-mobile", ("680", "234"))):
            svg = self.cards[name].svg(True)
            root = ET.fromstring(svg)
            self.assertEqual((root.get("width"), root.get("height")), dimensions)
            self.assertIsNotNone(root.find(".//svg:g[@id='system-illustration']", NS))
            self.assertNotRegex(svg, r"(?i)laptop|#bezel|#display|#screenlight")

    def test_hero_copy_matches_the_readme_in_both_sizes(self):
        lines = ["Ayman Bounaouj", "Software Developer", "Full-Stack Web Development",
                 "Building Practical & Secure Digital Products"]
        for name in ("hero", "hero-mobile"):
            root = ET.fromstring(self.cards[name].svg(True))
            texts = root.findall(".//svg:text", NS)
            self.assertEqual([node.text for node in texts], lines)
            self.assertEqual(texts[1].get("fill"), render.VIOLET)
            self.assertEqual(root.findtext("svg:title", namespaces=NS), "Ayman Bounaouj | Software Developer")
            for line in lines[2:]:
                self.assertIn(line, root.findtext("svg:desc", namespaces=NS))
        markup = render.profile_markup()
        description = "Software Developer. Full-Stack Web Development. Building Practical &amp; Secure Digital Products."
        self.assertIn(f'alt="Ayman Bounaouj. {description}"', markup)
        self.assertIn(f"<strong>Ayman Bounaouj</strong> · {description}", markup)
        self.assertIn("<summary><h3>Profile text and data sources</h3></summary>", markup)

    def test_readme_review_and_live_markup_are_reproducible(self):
        for live, marker in ((False, render.README_MARKER), (True, render.LIVE_README_MARKER)):
            with self.subTest(live=live), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "README.md"
                actual = render.profile_markup(live_technology=live)
                self.assertEqual(actual, render.profile_markup(live_technology=live))
                path.write_text(marker + actual, encoding="utf-8")
                render.verify_readme(path)
                for name in ("calendar", "technical", "tools"):
                    base = render.LIVE if live else "./cards/"
                    self.assertIn(f'src="{base}{name}.svg"', actual)
                    self.assertIn(f'srcset="{base}{name}-mobile.svg"', actual)
                self.assertIn("/profile-live/cards/technology.json" if live else "./data/dashboard-technology.json", actual)
                if live:
                    for name in ("calendar", "technical", "tools"):
                        self.assertNotIn(f'./cards/{name}.svg', actual)
                        self.assertNotIn(f'./cards/{name}-mobile.svg', actual)
                path.write_text(marker + actual.replace("tools.svg", "invalid.svg"), encoding="utf-8")
                with self.assertRaises(ValueError):
                    render.verify_readme(path)

    def test_readme_orders_sections_and_wraps_each_linkable_card(self):
        render.verify_readme()
        markup = render.profile_markup()
        order = ("hero.svg", "metrics.svg", "calendar.svg", "technical.svg", "tools.svg",
                 "heading-featured.svg", "heading-opensource.svg", "heading-building.svg", "heading-pinned.svg")
        self.assertEqual(sorted(order, key=markup.index), list(order))
        self.assertNotIn("footer", markup)
        self.assertNotIn("monthly totals", markup)

        class Paths(HTMLParser):
            def __init__(self):
                super().__init__()
                self.refs = []
                self.link = None

            def handle_starttag(self, tag, attrs):
                pairs = dict(attrs)
                if tag == "a":
                    self.link = pairs["href"]
                if tag in {"img", "source"}:
                    self.refs.append((tag, pairs, self.link))

            def handle_endtag(self, tag):
                if tag == "a":
                    self.link = None

        paths = Paths()
        paths.feed(markup)
        buttons = []
        for tag, attrs, destination in paths.refs:
            src = attrs["src"] if tag == "img" else attrs["srcset"]
            name = Path(urlsplit(src).path).stem
            if src.startswith("./assets/link-"):
                self.assertEqual(tag, "img")
                self.assertTrue(attrs["alt"])
                self.assertEqual(urlsplit(destination).scheme, "https")
                buttons.append(name)
                continue
            self.assertIn(name, self.cards)
            live = render.dynamic(name) and name.split("-")[0] not in {"calendar", "technical", "tools"}
            self.assertTrue(src.startswith(render.LIVE if live else "./cards/"))
            if tag == "img":
                self.assertTrue(attrs["alt"])
            if name.startswith("link-"):
                buttons.append(name)
            if name.startswith(("project-", "pin-", "building-", "contribution-")):
                self.assertEqual(urlsplit(destination).scheme, "https")
            elif name == "link-profile":
                self.assertEqual(urlsplit(destination).scheme, "https")
            elif name == "link-portfolio":
                if render.PORTFOLIO_SITE_URL:
                    self.assertEqual(destination, render.PORTFOLIO_SITE_URL)
                else:
                    self.assertIsNone(destination)
        self.assertEqual(buttons, ["link-profile", "link-portfolio"])
        self.assertNotIn("<script", markup.casefold())


if __name__ == "__main__":
    unittest.main()
