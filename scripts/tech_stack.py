#!/usr/bin/env python3
"""Generate a verified Tech Stack from public owned GitHub repositories."""
from __future__ import annotations
import argparse
import datetime as dt
import html
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
OWNER="aymanbouanouj"
SOURCE="github-rest-linguist-public-owned"
API="https://api.github.com"
COLORS={"Python":"#3776ab","PHP":"#777bb4","JavaScript":"#e4bd26","TypeScript":"#3178c6",
        "HTML":"#e34f26","CSS":"#1572b6","PowerShell":"#5391fe","Shell":"#52b788",
        "Java":"#ed8b00","C":"#a8b9cc","C++":"#6295cb","C#":"#68217a",
        "Go":"#00add8","Rust":"#ce7045","SQL":"#a886ff","Blade":"#fa6c48",
        "Vue":"#42b883","Ruby":"#cc342d","Dart":"#0175c2","Kotlin":"#a77fff"}

def github_json(url,token="",opener=urlopen):
    if not url.startswith(API+"/"):
        raise ValueError("Non-GitHub API endpoint")
    headers={"User-Agent":"Ayman-Verified-TechStack/1.0",
             "Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"}
    if token:
        headers["Authorization"]="Bearer "+token
    with opener(Request(url,headers=headers),timeout=25) as response:
        if response.status != 200:
            raise RuntimeError("Unexpected GitHub API status")
        return json.load(response)

def eligible(repo):
    return (isinstance(repo,dict) and repo.get("private") is False and
            repo.get("fork") is False and repo.get("archived") is False and
            repo.get("disabled") is False and repo.get("name") != OWNER and
            isinstance(repo.get("name"),str) and
            re.fullmatch(r"[A-Za-z0-9_.-]{1,100}",repo["name"]) is not None and
            isinstance(repo.get("owner"),dict) and
            repo["owner"].get("login","").lower()==OWNER.lower())

def aggregate(repositories,language_lookup):
    bytes_by_language=defaultdict(int)
    evidence=defaultdict(list)
    seen=set()
    scanned=0
    for repo in repositories:
        if not eligible(repo):
            continue
        name=repo["name"]
        if name.casefold() in seen:
            raise ValueError("Duplicate public repository")
        seen.add(name.casefold())
        languages=language_lookup(name)
        if not isinstance(languages,dict):
            raise ValueError("Invalid GitHub languages response")
        scanned+=1
        for language,count in languages.items():
            if (not isinstance(language,str) or not 1<=len(language)<=70 or
                type(count) is not int or count<0):
                raise ValueError("Invalid language measurements")
            if count:
                bytes_by_language[language]+=count
                evidence[language].append(name)
    if not scanned or not bytes_by_language:
        raise ValueError("No public original languages found; keeping previous verified snapshot")
    rows=[{"name":name,"bytes":total,
           "repositories":sorted(evidence[name],key=str.casefold)}
          for name,total in bytes_by_language.items()]
    rows.sort(key=lambda row:(-len(row["repositories"]),-row["bytes"],row["name"].casefold()))
    return {"repository_count":scanned,"languages":rows}

def collect(token="",getter=github_json,now=None):
    repositories=[]
    for page in range(1,11):
        result=getter(f"{API}/users/{OWNER}/repos?type=owner&per_page=100&page={page}",token)
        if not isinstance(result,list):
            raise ValueError("Invalid public repository listing")
        repositories.extend(result)
        if len(result)<100:
            break
    else:
        raise ValueError("More than 1000 repositories: refusing incomplete scan")
    def lookup(repo):
        return getter(f"{API}/repos/{OWNER}/{quote(repo,safe='')}/languages",token)
    data=aggregate(repositories,lookup)
    clock=now or dt.datetime.now(dt.timezone.utc)
    if clock.tzinfo is None:
        raise ValueError("Missing timezone")
    return {"schema_version":1,"username":OWNER,"source":SOURCE,
            "scanned_at_utc":clock.astimezone(dt.timezone.utc).isoformat(),**data}

def verify(snapshot,now=None,max_age_hours=None):
    if (not isinstance(snapshot,dict) or snapshot.get("schema_version")!=1 or
        snapshot.get("username")!=OWNER or snapshot.get("source")!=SOURCE):
        raise ValueError("Untrusted language data source")
    timestamp=dt.datetime.fromisoformat(snapshot["scanned_at_utc"].replace("Z","+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError("Scan time must include UTC offset")
    clock=now or dt.datetime.now(dt.timezone.utc)
    age=(clock.astimezone(dt.timezone.utc)-timestamp.astimezone(dt.timezone.utc)).total_seconds()
    if age< -300 or (max_age_hours is not None and age>max_age_hours*3600):
        raise ValueError("Invalid or stale language scan")
    n=snapshot.get("repository_count")
    if type(n) is not int or not 1<=n<=1000:
        raise ValueError("Invalid number of scanned repositories")
    items=snapshot.get("languages")
    if not isinstance(items,list) or not 1<=len(items)<=300:
        raise ValueError("Missing or excessive language list")
    seen=set()
    for row in items:
        if not isinstance(row,dict):
            raise ValueError("Invalid language row")
        name=row.get("name")
        refs=row.get("repositories")
        if (not isinstance(name,str) or not 1<=len(name)<=70 or name in seen or
            type(row.get("bytes")) is not int or row["bytes"]<=0 or
            not isinstance(refs,list) or not 1<=len(refs)<=n or
            len(refs)!=len(set(refs)) or
            any(not isinstance(ref,str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}",ref) for ref in refs)):
            raise ValueError("Invalid language evidence")
        seen.add(name)

def render(theme,data=None):
    if theme not in ("dark","light"):
        raise ValueError("Unknown theme")
    if data is not None:
        verify(data)
    dark=theme=="dark"
    bg="#090c13" if dark else "#fbfcff"
    panel="#111827" if dark else "#f2f5fb"
    border="#303849" if dark else "#cbd5e1"
    ink="#f3f6ff" if dark else "#182236"
    muted="#a7b3c6" if dark else "#4d5d75"
    accent="#a886ff" if dark else "#6540b1"
    languages=data["languages"] if data else []
    height=max(225,120+max(1,(len(languages)+3)//4)*62+57)
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{height}" viewBox="0 0 1000 {height}" role="img" aria-labelledby="t d">',
         '<title id="t">Verified Tech Stack for Ayman Bounaouj</title>',
         '<desc id="d">Languages detected by GitHub Linguist in public owned non-fork repositories. Not a proficiency rating.</desc>',
         '<style>@keyframes reveal{from{opacity:0}to{opacity:1}}.tile{animation:reveal .35s ease-out both}@media(prefers-reduced-motion:reduce){.tile{animation:none!important;opacity:1!important}}</style>',
         f'<rect width="1000" height="{height}" rx="16" fill="{bg}"/>',
         f'<rect x="1" y="1" width="998" height="{height-2}" rx="15" fill="none" stroke="{border}"/>',
         f'<path d="M1 33 H999" stroke="{border}"/>',
         '<circle cx="24" cy="17" r="4" fill="#ff6467"/><circle cx="41" cy="17" r="4" fill="#f5c35b"/><circle cx="58" cy="17" r="4" fill="#47ce9b"/>',
         f'<text x="500" y="22" text-anchor="middle" font-family="Consolas,monospace" font-size="12" fill="{muted}">ayman@github: ~ / tech-stack --auto</text>',
         f'<text x="27" y="72" font-family="Consolas,monospace" font-size="18" font-weight="700" fill="{accent}">$ ./tech-stack.sh <tspan fill="{muted}">--detected</tspan></text>']
    if not data:
        svg.append(f'<text x="500" y="141" text-anchor="middle" font-family="Consolas,monospace" font-size="18" fill="{ink}">AWAITING FIRST VERIFIED LANGUAGE SCAN</text>')
    else:
        svg.append(f'<text x="973" y="73" text-anchor="end" font-family="Consolas,monospace" font-size="12" fill="{muted}">{len(languages)} languages · {data["repository_count"]} public repos</text>')
        for idx,row in enumerate(languages):
            x=27+(idx%4)*244
            y=92+(idx//4)*62
            name=html.escape(row["name"])
            shown=name if len(name)<=23 else name[:20]+"…"
            label="1 repo" if len(row["repositories"])==1 else str(len(row["repositories"]))+" repos"
            color=COLORS.get(row["name"],accent)
            svg.extend([f'<g class="tile" style="animation-delay:{(idx%8)*.03:.2f}s">',
                f'<rect x="{x}" y="{y}" width="231" height="51" rx="10" stroke="{border}" fill="{panel}"/>',
                f'<circle cx="{x+17}" cy="{y+17}" r="5" fill="{color}"/>',
                f'<text x="{x+30}" y="{y+22}" font-family="Arial,sans-serif" font-size="14" font-weight="700" fill="{ink}">{shown}</text>',
                f'<text x="{x+30}" y="{y+40}" font-family="Consolas,monospace" font-size="11" fill="{muted}">{label}</text></g>'])
    foot="GitHub Linguist · Public owned original repositories · Not a skill rating"
    if data:
        foot+=" · Scan: "+data["scanned_at_utc"][:16].replace("T"," ")+" UTC"
    svg.extend([f'<text x="500" y="{height-21}" text-anchor="middle" font-family="Consolas,monospace" font-size="11" fill="{muted}">{foot}</text>',"</svg>"])
    result="".join(svg)
    ET.fromstring(result)
    return result

def main():
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--fetch",action="store_true")
    group.add_argument("--render",action="store_true")
    group.add_argument("--verify",action="store_true")
    args=parser.parse_args()
    snapshot=ROOT/"data"/"tech-stack.json"
    files={theme:ROOT/"assets"/f"tech-stack-{theme}.svg" for theme in ("dark","light")}
    if args.fetch:
        value=collect(os.environ.get("GITHUB_TOKEN",""))
        verify(value,max_age_hours=2)
        snapshot.parent.mkdir(parents=True,exist_ok=True)
        snapshot.write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        print("Scanned",value["repository_count"],"public owned repositories;",len(value["languages"]),"languages")
    elif args.render:
        data=json.loads(snapshot.read_text(encoding="utf-8")) if snapshot.exists() else None
        if data: verify(data,max_age_hours=2)
        for theme,path in files.items():
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(render(theme,data),encoding="utf-8")
        print("Tech Stack artwork generated")
    else:
        data=json.loads(snapshot.read_text(encoding="utf-8")) if snapshot.exists() else None
        if data: verify(data)
        for theme,path in files.items():
            if path.read_text(encoding="utf-8") != render(theme,data):
                raise ValueError("Tech Stack artwork disagrees with latest verified data: "+theme)
        print("Verified Tech Stack snapshot and both SVGs")

if __name__=="__main__":
    main()
