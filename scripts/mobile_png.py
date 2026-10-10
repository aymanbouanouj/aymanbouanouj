#!/usr/bin/env python3
"""Self-hosted mobile PNG fallbacks, strictly derived from verified local SVGs.

PNG is the direct README image for both mobile and desktop; the scalable SVG
versions remain available in assets and through the README's source links.
No external rasterization/image hosting API is involved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
MOBILE = ASSETS / "mobile"
MANIFEST = MOBILE / "manifest.json"
README = ROOT / "README.md"
COMPONENTS = ("hero", "contributions", "logo", "stats", "tech-stack", "engineering")
PNG_HEADER = b"\x89PNG\r\n\x1a\n"
MAX_FILE_SIZE = 4_000_000


def digest(contents: bytes) -> str:
    return hashlib.sha256(contents).hexdigest()


def dimensions(png: bytes) -> tuple[int, int]:
    if len(png) < 33 or not png.startswith(PNG_HEADER) or png[12:16] != b"IHDR":
        raise ValueError("Not a valid PNG header")
    width, height = struct.unpack(">II", png[16:24])
    if not 1 <= width <= 4096 or not 1 <= height <= 4096:
        raise ValueError("PNG dimensions outside safe bounds")
    if len(png) > MAX_FILE_SIZE:
        raise ValueError("PNG unexpectedly large")
    return width, height


def expected_dimensions(svg: bytes) -> tuple[int, int]:
    root = ET.fromstring(svg)
    if root.tag != "{http://www.w3.org/2000/svg}svg":
        raise ValueError("Invalid SVG namespace")
    width, height = root.get("width"), root.get("height")
    if not width or not height or not width.isdecimal() or not height.isdecimal():
        raise ValueError("SVG requires fixed integer dimensions")
    return 2 * int(width), 2 * int(height)


def render() -> None:
    # Deliberately load the rasterizer only in render mode, not while running
    # dependency-free offline unit tests and structural checks.
    import cairosvg

    MOBILE.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": 1, "source": "local-verified-svg", "scale": 2,
                "images": {}}
    for name in COMPONENTS:
        source = (ASSETS / (name + "-dark.svg")).read_bytes()
        expected = expected_dimensions(source)
        # Existing SVG sources are checked for embedded links/scripts by
        # scripts/validate.py before this call.
        output = cairosvg.svg2png(bytestring=source, scale=2)
        if dimensions(output) != expected:
            raise ValueError("Unexpected raster dimensions for " + name)
        target = MOBILE / (name + ".png")
        if not target.exists() or target.read_bytes() != output:
            target.write_bytes(output)
        manifest["images"][name] = {
            "svg_sha256": digest(source),
            "png_sha256": digest(output),
            "dimensions": list(expected),
        }
        print(f"{name}: {expected[0]}x{expected[1]}, {len(output)} bytes")
    new_json = json.dumps(manifest, indent=2) + "\n"
    if not MANIFEST.exists() or MANIFEST.read_text(encoding="utf-8") != new_json:
        MANIFEST.write_text(new_json, encoding="utf-8")
    verify()
    print("PASS: all mobile PNGs match the source SVGs")


def verify() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if (manifest.get("schema") != 1 or manifest.get("source") != "local-verified-svg"
            or manifest.get("scale") != 2
            or set(manifest.get("images", {})) != set(COMPONENTS)):
        raise ValueError("Untrusted or incomplete mobile raster manifest")
    for name in COMPONENTS:
        item = manifest["images"][name]
        svg = (ASSETS / (name + "-dark.svg")).read_bytes()
        png = (MOBILE / (name + ".png")).read_bytes()
        if (item["svg_sha256"] != digest(svg) or item["png_sha256"] != digest(png)
                or tuple(item["dimensions"]) != dimensions(png)
                or expected_dimensions(svg) != dimensions(png)):
            raise ValueError("Mobile PNG does not match the verified SVG: " + name)


DARK = re.compile(
    r'^<img src="\./assets/([a-z-]+)-dark\.svg#gh-dark-mode-only"'
    r' width="([^"]+)" alt="([^"]+)" />$'
)
LIGHT = re.compile(
    r'^<img src="\./assets/([a-z-]+)-light\.svg#gh-light-mode-only"'
    r' width="([^"]+)" alt="([^"]+)" />$'
)


def replace_readme(text: str) -> str:
    """Switch to simple, mobile-friendly PNG references only when complete."""
    lines = text.splitlines(keepends=True)
    rewritten = []
    seen = []
    index = 0
    while index < len(lines):
        first = DARK.fullmatch(lines[index].rstrip("\r\n"))
        second = (LIGHT.fullmatch(lines[index + 1].rstrip("\r\n"))
                  if first and index + 1 < len(lines) else None)
        if first and second:
            name, width, alt = first.groups()
            if name != second.group(1) or width != second.group(2) or alt != second.group(3):
                raise ValueError("Mismatched light and dark README images")
            if name not in COMPONENTS or name in seen:
                raise ValueError("Duplicate or unknown PNG target")
            seen.append(name)
            rewritten.append(
                f'<img src="./assets/mobile/{name}.png" width="{width}" alt="{alt}" />\n'
            )
            index += 2
        else:
            rewritten.append(lines[index])
            index += 1
    result = "".join(rewritten)
    if not seen:
        if all(f'./assets/mobile/{item}.png' in result for item in COMPONENTS):
            return result  # Already migrated.
        raise ValueError("README does not have an expected pre-migration layout")
    if set(seen) != set(COMPONENTS):
        raise ValueError("Incomplete migration of README artwork")
    if "Original scalable SVGs:" not in result:
        pos = result.rfind("</div>")
        if pos < 0:
            raise ValueError("Missing footer")
        links = " · ".join(
            f'<a href="./assets/{name}-dark.svg">{name.title()}</a>'
            for name in COMPONENTS
        )
        footer = (
            '<p><sub>Original scalable SVGs: ' + links +
            '. PNG previews ensure mobile-app compatibility.</sub></p>\n'
        )
        result = result[:pos] + footer + result[pos:]
    return result


def migrate() -> None:
    verify()  # Absolutely no broken README references can be pushed.
    current = README.read_text(encoding="utf-8")
    updated = replace_readme(current)
    if updated != current:
        README.write_text(updated, encoding="utf-8")
    print("PASS: README uses direct static PNG images and retains original SVG links")


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--render", action="store_true")
    group.add_argument("--verify", action="store_true")
    group.add_argument("--switch-readme", action="store_true")
    args = parser.parse_args()
    if args.render:
        render()
    elif args.switch_readme:
        migrate()
    else:
        verify()
        print("PASS: mobile PNG source hashes, bytes and dimensions verified")


if __name__ == "__main__":
    main()
