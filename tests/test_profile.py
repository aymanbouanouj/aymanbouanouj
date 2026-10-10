"""Repeatable offline tests. Fixture data is synthetic and never published."""
import datetime as dt
import json
import sys
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from render_profile import analysis, canonical_days, validate_live_snapshot, hero, heatmap, stats, logo_panel, link_badge, write_assets
from validate import validate_svg_file
import tempfile
from unittest.mock import patch
from fetch_contributions import read_data

class ProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sample=json.loads((ROOT/'tests/fixtures/demo-data.json').read_text())

    def test_valid_consecutive_days(self):
        self.assertTrue(len(canonical_days(self.sample))>=300)

    def test_reject_wrong_username(self):
        bad={**self.sample,'username':'someone-else'}
        with self.assertRaises(ValueError): canonical_days(bad)

    def test_reject_false_total(self):
        bad={**self.sample,'total_contributions':-1}
        with self.assertRaises(ValueError): canonical_days(bad)

    def test_reject_gaps(self):
        bad={**self.sample,'days':self.sample['days'][:5]+self.sample['days'][6:]}
        with self.assertRaises(ValueError): canonical_days(bad)

    def test_reject_malicious_count(self):
        bad={**self.sample,'days':[dict(d) for d in self.sample['days']]}
        bad['days'][0]['count']='<script>alert(1)</script>'
        with self.assertRaises(ValueError): canonical_days(bad)

    def test_generator_produces_all_valid_xml(self):
        for theme in ('dark','light'):
            for svg in (hero(theme),logo_panel(theme),heatmap(theme,self.sample,True),stats(theme,self.sample,True)):
                ET.fromstring(svg)
                self.assertIn('prefers-reduced-motion',svg)
                self.assertNotIn('<script',svg.lower())

    def test_clean_brand_and_links(self):
        readme=(ROOT/'README.md').read_text(encoding='utf-8')
        self.assertNotIn('./assets/ascii-dark.svg',readme)
        for name in ('linkedin','instagram','facebook','x','medium','profiles'):
            self.assertIn(f'./assets/link-{name}.svg',readme)
        for theme in ('dark','light'):
            self.assertIn('AYMAN BOUNAOUJ',logo_panel(theme))

    def test_vector_logo_position_not_overridden_by_css_transform(self):
        # SVG CSS transform animations override the transform attribute and
        # can move the logo outside its frame in GitHub and Edge.
        for theme in ('dark', 'light'):
            svg = logo_panel(theme)
            root_svg = ET.fromstring(svg)
            groups = list(root_svg.iter('{http://www.w3.org/2000/svg}g'))
            placed = [group for group in groups if 'transform' in group.attrib]
            self.assertTrue(placed)
            for group in placed:
                self.assertNotIn('enter', group.get('class', ''))
                self.assertNotIn('animation:', group.get('style', ''))
            self.assertIn('class="logo-fade"', svg)
            self.assertIn('translate(65 150)', svg)
            self.assertIn('logoFade{from{opacity:0}to{opacity:1}}', svg)

    def test_projects_and_footer_are_separate(self):
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        self.assertEqual(readme.count('#### ['), 4)
        self.assertNotIn('> **[Ayman Calc', readme)
        self.assertIn('\n\n---\n\n<div align="center">\n<h3><code>ayman@github ~ $ ./connect.sh', readme)
        self.assertNotIn('<sub>**Evidence-first profile:**', readme)
        self.assertIn('<p><sub>Original SVG artwork · Projects link to public code and demos', readme)

    def test_social_contact_badges(self):
        text=(ROOT/'README.md').read_text(encoding='utf-8')
        for name in ('linkedin','instagram','facebook','x','medium','profiles'):
            self.assertIn('./assets/link-'+name+'.svg',text)
        self.assertNotIn('./assets/link-demos.svg',text)
        self.assertNotIn('./assets/link-projects.svg',text)

    def test_no_numbers_when_missing_live_data(self):
        self.assertIn('AWAITING FIRST GITHUB SYNC',heatmap('dark'))
        self.assertIn('AWAITING FIRST SYNC',stats('light'))

    def test_streak_calculation(self):
        a=analysis(self.sample)
        self.assertGreaterEqual(a['longest'],a['current'])
        self.assertLessEqual(a['active'],len(a['days']))

    def test_historical_streak_is_not_current(self):
        sample = {**self.sample, 'days': [dict(day) for day in self.sample['days']]}
        last_day = dt.date.fromisoformat(sample['days'][-1]['date'])
        sample['days'][-1]['count'] = 4
        sample['total_contributions'] = sum(day['count'] for day in sample['days'])
        self.assertEqual(analysis(sample, reference_date=last_day + dt.timedelta(days=3))['current'], 0)

    def test_yesterday_streak_is_current(self):
        sample = {**self.sample, 'days': [dict(day) for day in self.sample['days']]}
        end = dt.date.fromisoformat(sample['days'][-1]['date'])
        sample['days'][-1]['count'] = 4
        sample['total_contributions'] = sum(day['count'] for day in sample['days'])
        self.assertGreaterEqual(analysis(sample, reference_date=end+dt.timedelta(days=1))['current'], 1)

    def test_zero_today_may_continue_yesterday(self):
        sample = {**self.sample, 'days': [dict(day) for day in self.sample['days']]}
        sample['days'][-1]['count'] = 0
        sample['days'][-2]['count'] = 3
        sample['total_contributions'] = sum(day['count'] for day in sample['days'])
        last = dt.date.fromisoformat(sample['days'][-1]['date'])
        self.assertGreaterEqual(analysis(sample, reference_date=last)['current'], 1)

    def test_yesterday_zero_breaks_streak(self):
        sample = {**self.sample, 'days': [dict(day) for day in self.sample['days']]}
        sample['days'][-1]['count'] = 0
        sample['days'][-2]['count'] = 4
        sample['total_contributions'] = sum(day['count'] for day in sample['days'])
        last = dt.date.fromisoformat(sample['days'][-1]['date'])
        self.assertEqual(analysis(sample, reference_date=last+dt.timedelta(days=1))['current'], 0)

    def test_live_source_staleness_and_utc(self):
        now = dt.datetime(2026, 10, 10, 19, 30, tzinfo=dt.timezone.utc)
        base = {**self.sample, 'source': 'github-graphql-contributionCalendar',
                'fetched_at_utc': now.isoformat()}
        self.assertEqual(len(validate_live_snapshot(base, now)), len(self.sample['days']))
        for change in (
            {'source':'SYNTHETIC DEMO DATA — NEVER PUBLISH'},
            {'fetched_at_utc':(now-dt.timedelta(hours=40)).isoformat()},
            {'fetched_at_utc':(now+dt.timedelta(minutes=6)).isoformat()},
            {'fetched_at_utc':'2026-10-10T19:30:00'},
            {'fetched_at_utc':'not-a-date'},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_live_snapshot({**base, **change}, now)

    def test_live_rejects_historical_calendar_even_with_fresh_fetch(self):
        now = dt.datetime(2026, 10, 15, 19, 30, tzinfo=dt.timezone.utc)
        base = {**self.sample, 'source': 'github-graphql-contributionCalendar',
                'fetched_at_utc': now.isoformat()}
        with self.assertRaisesRegex(ValueError, 'calendar end date'):
            validate_live_snapshot(base, now)

    def test_stale_saved_snapshot_may_still_be_checked_offline(self):
        now = dt.datetime(2027, 2, 1, tzinfo=dt.timezone.utc)
        stale = {**self.sample, 'source': 'github-graphql-contributionCalendar',
                 'fetched_at_utc': '2026-10-10T19:30:00+00:00'}
        self.assertEqual(len(validate_live_snapshot(stale, now, require_fresh=False)), len(self.sample['days']))
        with self.assertRaises(ValueError):
            validate_live_snapshot(stale, now)

    def test_reject_boolean_count_and_total(self):
        bad = {**self.sample, 'days': [dict(d) for d in self.sample['days']]}
        bad['days'][0]['count'] = False
        with self.assertRaises(ValueError): canonical_days(bad)
        bad2 = {**self.sample, 'total_contributions':True}
        with self.assertRaises(ValueError): canonical_days(bad2)

    def test_reject_duplicate_dates(self):
        bad = {**self.sample, 'days': [dict(d) for d in self.sample['days']]}
        bad['days'][1]['date'] = bad['days'][0]['date']
        with self.assertRaises(ValueError): canonical_days(bad)

    def test_readme_contains_verifiable_evidence_not_fake_numbers(self):
        readme = (ROOT/'README.md').read_text(encoding='utf-8')
        self.assertIn('Independent academic project', readme)
        self.assertIn('no real authentication', readme)
        self.assertIn('github.com/aymanbouanouj/PC-Full-Check/tree/main/tests', readme)
        self.assertNotIn('1,620', readme)
        self.assertNotIn('81 contributions', readme)

    def test_workflow_dry_run_read_only(self):
        wf = (ROOT/'.github/workflows/update-stats.yml').read_text(encoding='utf-8')
        self.assertIn('publish:', wf)
        self.assertIn('default: false', wf)
        self.assertIn('contents: read', wf)
        self.assertIn('contents: write', wf)
        self.assertIn('needs: verify', wf)
        self.assertIn('inputs.publish == true', wf)
        self.assertNotIn('cron:', wf)
        self.assertNotIn('pull_request_target:', wf)

    def test_live_rejects_fixture_via_command_line(self):
        import subprocess
        import hashlib
        svg = ROOT / 'assets/stats-dark.svg'
        before = hashlib.sha256(svg.read_bytes()).hexdigest()
        result = subprocess.run([sys.executable, str(ROOT/'scripts/render_profile.py'),
                                 '--data', str(ROOT/'tests/fixtures/demo-data.json')],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, hashlib.sha256(svg.read_bytes()).hexdigest())

    def test_svg_event_handler_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'unsafe.svg'
            path.write_text(hero('dark').replace('<svg ', '<svg onload="alert(1)" ', 1),encoding='utf-8')
            with self.assertRaises(AssertionError): validate_svg_file(path)

    def test_graphql_requires_ephemeral_token(self):
        with self.assertRaises(RuntimeError): read_data('')

    def test_graphql_parser_offline_mock(self):
        from io import BytesIO
        weeks=[{'contributionDays':[{'date':d['date'],'contributionCount':d['count']} for d in self.sample['days']]}]
        packet={'data':{'user':{'contributionsCollection':{'contributionCalendar':{
            'totalContributions':self.sample['total_contributions'],'weeks':weeks}}}}}
        class FakeResponse(BytesIO):
            def __enter__(self): return self
            def __exit__(self,*args): self.close()
        with patch('fetch_contributions.urlopen',return_value=FakeResponse(json.dumps(packet).encode('utf-8'))):
            got=read_data('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')
            self.assertEqual(got['total_contributions'],self.sample['total_contributions'])
            self.assertEqual(got['source'],'github-graphql-contributionCalendar')

    def test_mobile_app_compatible_theme_images(self):
        readme=(ROOT/'README.md').read_text(encoding='utf-8')
        self.assertNotIn('<picture>',readme)
        self.assertNotIn('<source ',readme)
        for component in ('hero','logo','contributions','stats','tech-stack','engineering'):
            if (ROOT/'assets/mobile/manifest.json').exists():
                self.assertIn(f'./assets/mobile/{component}.png',readme)
            else:
                self.assertIn(f'./assets/{component}-dark.svg#gh-dark-mode-only',readme)

    def test_responsive_mark_and_stats_markdown(self):
        readme=(ROOT/'README.md').read_text(encoding='utf-8')
        start=readme.index('identity-and-stats.sh')
        end=readme.index('tech-stack.sh --auto',start)
        section=readme[start:end]
        self.assertNotIn('<table>',section)
        self.assertNotIn('width="50%"',section)
        migrated=(ROOT/'assets/mobile/manifest.json').exists()
        self.assertEqual(section.count('width="445"'),2 if migrated else 4)
        if (ROOT/'assets/mobile/manifest.json').exists():
            self.assertIn('assets/mobile/logo.png',section)
            self.assertIn('assets/mobile/stats.png',section)
        else:
            self.assertIn('assets/logo-light.svg',section)
            self.assertIn('assets/stats-light.svg',section)

    def test_no_external_image_references(self):
        for p in (ROOT/'assets').glob('*.svg'):
            s=p.read_text(encoding='utf-8')
            self.assertNotIn('https://',s)
            self.assertNotIn('http://',s.replace('http://www.w3.org/2000/svg',''))

if __name__=='__main__': unittest.main()
