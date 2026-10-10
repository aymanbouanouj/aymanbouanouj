#!/usr/bin/env python3
"""Fetch the public GitHub contribution calendar via authenticated GraphQL.

Uses the ephemeral GITHUB_TOKEN supplied by GitHub Actions. No personal access
 token, third-party counter service, scraping or project data is necessary.
"""
from __future__ import annotations
import datetime as dt
import json
import os
import sys
from pathlib import Path
import tempfile
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT=Path(__file__).resolve().parents[1]
USER='aymanbouanouj'
QUERY='''query($login:String!) {
  user(login:$login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}'''

def read_data(token:str) -> dict:
    if not token or len(token.strip())<10:
        raise RuntimeError('Missing GITHUB_TOKEN. Run this inside the GitHub Actions workflow.')
    payload=json.dumps({'query':QUERY,'variables':{'login':USER}}).encode('utf-8')
    req=Request('https://api.github.com/graphql',data=payload,headers={
        'Authorization':f'Bearer {token}',
        'Content-Type':'application/json',
        'Accept':'application/vnd.github+json',
        'User-Agent':'ayman-github-profile-readme/2.0',
    },method='POST')
    with urlopen(req,timeout=25) as res:
        response=json.load(res)
    if response.get('errors'):
        raise RuntimeError('GitHub GraphQL returned an error; no data was overwritten')
    try:
        cal=response['data']['user']['contributionsCollection']['contributionCalendar']
        days=[{'date':d['date'],'count':d['contributionCount']}
              for week in cal['weeks'] for d in week['contributionDays']]
    except (KeyError,TypeError) as err:
        raise RuntimeError('GitHub API returned an unexpected calendar structure') from err
    result={'username':USER,'total_contributions':cal['totalContributions'],'days':days,
            'source':'github-graphql-contributionCalendar',
            'fetched_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}
    # Strict consistency validation before writing any file
    from render_profile import validate_live_snapshot
    validate_live_snapshot(result)
    return result

def main()->int:
    try:
        data=read_data(os.environ.get('GITHUB_TOKEN',''))
        out=ROOT/'data'/'contributions.json'
        out.parent.mkdir(exist_ok=True)
        # Atomic replace prevents a truncated verified snapshot on interrupted writes.
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=out.parent,
                                         prefix='.contrib-', suffix='.tmp', delete=False) as stream:
            temp = Path(stream.name)
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.write('\n')
        try:
            temp.replace(out)
        finally:
            temp.unlink(missing_ok=True)
        print(f'Validated {len(data["days"])} GitHub calendar days and saved {out.relative_to(ROOT)}.')
        return 0
    except (RuntimeError,ValueError,HTTPError,URLError,TimeoutError) as exc:
        # Do not print token, request headers, or API payloads.
        print(f'ERROR: contribution sync failed ({type(exc).__name__}). Keeping previous artwork.',file=sys.stderr)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
