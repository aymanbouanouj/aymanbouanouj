#!/usr/bin/env python3
"""Generate original GitHub-safe artwork, preserving Ayman's actual AB+arrow silhouette.

No runtime image host, JavaScript, external fonts or third-party badge scripts.
Real statistics ONLY from validated GitHub API data. Never publish synthetic fixtures.
"""
from __future__ import annotations
import argparse
import datetime as dt
import html
import json
from collections import Counter
from pathlib import Path
from brand_paths import WHITE, PURPLE

ROOT=Path(__file__).resolve().parents[1]
USER='aymanbouanouj'
NAMESPACE='http://www.w3.org/2000/svg'
PALETTES={
 'dark':dict(bg='#090c13', top='#111621', panel='#0d121d',card='#161d2b',border='#303849',ink='#f5f7ff',muted='#9ca8be',accent='#a886ff',cyan='#51dfda',green='#38d992',faint='#1b2530',ramp=['#19242f','#12442f','#1d754a','#279d5e','#38d992']),
 'light':dict(bg='#fcfcff',top='#f1f3fa',panel='#ffffff',card='#f5f6fb',border='#cbd2df',ink='#172033',muted='#556378',accent='#7044c7',cyan='#117d86',green='#218951',faint='#e4e8f0',ramp=['#e2e7ed','#b4dfbe','#72bf8a','#3aa46a','#218951'])
}

def e(x): return html.escape(str(x),quote=True)

def start(w,h,title,desc):
 return (f'<svg xmlns="{NAMESPACE}" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="t d">'
         f'<title id="t">{e(title)}</title><desc id="d">{e(desc)}</desc>')

def styling():
 return """<style>
  @keyframes appear{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:translateY(0)}}
  @keyframes draw{from{opacity:0}to{opacity:1}}
  @keyframes load{from{transform:scaleY(.02)}to{transform:scaleY(1)}}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.45}}
  .enter{animation:appear .8s ease-out both}
  .cell{animation:draw .44s ease-in both}
  .line{animation:draw .32s ease-in both}
  .bar{transform-box:fill-box;transform-origin:center bottom;animation:load .6s ease-out both}
  .cursor{animation:pulse 1.3s ease-in-out infinite}
  @media (prefers-reduced-motion:reduce){.enter,.cell,.line,.bar,.cursor{animation:none!important;opacity:1!important;transform:none!important}}
 </style>"""

def frame(w,h,p,label):
 return (f'<rect width="{w}" height="{h}" rx="16" fill="{p["bg"]}"/>'
         f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="15" fill="none" stroke="{p["border"]}"/>'
         f'<rect x="1" y="1" width="{w-2}" height="32" rx="15" fill="{p["top"]}"/>'
         f'<rect x="1" y="19" width="{w-2}" height="14" fill="{p["top"]}"/>'
         f'<path d="M1 33 H{w-1}" stroke="{p["border"]}"/>'
         +''.join(f'<circle cx="{24+17*i}" cy="17" r="4" fill="{c}"/>' for i,c in enumerate(['#ff6467','#f5c35b','#47ce9b']))
         +f'<text x="{w//2}" y="21" text-anchor="middle" font-family="Consolas,monospace" font-size="12" fill="{p["muted"]}">{e(label)}</text>')

def brandmark(x,y,w,h,theme):
 # SVG paths are native vectors traced from the owner's existing logo.
 # Recolor pale metallic shapes for legibility on GitHub's light theme.
 highlights=('#ffffff','#f0f1f5','#c6cad2') if theme=='dark' else ('#111827','#303b51','#48566d')
 return (f'<g transform="translate({x} {y}) scale({w/340:.4f} {h/205:.4f})">'
         '<defs><linearGradient id="metal" x1="0" x2=".28" y1="0" y2="1">'
         f'<stop stop-color="{highlights[0]}"/><stop offset=".62" stop-color="{highlights[1]}"/><stop offset="1" stop-color="{highlights[2]}"/></linearGradient>'
         '<linearGradient id="violetGrad" x1="0" y1="1" x2="1" y2="0">'
         '<stop stop-color="#8e32ec"/><stop offset=".5" stop-color="#b748ff"/><stop offset="1" stop-color="#7b40ff"/></linearGradient></defs>'
         f'<path d="{WHITE}" fill="url(#metal)" fill-rule="evenodd"/>'
         f'<path d="{PURPLE}" fill="url(#violetGrad)" fill-rule="evenodd"/>'
         '</g>')

def hero(theme):
 p=PALETTES[theme]; w,h=1000,280
 s=[start(w,h,'Ayman Bounaouj — original developer brand','Ayman Bounaouj, software developer. Original AB logo with purple upward arrow, rendered in a terminal-style banner.'),styling(),frame(w,h,p,'ayman@github: ~ / identity'),
    f'<rect x="28" y="58" width="231" height="187" rx="12" fill="{p["panel"]}" stroke="{p["border"]}"/>',
    brandmark(37,72,207,135,theme),
    f'<text x="143" y="229" text-anchor="middle" letter-spacing="2.5" font-family="Consolas,monospace" font-size="10" fill="{p["muted"]}">ORIGINAL MARK</text>',
    f'<text x="294" y="89" font-family="Consolas,monospace" font-size="14" fill="{p["cyan"]}">$ whoami <tspan class="cursor" fill="{p["accent"]}">▌</tspan></text>',
    f'<text class="enter" x="294" y="147" font-family="Arial,Helvetica,sans-serif" letter-spacing="1.5" font-size="48" font-weight="800" fill="{p["ink"]}">AYMAN BOUNAOUJ</text>',
    f'<text x="296" y="183" font-family="Consolas,monospace" font-size="16" fill="{p["accent"]}">SOFTWARE DEVELOPER  /  FULL-STACK WEB</text>',
    f'<text x="296" y="213" font-family="Arial,Helvetica,sans-serif" font-size="15" fill="{p["muted"]}">Building practical, secure &amp; user-centered digital products.</text>',
    f'<circle cx="302" cy="241" r="4" fill="{p["green"]}"/><text x="315" y="245" font-family="Consolas,monospace" font-size="12" fill="{p["muted"]}">MOROCCO  •  PUBLIC PROJECTS  •  BUILD &amp; VERIFY</text>',
    '</svg>']
 return ''.join(s)

def canonical_days(data):
    """Validate the complete GitHub calendar, never silently fix malformed data."""
    if not isinstance(data, dict) or data.get('username') != USER:
        raise ValueError('Wrong GitHub username')
    raw = data.get('days')
    if not isinstance(raw, list) or not 300 <= len(raw) <= 385:
        raise ValueError('Invalid calendar size')
    last = None
    out = []
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get('date'), str):
            raise ValueError('Invalid calendar date structure')
        text = item['date']
        if len(text) != 10 or text[4] != '-' or text[7] != '-':
            raise ValueError('Invalid ISO date string')
        try:
            date = dt.date.fromisoformat(text)
        except ValueError as ex:
            raise ValueError('Invalid ISO date') from ex
        count = item.get('count')
        if type(count) is not int or not 0 <= count <= 100_000:
            raise ValueError('Invalid contribution count')
        if last is not None and date - last != dt.timedelta(days=1):
            raise ValueError('Calendar must have consecutive dates')
        out.append({'date': date, 'count': count})
        last = date
    total = data.get('total_contributions')
    if type(total) is not int or sum(d['count'] for d in out) != total:
        raise ValueError('Total mismatches counts')
    return out


def validate_live_snapshot(data, now=None, require_fresh=True):
    """Fail closed: the publish path must never render an old/fictional snapshot."""
    days = canonical_days(data)
    if data.get('source') != 'github-graphql-contributionCalendar':
        raise ValueError('Unexpected data source; require official GitHub GraphQL')
    fetched = data.get('fetched_at_utc')
    if not isinstance(fetched, str):
        raise ValueError('Missing timestamp')
    try:
        fetched_at = dt.datetime.fromisoformat(fetched.replace('Z', '+00:00'))
    except ValueError as ex:
        raise ValueError('Invalid fetched_at_utc') from ex
    if fetched_at.tzinfo is None or fetched_at.utcoffset() != dt.timedelta(0):
        raise ValueError('Timestamp must be UTC with timezone')
    now = now or dt.datetime.now(dt.timezone.utc)
    age = now - fetched_at
    if require_fresh and not dt.timedelta(minutes=-5) <= age <= dt.timedelta(hours=36):
        raise ValueError('Snapshot is stale or dated in the future')
    last_date = days[-1]['date']
    # Time zone differences may legitimately shift the calendar by one day.
    if require_fresh and abs((last_date - now.date()).days) > 1:
        raise ValueError('GitHub calendar end date is not current')
    return days


def analysis(data, reference_date=None):
    days = canonical_days(data)
    today = reference_date or dt.datetime.now(dt.timezone.utc).date()
    if isinstance(today, dt.datetime):
        today = today.date()
    if not isinstance(today, dt.date):
        raise ValueError('reference_date must be a date')
    if days[0]['date'] > today:
        raise ValueError('Calendar starts in the future')
    usable = [day for day in days if day['date'] <= today]
    if not usable:
        raise ValueError('Calendar has no current entries')
    i = len(usable) - 1
    # A current streak must include today or yesterday (today may be incomplete).
    # A historical streak is NOT current, even when the snapshot ends on a nonzero day.
    if (today - usable[i]['date']).days > 1:
        current = 0
    else:
        if usable[i]['date'] == today and usable[i]['count'] == 0:
            i -= 1
        current = 0
        if i >= 0 and (today - usable[i]['date']).days <= 1:
            while i >= 0 and usable[i]['count'] > 0:
                current += 1
                i -= 1
    longest = run = 0
    for day in usable:
        run = run + 1 if day['count'] > 0 else 0
        longest = max(longest, run)
    monthly = Counter()
    for day in usable:
        monthly[day['date'].strftime('%Y-%m')] += day['count']
    months = list(dict.fromkeys(day['date'].strftime('%Y-%m') for day in usable))[-12:]
    return dict(days=days, total=sum(day['count'] for day in days),
                active=sum(day['count'] > 0 for day in usable),
                current=current, longest=longest,
                months=[(month, monthly[month]) for month in months],
                range=(days[0]['date'], days[-1]['date']))

def heatmap(theme,data=None,demo=False):
 p=PALETTES[theme];w,h=1000,255
 s=[start(w,h,'Contribution calendar','Calendar updated from GitHub GraphQL; pending sync if no data fetched.'),styling(),frame(w,h,p,'ayman@github: ~ / contributions'),
    f'<text x="32" y="67" font-family="Consolas,monospace" font-size="16" fill="{p["cyan"]}">$ ./contributions.sh <tspan fill="{p["muted"]}">--last-year</tspan></text>']
 cell,step,x0,y0=10,15,58,111
 if data is None:
  # Neutral empty cells are a layout skeleton, NOT fabricated contributions.
  for wk in range(53):
   for row in range(7):
    s.append(f'<rect x="{x0+wk*step}" y="{y0+row*step}" width="{cell}" height="{cell}" rx="2" fill="{p["faint"]}"/>')
  s.append(f'<rect x="265" y="131" width="470" height="57" rx="8" fill="{p["panel"]}" stroke="{p["accent"]}"/>')
  s.append(f'<text x="500" y="154" text-anchor="middle" font-family="Consolas,monospace" font-size="16" font-weight="700" fill="{p["ink"]}">AWAITING FIRST GITHUB SYNC</text>')
  s.append(f'<text x="500" y="176" text-anchor="middle" font-family="Consolas,monospace" font-size="11" fill="{p["muted"]}">No contribution activity is inferred or simulated.</text>')
 else:
  a=analysis(data);first=a['days'][0]['date'];sunday=first-dt.timedelta(days=(first.weekday()+1)%7)
  for d in a['days']:
   index=(d['date']-sunday).days; wk,row=divmod(index,7);level=0 if d['count']==0 else 1 if d['count']<=2 else 2 if d['count']<=6 else 3 if d['count']<=12 else 4
   s.append(f'<rect class="cell" x="{x0+wk*step}" y="{y0+row*step}" width="{cell}" height="{cell}" rx="2" fill="{p["ramp"][level]}" style="animation-delay:{min(wk*.018+row*.02,1.5):.3f}s"><title>{d["date"].isoformat()}: {d["count"]} contributions</title></rect>')
  seen=set()
  for d in a['days']:
   k=d['date'].strftime('%Y-%m')
   if k not in seen and d['date'].day<=7:
    seen.add(k);x=x0+((d['date']-sunday).days//7)*step
    s.append(f'<text x="{x}" y="97" font-family="Consolas,monospace" font-size="10" fill="{p["muted"]}">{d["date"].strftime("%b")}</text>')
  s.append(f'<text x="34" y="235" font-family="Consolas,monospace" font-size="14" font-weight="700" fill="{p["ink"]}">{a["total"]:,} contributions / rolling year</text>')
  s.append(f'<text x="970" y="235" text-anchor="end" font-family="Consolas,monospace" font-size="11" fill="{p["muted"]}">{a["range"][0]} to {a["range"][1]}</text>')
 for row,lbl in ((1,'Mon'),(3,'Wed'),(5,'Fri')):
  s.append(f'<text x="18" y="{y0+row*step+9}" font-family="Consolas,monospace" font-size="10" fill="{p["muted"]}">{lbl}</text>')
 if data is None:s.append(f'<text x="34" y="236" font-family="Consolas,monospace" font-size="12" fill="{p["muted"]}">SOURCE github.com  /  STATUS waiting for authenticated sync</text>')
 if demo:s.append(f'<text x="968" y="66" text-anchor="end" font-family="Consolas,monospace" font-size="12" fill="{p["accent"]}">DEMO FIXTURE · NOT LIVE</text>')
 s.append('</svg>');return ''.join(s)

# Dense ASCII artwork of the *same* monogram, stored locally in plain text for reproducibility.
def ascii_art():
 return (ROOT/'scripts'/'monogram-ascii.txt').read_text(encoding='utf-8').splitlines()

def ascii_panel(theme):
 p=PALETTES[theme];w,h=495,500
 s=[start(w,h,'ASCII AB brand signature','Original AB and arrow brand mark drawn as terminal ASCII art.'),styling(),frame(w,h,p,'ayman@github: ~ / identity --ascii'),
    f'<text x="22" y="65" font-family="Consolas,monospace" font-size="14" fill="{p["cyan"]}">$ cat brand.txt</text>',
    f'<rect x="18" y="81" width="459" height="356" rx="10" fill="{p["panel"]}" stroke="{p["border"]}"/>']
 lines=ascii_art()
 for i,row in enumerate(lines):
  # Content contains only ASCII, escaped even though generated from a local vector trace.
  s.append(f'<text class="line" xml:space="preserve" x="35" y="{103+i*8.2:.1f}" fill="{p["ink"]}" font-family="Consolas,monospace" font-size="8.15" letter-spacing=".5" style="animation-delay:{i*.048:.3f}s">{e(row)}</text>')
 s.append(f'<path class="enter" d="{e(PURPLE)}" transform="matrix(1.06 0 0 1.55 27.3 88.5)" fill="{p["accent"]}" opacity=".90"/>')
 s.append(f'<text x="21" y="472" font-family="Consolas,monospace" font-size="12" fill="{p["muted"]}">ayman@github:~$ <tspan fill="{p["accent"]}">Ayman Bounaouj</tspan></text>')
 s.append('</svg>');return ''.join(s)

def stats(theme,data=None,demo=False):
 p=PALETTES[theme];w,h=495,500
 s=[start(w,h,'GitHub activity analytics','Contribution totals, active days and verified monthly graph. No invented metrics.'),styling(),frame(w,h,p,'ayman@github: ~ / metrics --verified'),
    f'<text x="20" y="65" font-family="Consolas,monospace" font-size="14" fill="{p["cyan"]}">$ ./stats.sh <tspan fill="{p["muted"]}">--github</tspan></text>']
 a=analysis(data) if data else None
 tiles=[('CONTRIBUTIONS',f'{a["total"]:,}' if a else '—'),('ACTIVE DAYS',str(a['active']) if a else '—'),('CURRENT STREAK',f'{a["current"]}d' if a else '—'),('LONGEST STREAK',f'{a["longest"]}d' if a else '—')]
 for i,(name,val) in enumerate(tiles):
  xx=20+(i%2)*238;yy=85+(i//2)*106
  s.extend([f'<rect x="{xx}" y="{yy}" width="217" height="93" rx="9" stroke="{p["border"]}" fill="{p["card"]}"/>',
            f'<text x="{xx+15}" y="{yy+28}" font-family="Consolas,monospace" font-size="11" fill="{p["muted"]}">{name}</text>',
            f'<text class="enter" x="{xx+15}" y="{yy+70}" font-family="Arial,Helvetica,sans-serif" font-size="30" font-weight="700" fill="{p["cyan"] if i==0 else p["ink"]}">{val}</text>'])
 s.append(f'<rect x="20" y="308" width="455" height="163" rx="9" stroke="{p["border"]}" fill="{p["card"]}"/>')
 s.append(f'<text x="36" y="335" font-family="Consolas,monospace" font-size="12" fill="{p["muted"]}">contributions / month</text>')
 if data is None:
  s.append(f'<text x="247" y="402" text-anchor="middle" font-family="Consolas,monospace" font-size="16" fill="{p["ink"]}">AWAITING FIRST SYNC</text>')
  s.append(f'<text x="247" y="428" text-anchor="middle" font-family="Consolas,monospace" font-size="11" fill="{p["muted"]}">All counts will come from GitHub.</text>')
 else:
  values=a['months'];peak=max(1,max(n for _,n in values))
  for j,(month,n) in enumerate(values):
   height=79*n/peak;xx=44+j*35
   s.append(f'<rect class="bar" x="{xx}" y="{440-height:.1f}" width="20" height="{max(1,height):.1f}" rx="3" fill="{p["cyan"] if n==peak else p["accent"]}" style="animation-delay:{j*.06:.2f}s"/>')
   s.append(f'<text x="{xx+10}" y="460" text-anchor="middle" font-family="Consolas,monospace" font-size="9" fill="{p["muted"]}">{month[5:]}</text>')
 if data is not None:
  stamp=e(data.get('fetched_at_utc','UNVERIFIED')[:16].replace('T',' ')+' UTC') if not demo else 'DEMO / NOT LIVE'
  s.append(f'<text x="465" y="490" text-anchor="end" font-family="Consolas,monospace" font-size="10" fill="{p["muted"]}">Synced: {stamp}</text>')
 if demo:s.append(f'<text x="476" y="66" text-anchor="end" font-family="Consolas,monospace" font-size="10" fill="{p["accent"]}">DEMO DATA · NOT LIVE</text>')
 s.append('</svg>');return ''.join(s)

def write_assets(target,data=None,demo=False,include_static=True):
 target.mkdir(parents=True,exist_ok=True)
 for theme in ('dark','light'):
  if include_static:
   (target/f'hero-{theme}.svg').write_text(hero(theme),encoding='utf-8')
   (target/f'ascii-{theme}.svg').write_text(ascii_panel(theme),encoding='utf-8')
  (target/f'contributions-{theme}.svg').write_text(heatmap(theme,data,demo),encoding='utf-8')
  (target/f'stats-{theme}.svg').write_text(stats(theme,data,demo),encoding='utf-8')

def main():
 cli=argparse.ArgumentParser()
 cli.add_argument('--data',type=Path)
 cli.add_argument('--placeholder',action='store_true')
 cli.add_argument('--demo',action='store_true')
 a=cli.parse_args()
 if bool(a.data)==bool(a.placeholder):cli.error('Specify exactly one of --data or --placeholder')
 if a.demo and not a.data:cli.error('--demo requires a data fixture')
 data=json.loads(a.data.read_text(encoding='utf-8')) if a.data else None
 if data is not None:
  analysis(data, reference_date=dt.date.fromisoformat(data['days'][-1]['date']) if a.demo else None)
  if not a.demo: validate_live_snapshot(data)
 dest=ROOT/'docs'/'demo' if a.demo else ROOT/'assets'
 write_assets(dest,data,a.demo,include_static=not a.demo)
 print('Generated',dest,'(demo only)' if a.demo else '(publishable verified data)' if data else '(no statistics yet)')
if __name__=='__main__':main()
