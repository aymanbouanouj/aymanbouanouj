#!/usr/bin/env python3
"""Render V6 project-card PNGs with *real* public repository screenshots.

One optional image is discovered from each explicitly named public repository.
If not present, the reserved cover area remains a designed placeholder.
Only GitHub REST contents endpoints are consulted; private source is never read.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

OWNER = "aymanbouanouj"
API = "https://api.github.com"
MAX_BYTES = 2_000_000
MAX_PIXELS = 6_000_000
DIMENSIONS = (640, 630)
STANDARD_PATHS = (
    "assets/profile-cover.png", "assets/profile-cover.jpg", "assets/profile-cover.webp",
    "assets/profile-card.png", "media/readme/cover.png", "media/readme/preview.png",
    "docs/screenshots/cover.png",
)
PROJECTS = (
    ("morocco", "morocco2030", "Morocco 2030",
     "Multilingual tournament portal", ("Laravel", "React", "MySQL"),
     ("docs/screenshots/01-home.png",)),
    ("train", "ab-train-ticket-studio", "AB Train Ticket Studio",
     "Rail ticket booking and QR/PDF export", ("JavaScript", "Vite", "Playwright"),
     ("media/readme/desktop-journey.png", "media/readme/ticket-preview.png")),
    ("pc", "PC-Full-Check", "PC Full Check",
     "Privacy-first Windows diagnostics", ("PowerShell", "Windows"),
     ("docs/screenshots/overview.png",)),
)
CARD_FILES = tuple("v6-feature-" + p[0] + ".png" for p in PROJECTS)
MANIFEST = "v6-featured.json"
HEX40 = re.compile(r"^[a-f0-9]{40}$")
SAFE_BRANCH = re.compile(r"^[A-Za-z0-9._/-]{1,200}$")


def github_json(url: str, token: str):
    if not url.startswith(API + "/repos/" + OWNER + "/"):
        raise ValueError("Unexpected API host or owner")
    request = Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "ayman-profile-verified-project-card/1.0",
        "Authorization": "Bearer " + token,
    })
    with urlopen(request, timeout=22) as response:
        data = response.read(2_500_000)
        if len(data) >= 2_500_000:
            raise ValueError("Oversized GitHub API response")
    return json.loads(data)


def blob_sha(content: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()


def locate(repo: str, fetch):
    info = fetch(f"{API}/repos/{OWNER}/{repo}")
    if (not isinstance(info, dict) or info.get("private") is not False
        or (info.get("owner") or {}).get("login", "").casefold() != OWNER
        or info.get("name", "").casefold() != repo.casefold()):
        raise ValueError("Expected a verified public owner repository")
    branch = info.get("default_branch")
    if not isinstance(branch, str) or not SAFE_BRANCH.fullmatch(branch) or ".." in branch:
        raise ValueError("Invalid public default branch")
    stars = info.get("stargazers_count")
    forks = info.get("forks_count")
    if any(type(n) is not int or n < 0 or n > 1_000_000_000 for n in (stars, forks)):
        raise ValueError("Invalid public repository metrics")
    extra_paths = next(p[5] for p in PROJECTS if p[1] == repo)
    for path in (*STANDARD_PATHS, *extra_paths):
        url = f"{API}/repos/{OWNER}/{repo}/contents/{quote(path, safe='/')}?ref={quote(branch, safe='')}"
        try:
            item = fetch(url)
        except HTTPError as err:
            if err.code == 404:
                continue
            raise
        if (not isinstance(item, dict) or item.get("type") != "file"
            or item.get("path") != path or item.get("encoding") != "base64"
            or type(item.get("size")) is not int or not 0 < item["size"] <= MAX_BYTES
            or not isinstance(item.get("content"), str)
            or not isinstance(item.get("sha"), str)
            or not HEX40.fullmatch(item["sha"])):
            raise ValueError("Image path is present but its GitHub evidence is invalid")
        raw = base64.b64decode(item["content"].replace("\n", ""), validate=True)
        if len(raw) != item["size"] or blob_sha(raw) != item["sha"]:
            raise ValueError("Image bytes disagree with GitHub blob SHA")
        return {"repo": repo, "path": path, "source_sha": item["sha"],
                "stars": stars, "forks": forks}, raw
    return {"repo": repo, "path": None, "source_sha": None,
            "stars": stars, "forks": forks}, None


def render_card(project, metadata, raw: bytes | None) -> bytes:
    # Pillow is a dedicated publish-only dependency; routine profile verification
    # and legacy security scans do not import the package at module import time.
    from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    width, height = DIMENSIONS
    canvas = Image.new("RGB", DIMENSIONS, "#10121f")
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((1, 1, width - 2, height - 2), radius=27,
                           outline="#59436f", width=3, fill="#10121f")
    area = (9, 9, width - 9, 290)
    if raw is not None:
        try:
            with Image.open(io.BytesIO(raw)) as image:
                if image.format not in ("PNG", "JPEG", "WEBP") or image.is_animated:
                    raise ValueError("Unsupported or animated project image")
                if image.width * image.height > MAX_PIXELS:
                    raise ValueError("Oversized image dimensions")
                image.verify()
            with Image.open(io.BytesIO(raw)) as loaded:
                photo = ImageOps.fit(loaded.convert("RGB"), (area[2] - area[0], area[3] - area[1]),
                                     method=Image.Resampling.LANCZOS)
                canvas.paste(photo, area[:2])
        except (UnidentifiedImageError, OSError) as err:
            raise ValueError("Untrusted project image cannot be decoded") from err
        # A dark gradient preserves legibility and matches the supplied example.
        overlay = Image.new("RGBA", (width, area[3]), (0, 0, 0, 0))
        layer = ImageDraw.Draw(overlay)
        for y in range(170, area[3]):
            alpha = min(175, int((y - 170) * 1.4))
            layer.line((9, y, width - 9, y), fill=(6, 5, 21, alpha))
        canvas.paste(overlay, (0, 0), overlay)
    else:
        for y in range(9, area[3]):
            t = (y - 9) / (area[3] - 9)
            fill = (int(22 + 19*t), int(19 + 6*t), int(44 + 39*t))
            draw.line((9, y, width - 9, y), fill=fill)
        for i in range(5):
            draw.arc((-90 + i*48, 110 + i*16, 570 + i*95, 430 + i*42),
                     184, 324, fill="#5d2e96", width=2)
    def font(size: int, bold=False):
        paths = (("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
                 else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
                 "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf")
        for p in paths:
            if Path(p).exists():
                return ImageFont.truetype(p, size)
        return ImageFont.load_default()
    slug, repo, title, summary, tags, _ = project
    if raw is None:
        draw.text((29, 77), "PROJECT IMAGE", font=font(27, True), fill="#c3a5f5")
        draw.text((29, 122), "Reserved for a published", font=font(21), fill="#d5cbe1")
        draw.text((29, 153), "repository screenshot", font=font(21), fill="#d5cbe1")
    draw.text((25, 228), title, font=font(29, True), fill="#ffffff")
    draw.line((12, 290, width - 12, 290), fill="#4b4264", width=2)
    draw.text((25, 319), title, font=font(30, True), fill="#f8f7ff")
    draw.text((25, 369), summary, font=font(21), fill="#e0dfec")
    draw.text((25, 419), "   /   ".join(tags), font=font(21), fill="#c6a9f5")
    draw.rounded_rectangle((25, 468, width - 25, 534), radius=14,
                           outline="#574467", width=2, fill="#19182d")
    draw.text((42, 481), f"Stars: {metadata['stars']}    Forks: {metadata['forks']}",
              font=font(21), fill="#d8dce7")
    draw.text((25, 581), "SOURCE CODE / GITHUB", font=font(20, True), fill="#d2aaff")
    out = io.BytesIO()
    canvas.save(out, format="PNG", optimize=True)
    return out.getvalue()


def build(folder: Path, fetch) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": 1, "source": "github-rest-public-repository-contents",
                "owner": OWNER, "cards": []}
    for project in PROJECTS:
        slug, repo = project[:2]
        metadata, raw = locate(repo, fetch)
        png = render_card(project, metadata, raw)
        name = f"v6-feature-{slug}.png"
        (folder / name).write_bytes(png)
        manifest["cards"].append({**metadata, "file": name,
                                  "sha256": hashlib.sha256(png).hexdigest()})
    (folder / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    verify(folder)
    return manifest


def verify(folder: Path):
    data = json.loads((folder / MANIFEST).read_text(encoding="utf-8"))
    if data.get("schema") != 1 or data.get("owner") != OWNER or len(data.get("cards", [])) != len(PROJECTS):
        raise ValueError("Invalid verified project-card snapshot")
    for expected, item in zip(PROJECTS, data["cards"]):
        slug, name = expected[:2]
        if (item.get("repo") != name or item.get("file") != f"v6-feature-{slug}.png"
            or (item.get("path") is None) != (item.get("source_sha") is None)
            or type(item.get("stars")) is not int or type(item.get("forks")) is not int):
            raise ValueError("Project-card manifest mismatch")
        if item["path"] is not None and (item["path"] not in (*STANDARD_PATHS, *expected[5])
                                         or not HEX40.fullmatch(item["source_sha"])):
            raise ValueError("Unexpected source image")
        content = (folder / item["file"]).read_bytes()
        if (not content.startswith(b"\x89PNG\r\n\x1a\n") or
            hashlib.sha256(content).hexdigest() != item.get("sha256")):
            raise ValueError("Project-card PNG is missing or tampered")
    return data


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build", action="store_true")
    mode.add_argument("--verify", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.build:
        token = os.environ.get("GITHUB_TOKEN", "")
        if not token or len(token) < 10:
            raise ValueError("Missing ephemeral GitHub Actions credential")
        build(args.output, lambda url: github_json(url, token))
    verify(args.output)
    print("PASS: project images are source-verified, public, and tamper-checked")


if __name__ == "__main__":
    main()
