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

    def test_metrics_refresh_preserves_reviewed_static_artwork(self):
        # Generated statistics may change daily; the reviewed owner logo must not.
        with tempfile.TemporaryDirectory() as temp:
            destination=Path(temp)
            for theme in ('dark','light'):
                for name in ('hero','logo'):
                    (destination/f'{name}-{theme}.svg').write_text('BRAND-REVIEWED',encoding='utf-8')
            write_assets(destination,self.sample,True,include_static=False)
            for theme in ('dark','light'):
                for name in ('hero','logo'):
                    self.assertEqual((destination/f'{name}-{theme}.svg').read_text(encoding='utf-8'),'BRAND-REVIEWED')
                self.assertTrue((destination/f'contributions-{theme}.svg').exists())
                self.assertTrue((destination/f'stats-{theme}.svg').exists())

    def test_combined_refresh_stages_every_generated_svg(self):
        workflow=(ROOT/'.github/workflows/profile-refresh.yml').read_text(encoding='utf-8')
        commit=workflow.split('- name: Create review pull request for verified generated assets',1)[1]
        for name in ('hero','logo','contributions','stats','tech-stack','engineering'):
            for theme in ('dark','light'):
                self.assertIn(f'assets/{name}-{theme}.svg',commit)
        self.assertIn('assets/mobile/',commit)
        self.assertIn('scripts/mobile_png.py --verify',workflow)
        self.assertIn('render_profile.py --data data/contributions.json --no-static',workflow)

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
        self.assertIn('---\n\n<div align="center">', readme)
        self.assertNotIn('<sub>**Evidence-first profile:**', readme)
        self.assertIn('<p><sub>Original SVG artwork · Projects link to public code and demos', readme)

    def test_profile_avoids_duplicate_summaries_and_keeps_verifiable_evidence(self):
        readme=(ROOT/'README.md').read_text(encoding='utf-8')
        self.assertIn('Full-Stack Web Developer',readme)
        self.assertIn('GitHub Linguist',readme)
        self.assertIn('Independent academic project',readme)
        self.assertNotIn('Résumé professionnel des projets en français',readme)
        self.assertNotIn('Projet académique indépendant :',readme)
        self.assertEqual(readme.count('#### ['),4)
        for name in ('hero','contributions','logo','stats','tech-stack','engineering'):
            self.assertIn(f'./assets/mobile/{name}.png',readme)
        self.assertNotIn('<script',readme.lower())

    def test_publish_job_is_restricted_to_main(self):
        workflow=(ROOT/'.github/workflows/profile-refresh.yml').read_text(encoding='utf-8')
        self.assertIn("github.ref == 'refs/heads/main'", workflow)
        self.assertIn('test "${GITHUB_REF}" = "refs/heads/main"', workflow)
        self.assertIn('git push -u origin "${review_branch}"',workflow)
        self.assertIn('gh pr create --base main',workflow)
        self.assertIn('pull-requests: write',workflow)
        self.assertNotIn('git push origin HEAD:main',workflow)
        self.assertIn("vars.ENABLE_SCHEDULED_PROFILE_PUBLISH == 'true'",workflow)

    def test_profile_disclosure_notice_and_refresh_cadence_are_accurate(self):
        readme=(ROOT/'README.md').read_text(encoding='utf-8')
        workflow=(ROOT/'.github/workflows/profile-refresh.yml').read_text(encoding='utf-8')
        self.assertIn('aggregate private contributions',readme)
        self.assertIn('GitHub Actions checks approximately every six hours',readme)
        self.assertIn('scheduled writes require explicit opt-in',readme)
        self.assertNotIn('The scan updates every 6 hours',readme)
        self.assertIn("vars.ENABLE_SCHEDULED_PROFILE_PUBLISH == 'true'",workflow)

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

    def test_full_history_gitleaks_scan_is_not_only_incremental(self):
        ci = (ROOT/'.github/workflows/security-ci.yml').read_text(encoding='utf-8')
        self.assertIn('fetch-depth: 0', ci)
        self.assertIn('git rev-parse --is-shallow-repository', ci)
        self.assertIn('git rev-list --all --count', ci)
        self.assertIn('git --redact --log-opts="--all" .', ci)

    def test_ownership_notice_and_sensitive_file_gate(self):
        readme=(ROOT/'README.md').read_text(encoding='utf-8')
        self.assertIn('All rights reserved',readme)
        self.assertNotIn('Tous droits réservés',readme)
        from check_public_surface import audit
        audit()
        ci=(ROOT/'.github/workflows/security-ci.yml').read_text(encoding='utf-8')
        self.assertIn('python3 scripts/check_public_surface.py',ci)

    def test_generated_pr_requires_manual_ci_dispatch(self):
        workflow=(ROOT/'.github/workflows/profile-refresh.yml').read_text(encoding='utf-8')
        self.assertIn('Manually dispatch security-ci.yml on the review branch',workflow)
        self.assertIn('exact head SHA before merging',workflow)
        self.assertNotIn('approve CI workflow execution if prompted',workflow)

    def test_workflow_dry_run_read_only(self):
        wf = (ROOT/'.github/workflows/profile-refresh.yml').read_text(encoding='utf-8')
        ci = (ROOT/'.github/workflows/security-ci.yml').read_text(encoding='utf-8')
        self.assertIn('publish:', wf)
        self.assertIn('default: false', wf)
        self.assertIn('contents: read', wf)
        self.assertIn('contents: write', wf)
        self.assertIn('needs: verify', wf)
        self.assertIn("vars.ENABLE_SCHEDULED_PROFILE_PUBLISH == 'true'", wf)
        self.assertIn("github.event_name == 'workflow_dispatch' && inputs.publish == true", wf)
        self.assertIn("github.actor == 'aymanbouanouj'", wf)
        self.assertIn('test "${GITHUB_ACTOR}" = "aymanbouanouj"', wf)
        self.assertIn('git push -u origin "${review_branch}"', wf)
        self.assertIn('gh pr create --base main', wf)
        self.assertIn('pull-requests: write', wf)
        self.assertNotIn('git push origin HEAD:main', wf)
        self.assertNotIn('http.https://github.com/.extraheader', wf)
        self.assertNotIn('pull_request_target:', wf)
        self.assertIn('fetch-depth: 0', ci)
        self.assertIn('gitleaks/gitleaks-action@e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e', ci)
        self.assertIn('contents: read', ci)
        self.assertNotIn('contents: write', ci)
        self.assertFalse((ROOT/'.github/workflows/update-stats.yml').exists())
        self.assertFalse((ROOT/'.github/workflows/tech-stack.yml').exists())

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

    def test_v5_brand_is_original_self_hosted_accessible(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        banner = ROOT / "assets/brand-v5.svg"
        self.assertTrue(banner.is_file())
        validate_svg_file(banner)
        artwork = banner.read_text(encoding="utf-8")
        self.assertIn("AYMAN", artwork)
        self.assertIn("BOUNAOUJ", artwork)
        self.assertIn("prefers-reduced-motion", artwork)
        self.assertIn("./assets/brand-v5.svg", readme)
        self.assertLess(readme.index('contributions.sh'), readme.index('whoami'))
        self.assertLess(readme.index('whoami'), readme.index('./links.sh'))
        self.assertLess(readme.index("## Featured Projects"), readme.index("## Current public activity"))
        self.assertLess(readme.index("## Languages & Technical Stack"), readme.index("## Featured Projects"))
        self.assertIn('profile-live/live/contributions.svg', readme)
        self.assertIn('profile-live/live/stats.svg', readme)
        self.assertIn('<table>', readme)

    def test_profile_compact_and_interactive_without_unsafe_scripts(self):
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        self.assertGreaterEqual(readme.count('<details>'), 3)
        self.assertEqual(readme.count('<details>'), readme.count('</details>'))
        self.assertEqual(readme.count('#### ['), 4)
        self.assertEqual(readme.count('src="./assets/mobile/hero.png'), 1)
        self.assertEqual(readme.count('src="./assets/mobile/logo.png'), 1)
        self.assertEqual(readme.count('src="./assets/mobile/contributions.png'), 1)
        self.assertLess(readme.index('## Featured Projects'), readme.index('Original AB artwork and open-source work'))
        self.assertIn('View current GitHub activity', readme)
        self.assertIn('not a live counter', readme)
        self.assertNotIn('featured-project.sh', readme)
        self.assertNotIn('<script', readme.lower())
        self.assertNotIn('onclick=', readme.lower())
        self.assertNotIn('http://', readme)

    def test_reference_layout_is_compact_and_uses_verified_live_images(self):
        r = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn('contributions.sh', r)
        self.assertIn('whoami', r)
        self.assertIn('links.sh', r)
        self.assertIn('profile-live/live/contributions.svg', r)
        self.assertIn('profile-live/live/stats.svg', r)
        self.assertIn('profile-live/live/activity.svg', r)
        self.assertEqual(r.count('<table>'), 1)
        self.assertEqual(r.count('</table>'), 1)
        self.assertLess(r.index('contributions.sh'), r.index('whoami'))
        self.assertLess(r.index('whoami'), r.index('links.sh'))
        self.assertNotIn('8,601', r)
        self.assertNotIn('<script', r.lower())

    def test_restore_v5_live_visual_layout_without_duplicate_static_technologies(self):
        readme=(ROOT/'README.md').read_text(encoding='utf-8')
        for image in ("contributions.svg","stats.svg","portfolio-tech.svg","portfolio-projects.svg","portfolio-collabs.svg","activity.svg"):
            self.assertIn("profile-live/live/"+image,readme)
        for name in ("github","linkedin","instagram","facebook","x","medium","profiles"):
            self.assertIn("./assets/link-"+name+".svg",readme)
        self.assertLess(readme.index('contributions.sh'),readme.index('whoami'))
        self.assertLess(readme.index('## Languages & Technical Stack'),readme.index('## Featured Projects'))
        self.assertIn('profile-live/live/portfolio.md',readme)
        self.assertNotIn('Résumé professionnel des projets en français',readme)
        self.assertNotIn('**Backend & APIs:**',readme)
        self.assertEqual(readme.count('#### ['),4)

    def test_responsive_mark_and_stats_markdown(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        panel = readme.split('<table>', 1)[1].split('</table>', 1)[0]
        self.assertEqual(panel.count('<td '), 2)
        self.assertIn('width="50%"', panel)
        self.assertIn('assets/mobile/logo.png', panel)
        self.assertIn('profile-live/live/stats.svg', panel)
        self.assertIn('profile-live/live/contributions.svg', readme)
        self.assertIn('assets/mobile/stats.png', readme)
        self.assertIn('assets/mobile/engineering.png', readme)

    def test_no_external_image_references(self):
        for p in (ROOT/'assets').glob('*.svg'):
            s=p.read_text(encoding='utf-8')
            self.assertNotIn('https://',s)
            self.assertNotIn('http://',s.replace('http://www.w3.org/2000/svg',''))

if __name__=='__main__': unittest.main()
