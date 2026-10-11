#!/usr/bin/env python3
"""Offline, dependency-free integrity and security checks for the profile."""
from __future__ import annotations
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'assets'
SVG_NS='http://www.w3.org/2000/svg'
REPO_NAMES=('morocco2030','PC-Full-Check','violetgate','ayman-calc')
NAMES=tuple(f'{component}-{theme}.svg' for component in ('hero','logo','contributions','stats','tech-stack','engineering') for theme in ('dark','light'))

def validate_svg_file(path:Path) -> None:
    text=path.read_text(encoding='utf-8')
    root=ET.fromstring(text)
    assert root.tag==f'{{{SVG_NS}}}svg',f'{path.name}: missing SVG root'
    assert root.find(f'{{{SVG_NS}}}title') is not None, f'{path.name}: missing title'
    assert root.find(f'{{{SVG_NS}}}desc') is not None, f'{path.name}: missing description'
    assert 'prefers-reduced-motion' in text,f'{path.name}: missing reduced motion'
    assert '<script' not in text.lower() and '<foreignobject' not in text.lower()
    assert not re.search(r'@import|url\(\s*["\']?https?:|javascript:|data:text/html',text,re.I), f'{path.name}: remote/active content'
    for node in root.iter():
        tag=node.tag.rsplit('}',1)[-1].lower()
        assert tag not in {'script','iframe','foreignobject','image','use','a','animation','animatemotion'},f'{path.name}: disallowed element: {tag}'
        for key,value in node.attrib.items():
            attr=key.rsplit('}',1)[-1].lower()
            assert not attr.startswith('on'),f'{path.name}: event handler'
            assert attr not in ('href','src'),f'{path.name}: forbidden URL reference'
    assert len(text.encode('utf-8'))<500_000, f'{path.name}: oversized SVG'

def main()->int:
    content=(ROOT/'README.md').read_text(encoding='utf-8')
    assert len(content.encode('utf-8'))<500_000
    assert 'javascript:' not in content.lower() and '<script' not in content.lower()
    assert 'github-readme-stats' not in content and 'img.shields.io' not in content
    for name in NAMES + ('link-linkedin.svg','link-instagram.svg','link-facebook.svg','link-x.svg','link-medium.svg','link-profiles.svg'):
        assert (ASSETS/name).exists(), f'Missing generated art {name}'
        assert (f'./assets/{name}' in content or (name.endswith('-light.svg') and (ROOT/'assets/mobile/manifest.json').exists())), f'Not referenced from README: {name}'
        validate_svg_file(ASSETS/name)
    assert '<picture>' not in content and '<source ' not in content, 'GitHub Mobile does not reliably render picture elements'
    mobile=ROOT/'assets'/'mobile'/'manifest.json'
    if mobile.exists():
        from mobile_png import verify as verify_mobile
        verify_mobile()
        from mobile_png import stamp_image_versions
        assert stamp_image_versions(content) == content, 'README PNG cache keys must match verified hashes'
        for component in ('hero','logo','contributions','stats','tech-stack','engineering'):
            assert f'./assets/mobile/{component}.png' in content
            assert f'./assets/{component}-dark.svg' in content
    else:
        for component in ('hero','logo','contributions','stats','tech-stack','engineering'):
            assert f'./assets/{component}-dark.svg#gh-dark-mode-only' in content
            assert f'./assets/{component}-light.svg#gh-light-mode-only' in content
    for repo in REPO_NAMES:
        assert f'https://github.com/aymanbouanouj/{repo}' in content, f'Missing featured repository {repo}'
    for pattern in [r'ghp_[A-Za-z0-9]{30,}',r'github_pat_[A-Za-z0-9_]{30,}',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']:
        assert not re.search(pattern,'\n'.join(p.read_text(encoding='utf-8',errors='ignore') for p in ROOT.rglob('*') if p.is_file() and p.suffix in ('.md','.py','.svg','.yml','.json','.html'))), 'Possible exposed secret'
    snapshot=ROOT/'data'/'contributions.json'
    if snapshot.exists():
        import json
        sys.path.insert(0,str(ROOT/'scripts'))
        from render_profile import validate_live_snapshot
        validate_live_snapshot(json.loads(snapshot.read_text(encoding='utf-8')), require_fresh=False)
        assert 'AWAITING FIRST GITHUB SYNC' not in (ASSETS/'contributions-dark.svg').read_text(encoding='utf-8'), 'Snapshot exists but assets are stale placeholders'
    else:
        assert 'AWAITING FIRST GITHUB SYNC' in (ASSETS/'contributions-dark.svg').read_text(encoding='utf-8'), 'Unverified counts must never be published'
    tech_snapshot=ROOT/'data'/'tech-stack.json'
    sys.path.insert(0,str(ROOT/'scripts'))
    from tech_stack import verify as verify_tech_stack
    if tech_snapshot.exists():
        import json
        verify_tech_stack(json.loads(tech_snapshot.read_text(encoding='utf-8')))
        assert 'AWAITING FIRST VERIFIED LANGUAGE SCAN' not in (ASSETS/'tech-stack-dark.svg').read_text(encoding='utf-8'), 'Tech Stack data exists but artwork is still placeholder'
    else:
        assert 'AWAITING FIRST VERIFIED LANGUAGE SCAN' in (ASSETS/'tech-stack-dark.svg').read_text(encoding='utf-8'), 'Tech Stack without trusted data must remain placeholder'
    engineering_data=ROOT/'data'/'engineering.json'
    from engineering import verify as verify_engineering
    if engineering_data.exists():
        import json
        verify_engineering(json.loads(engineering_data.read_text(encoding='utf-8')))
        assert 'AWAITING FIRST VERIFIED ENGINEERING SCAN' not in (ASSETS/'engineering-dark.svg').read_text(encoding='utf-8')
    else:
        assert 'AWAITING FIRST VERIFIED ENGINEERING SCAN' in (ASSETS/'engineering-dark.svg').read_text(encoding='utf-8')
    workflow_dir=ROOT/'.github/workflows'
    wf=(workflow_dir/'profile-refresh.yml').read_text(encoding='utf-8')
    ci=(workflow_dir/'security-ci.yml').read_text(encoding='utf-8')
    assert 'workflow_dispatch:' in wf and 'contents: write' in wf and 'contents: read' in wf
    assert 'default: false' in wf and 'needs: verify' in wf and 'persist-credentials: false' in wf
    assert "vars.ENABLE_SCHEDULED_PROFILE_PUBLISH == 'true'" in wf
    assert "github.event_name == 'workflow_dispatch' && inputs.publish == true" in wf
    assert "github.actor == 'aymanbouanouj'" in wf
    assert 'test "${GITHUB_ACTOR}" = "aymanbouanouj"' in wf
    assert 'git push -u origin "${review_branch}"' in wf
    assert 'gh pr create --base main' in wf
    assert 'pull-requests: write' in wf
    assert 'git push origin HEAD:main' not in wf
    assert 'pull_request_target' not in wf and 'schedule:' in wf
    assert not (workflow_dir/'update-stats.yml').exists() and not (workflow_dir/'tech-stack.yml').exists()
    assert 'fetch-depth: 0' in ci and 'gitleaks/gitleaks-action@' in ci
    assert 'pull_request_target' not in ci and 'contents: write' not in ci
    print('PASS: all eighteen SVGs parse, contain accessibility metadata and reduced-motion support.')
    print('PASS: SVGs contain no third-party requests, links, scripts or event handlers.')
    print('PASS: README links verified by path and limited embedded content.')
    print('PASS: real-vs-placeholder data state is honest and consistent.')
    print('PASS: manual dry-run is read-only; publishing requires explicit consent and scoped permission.')
    return 0

if __name__=='__main__':
    try:
        raise SystemExit(main())
    except (OSError,AssertionError,ValueError,ET.ParseError) as err:
        print(f'FAIL: {err}',file=sys.stderr)
        raise SystemExit(1)
