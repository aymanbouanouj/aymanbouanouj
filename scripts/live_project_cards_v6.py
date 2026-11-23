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

from v6_design_system import TOKENS

OWNER = "aymanbouanouj"
API = "https://api.github.com"
MAX_BYTES = 2_000_000
MAX_PIXELS = 6_000_000
DIMENSIONS = (TOKENS.project_card_width, TOKENS.project_card_height)
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
    """Real screenshot over a visually consistent reference-matched project card.

    The screenshot pixels come only from the verified public project; empty
    screenshot slots become clearly labelled placeholders, never fabricated art.
    """
    from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    width, height = DIMENSIONS
    canvas = Image.new("RGB", DIMENSIONS, TOKENS.background)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((1, 1, width - 2, height - 2), radius=22,
                           outline=TOKENS.border, width=3, fill=TOKENS.card)
    area = (8, 8, width - 8, 264)
    if raw is not None:
        try:
            with Image.open(io.BytesIO(raw)) as image:
                if image.format not in ("PNG", "JPEG", "WEBP") or getattr(image, "is_animated", False):
                    raise ValueError("Unsupported or animated project image")
                if image.width * image.height > MAX_PIXELS:
                    raise ValueError("Oversized image dimensions")
                image.verify()
            with Image.open(io.BytesIO(raw)) as loaded:
                photo = ImageOps.fit(
                    loaded.convert("RGB"),
                    (area[2] - area[0], area[3] - area[1]),
                    method=Image.Resampling.LANCZOS,
                )
                canvas.paste(photo, area[:2])
        except (UnidentifiedImageError, OSError) as err:
            raise ValueError("Untrusted project image cannot be decoded") from err
        veil = Image.new("RGBA", (width, area[3]), (0, 0, 0, 0))
        tint = ImageDraw.Draw(veil)
        # Darken the top/bottom of the *real screenshot* to integrate with the card.
        for py in range(area[3]):
            alpha = min(173, max(0, int((py - 108) * 1.10)))
            tint.line((area[0], py, area[2], py), fill=(9, 8, 28, alpha))
        canvas.paste(veil, (0, 0), veil)
    else:
        for py in range(area[1], area[3]):
            t = (py-area[1]) / (area[3]-area[1])
            r, g, b = (int(15 + 20*t), int(18 + 2*t), int(37 + 36*t))
            draw.line((area[0], py, area[2], py), fill=(r, g, b))
        # Subtle decorative area stays outside the readable placeholder label.
        draw.ellipse((448, 40, 590, 182), outline="#62419a", width=3)
        draw.ellipse((482, 74, 556, 148), outline="#3b2a62", width=2)

    def font(size: int, bold=False):
        names = (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        )
        for candidate in names:
            if Path(candidate).exists():
                return ImageFont.truetype(candidate, size)
        return ImageFont.load_default()

    slug, repo, title, summary, tags, _ = project
    if raw is None:
        draw.text((27, 73), "PROJECT IMAGE PENDING", font=font(28, True), fill=TOKENS.image_pending)
        draw.text((27, 121), "A cover will appear after upload", font=font(20),
                  fill="#cfc6e3")
        draw.text((27, 154), "to the public repository.", font=font(20), fill="#cfc6e3")

    # Keep the title only in the lower content card, not twice on the cover.
    draw.line((10, 267, width-10, 267), fill="#494359", width=2)
    draw.text((26, 285), title, font=font(30, True), fill="#ffffff")

    # Width-aware two-line wrapping. Never drop words or duplicate the title.
    summary_font = font(20)
    max_width = width - 52
    lines = []
    current = ""
    for word in summary.split():
        candidate = (current + " " + word).strip()
        if current and draw.textlength(candidate, font=summary_font) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    if len(lines) > 2:
        raise ValueError("Project summary exceeds two lines; shorten authored text")
    for i, line in enumerate(lines):
        draw.text((26, 336 + i*29), line, font=summary_font, fill="#e1dfee")

    tag_x = 25
    for tag in tags:
        w = int(draw.textlength(tag, font=font(17, True))) + 28
        draw.rounded_rectangle((tag_x, 405, tag_x+w, 444), radius=14,
                               fill="#282036", outline="#564666", width=2)
        draw.text((tag_x+14, 416), tag, font=font(17, True), fill="#ded1ff")
        tag_x += w+10
    draw.line((18, 466, width-18, 466), fill="#403b57", width=2)
    # Draw icons as geometry; uncommon Unicode symbols can render as empty boxes.
    from math import cos, sin, pi
    points = []
    for i in range(10):
        angle = -pi / 2 + i * pi / 5
        radius = 13 if i % 2 == 0 else 6
        points.append((43 + cos(angle)*radius, 506 + sin(angle)*radius))
    draw.line(points + [points[0]], fill="#f0e5ff", width=3, joint="curve")
    draw.text((62, 493), str(metadata["stars"]), font=font(22, True), fill="#f8f7ff")
    draw.ellipse((142, 495, 152, 505), outline="#f0e5ff", width=2)
    draw.ellipse((170, 495, 180, 505), outline="#f0e5ff", width=2)
    draw.ellipse((170, 514, 180, 524), outline="#f0e5ff", width=2)
    draw.line((147, 505, 147, 518, 175, 518, 175, 514), fill="#f0e5ff", width=2)
    draw.text((196, 493), str(metadata["forks"]), font=font(22, True), fill="#f8f7ff")
    draw.rounded_rectangle((415, 480, 613, 531), radius=15, fill="#29203d")
    draw.text((443, 496), "Source Code", font=font(19, True), fill="#dfb5ff")
    draw.line((571, 503, 591, 503, 591, 486), fill="#dfb5ff", width=2)
    draw.line((577, 493, 591, 486), fill="#dfb5ff", width=2)

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
