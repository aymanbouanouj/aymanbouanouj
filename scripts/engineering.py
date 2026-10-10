#!/usr/bin/env python3
"""Evidence-backed GitHub engineering dashboard; only public owned repository data."""
from __future__ import annotations
import argparse
import base64
import datetime as dt
import html
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from tech_stack import OWNER, eligible

ROOT=Path(__file__).resolve().parents[1]
SOURCE="github-rest-public-repo-evidence"
FEATURED=("morocco2030","PC-Full-Check","violetgate","ayman-calc")
FRAMEWORKS={"laravel/framework":"Laravel","laravel/sanctum":"Laravel Sanctum",
    "livewire/livewire":"Livewire","inertiajs/inertia-laravel":"Inertia.js",
    "react":"React","vue":"Vue","next":"Next.js","vite":"Vite",
    "tailwindcss":"Tailwind CSS","bootstrap":"Bootstrap","express":"Express",
    "fastapi":"FastAPI","flask":"Flask","django":"Django"}
MANIFESTS=("composer.json","package.json","requirements.txt","pyproject.toml")

def github_json(url,token=""):
    if not url.startswith("https://api.github.com/"):
        raise ValueError("Unsupported evidence endpoint")
    hdr={"Accept":"application/vnd.github+json","User-Agent":"AymanEngineeringEvidence/1.0",
         "X-GitHub-Api-Version":"2022-11-28"}
    if token:hdr["Authorization"]="Bearer "+token
    with urlopen(Request(url,headers=hdr),timeout=25) as response:
        return json.load(response)

def source_repo(name):
    if not isinstance(name,str) or not name or not all(x.isalnum() or x in "_.-" for x in name):
        raise ValueError("Unsafe repository name")
    return "https://api.github.com/repos/"+OWNER+"/"+quote(name,safe="")

def dependency_names(filename,content):
    if filename in ("composer.json","package.json"):
        data=json.loads(content)
        if not isinstance(data,dict):raise ValueError("Invalid manifest")
        keys=("require",) if filename=="composer.json" else ("dependencies","devDependencies")
        names=set()
        for key in keys:
            dep=data.get(key,{})
            if not isinstance(dep,dict):raise ValueError("Invalid dependency list")
            names.update(str(k).lower() for k in dep)
        return names
    if filename=="pyproject.toml":
        import tomllib
        deps=tomllib.loads(content).get("project",{}).get("dependencies",[])
        return {str(d).split("=",1)[0].split("<",1)[0].split(">",1)[0].split("[",1)[0].strip().lower() for d in deps}
    if filename=="requirements.txt":
        return {line.split("#",1)[0].split("=",1)[0].split("<",1)[0].split(">",1)[0].split("[",1)[0].strip().lower()
                for line in content.splitlines() if line.strip() and not line.lstrip().startswith("#")}
    return set()

def collect(token="",get=github_json,now=None):
    def ask(url):return get(url,token)
    repos=[]
    for page in range(1,11):
        r=ask(f"https://api.github.com/users/{OWNER}/repos?type=owner&per_page=100&page={page}")
        if not isinstance(r,list):raise ValueError("Invalid repository listing")
        repos.extend(r)
        if len(r)<100:break
    else:raise ValueError("Repository listing not complete")
    eligible_repos=[r for r in repos if eligible(r)]
    if not eligible_repos:raise ValueError("No public original repositories")
    frameworks={}
    for repo in eligible_repos:
        name=repo["name"]
        for manifest in MANIFESTS:
            try:raw=ask(source_repo(name)+"/contents/"+manifest)
            except HTTPError as e:
                if e.code==404:continue
                raise
            if not isinstance(raw,dict) or raw.get("type")!="file" or raw.get("encoding")!="base64" or raw.get("size",0)>256000:
                raise ValueError("Malformed manifest response")
            text=base64.b64decode(raw["content"]).decode("utf-8")
            for dependency in dependency_names(manifest,text):
                if dependency in FRAMEWORKS:
                    frameworks.setdefault(FRAMEWORKS[dependency],set()).add(name)
    featured=[]
    available={r["name"]:r for r in eligible_repos}
    for name in FEATURED:
        if name not in available:continue
        branch=available[name].get("default_branch") or "main"
        runs=ask(source_repo(name)+"/actions/runs?branch="+quote(branch,safe="")+"&per_page=40")
        if not isinstance(runs,dict) or not isinstance(runs.get("workflow_runs"),list):
            raise ValueError("Invalid public GitHub workflow results")
        latest=next((x for x in runs["workflow_runs"]
           if x.get("head_branch")==branch and x.get("status")=="completed"
           and x.get("event") in ("push","workflow_dispatch")
           and x.get("name") in ("CI","Quality checks","CodeQL")),None)
        releases=ask(source_repo(name)+"/releases?per_page=10")
        if not isinstance(releases,list):raise ValueError("Invalid release listing")
        release=next((x for x in releases if x.get("draft") is False and x.get("prerelease") is False),None)
        if not release:release=next((x for x in releases if x.get("draft") is False),None)
        ci=latest.get("conclusion") if latest else "not-verified"
        if ci not in ("success","failure","cancelled","timed_out","neutral","skipped","action_required"):
            ci="unknown" if latest else "not-verified"
        featured.append({"name":name,"url":"https://github.com/"+OWNER+"/"+name,
            "ci":ci,"ci_name":latest.get("name") if latest else None,
            "ci_url":latest.get("html_url") if latest else None,
            "release":release.get("tag_name") if release else None,
            "release_url":release.get("html_url") if release else None})
    if len(featured)<2:raise ValueError("Not enough public featured repositories")
    stamp=(now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc).isoformat()
    rows=[{"name":name,"repositories":sorted(refs,key=str.casefold)} for name,refs in frameworks.items()]
    rows.sort(key=lambda x:(-len(x["repositories"]),x["name"].casefold()))
    return {"schema":1,"owner":OWNER,"source":SOURCE,"checked_at_utc":stamp,
            "frameworks":rows,"projects":featured,"public_repositories_scanned":len(eligible_repos)}

def verify(data,max_age_hours=None):
    if not isinstance(data,dict) or data.get("schema")!=1 or data.get("owner")!=OWNER or data.get("source")!=SOURCE:
        raise ValueError("Untrusted engineering evidence")
    timestamp=dt.datetime.fromisoformat(data["checked_at_utc"].replace("Z","+00:00"))
    if timestamp.tzinfo is None:raise ValueError("Timestamp missing timezone")
    age=(dt.datetime.now(dt.timezone.utc)-timestamp.astimezone(dt.timezone.utc)).total_seconds()
    if age< -300 or (max_age_hours is not None and age>3600*max_age_hours):
        raise ValueError("Stale or future-dated engineering evidence")
    frameworks=data.get("frameworks")
    projects=data.get("projects")
    if not isinstance(frameworks,list) or not isinstance(projects,list) or not 2<=len(projects)<=4:
        raise ValueError("Invalid engineering lists")
    for row in frameworks:
        if row.get("name") not in FRAMEWORKS.values() or not isinstance(row.get("repositories"),list):
            raise ValueError("Invalid framework claim")
    for p in projects:
        if p.get("name") not in FEATURED or p.get("ci") not in ("success","failure","cancelled","timed_out","neutral","skipped","action_required","unknown","not-verified"):
            raise ValueError("Invalid project evidence")
        if p.get("url")!="https://github.com/"+OWNER+"/"+p["name"]:
            raise ValueError("Invalid project URL")

def render(theme,data=None):
    if theme not in ("dark","light"):raise ValueError("Unknown theme")
    if data:verify(data)
    dark=theme=="dark"
    bg="#090c13" if dark else "#fbfcff"
    ink="#f3f6ff" if dark else "#182236"
    card="#121827" if dark else "#f0f3fa"
    border="#303849" if dark else "#cbd5e1"
    muted="#a7b3c6" if dark else "#4d5d75"
    accent="#a886ff" if dark else "#6540b1"
    cyan="#4dd4cf" if dark else "#137e87"
    height=365 if data else 202
    pieces=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{height}" viewBox="0 0 1000 {height}" role="img" aria-labelledby="t d">',
      '<title id="t">Verified engineering tools and repository quality signals</title>',
      '<desc id="d">Frameworks detected from public dependency manifests, release tags and CI results. Not a skill rating.</desc>',
      '<style>@keyframes fade{from{opacity:0}to{opacity:1}}.tile{animation:fade .4s ease both}@media(prefers-reduced-motion:reduce){.tile{animation:none!important;opacity:1!important}}</style>',
      f'<rect width="1000" height="{height}" rx="14" fill="{bg}"/><rect x="1" y="1" width="998" height="{height-2}" rx="14" fill="none" stroke="{border}"/>',
      f'<path d="M0 32 H1000" stroke="{border}"/>',
      '<circle cx="23" cy="16" r="4" fill="#ff6467"/><circle cx="40" cy="16" r="4" fill="#f5c35b"/><circle cx="57" cy="16" r="4" fill="#47ce9b"/>',
      f'<text x="500" y="21" text-anchor="middle" font-size="12" font-family="monospace" fill="{muted}">ayman@github: ~ / engineering --verified</text>',
      f'<text x="25" y="67" font-size="17" font-family="monospace" font-weight="700" fill="{accent}">$ ./engineering.sh --public-evidence</text>']
    if not data:
        pieces.append(f'<text x="500" y="133" text-anchor="middle" font-size="18" font-family="monospace" fill="{ink}">AWAITING FIRST VERIFIED ENGINEERING SCAN</text>')
    else:
        pieces.append(f'<text x="26" y="101" font-size="14" font-family="monospace" fill="{cyan}">FRAMEWORKS &amp; BUILD TOOLS · public dependency manifests</text>')
        for i,row in enumerate(data["frameworks"][:8]):
            x=25+i%4*245;y=112+(i//4)*50
            n=html.escape(row["name"]);count=len(row["repositories"])
            pieces.extend([f'<g class="tile"><rect x="{x}" y="{y}" width="231" height="40" rx="7" fill="{card}" stroke="{border}"/>',
              f'<text x="{x+12}" y="{y+18}" font-size="14" font-weight="700" font-family="Arial,sans-serif" fill="{ink}">{n}</text>',
              f'<text x="{x+12}" y="{y+33}" font-size="10" font-family="monospace" fill="{muted}">{count} public repo{("s" if count!=1 else "")}</text></g>'])
        if not data["frameworks"]:
            pieces.append(f'<text x="30" y="142" font-size="14" fill="{muted}">No recognized public manifests</text>')
        pieces.append(f'<text x="26" y="231" font-size="14" font-family="monospace" fill="{cyan}">PROJECT SIGNALS · published releases and named CI</text>')
        for i,row in enumerate(data["projects"]):
            x=25+i%2*490;y=244+i//2*47
            ci=row["ci"].upper().replace("NOT-VERIFIED","NOT VERIFIED")
            release=html.escape(row.get("release") or "No published release")
            color="#49d2a1" if row["ci"]=="success" else "#f1c471" if row["ci"]=="not-verified" else "#ef9397"
            pieces.extend([f'<rect x="{x}" y="{y}" width="473" height="39" rx="7" fill="{card}" stroke="{border}"/>',
              f'<text x="{x+10}" y="{y+17}" font-size="13" font-weight="700" font-family="Arial,sans-serif" fill="{ink}">{html.escape(row["name"])}</text>',
              f'<text x="{x+10}" y="{y+32}" font-size="11" font-family="monospace" fill="{muted}">Release: {release}</text>',
              f'<text x="{x+462}" y="{y+23}" text-anchor="end" font-size="11" font-family="monospace" font-weight="700" fill="{color}">{ci}</text>'])
    footer="Sources: public GitHub manifests, releases and Actions; not a proficiency score"
    if data:footer+=" · "+data["checked_at_utc"][:16].replace("T"," ")+" UTC"
    pieces.append(f'<text x="500" y="{height-15}" text-anchor="middle" font-size="11" font-family="monospace" fill="{muted}">{html.escape(footer)}</text>')
    pieces.append("</svg>")
    result="".join(pieces);ET.fromstring(result);return result

def main():
    cli=argparse.ArgumentParser()
    group=cli.add_mutually_exclusive_group(required=True)
    for op in ("fetch","render","verify"):group.add_argument("--"+op,action="store_true")
    args=cli.parse_args();path=ROOT/"data"/"engineering.json"
    if args.fetch:
        data=collect(os.environ.get("GITHUB_TOKEN",""));verify(data,max_age_hours=2)
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    else:
        data=json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        if data:verify(data,max_age_hours=2 if args.render else None)
        for theme in ("dark","light"):
            dest=ROOT/"assets"/f"engineering-{theme}.svg"
            if args.render:dest.write_text(render(theme,data),encoding="utf-8")
            elif dest.read_text(encoding="utf-8")!=render(theme,data):
                raise ValueError("Engineering snapshot and SVG are inconsistent")
    print("Engineering "+("verified" if args.verify else "completed"))

if __name__=="__main__":main()
