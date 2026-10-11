#!/usr/bin/env python3
"""Publish independently verified GitHub GraphQL contribution art, without private names.

The GitHub native public contribution count can differ from this snapshot due
to viewer settings, time zones, and cache. Only aggregate calendar data is used.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from fetch_contributions import read_data
from render_profile import heatmap, stats, validate_live_snapshot


FILES = ("contributions.svg", "stats.svg", "contributions.json")


def render(data: dict) -> dict[str, str]:
    validate_live_snapshot(data, require_fresh=False)
    graph = heatmap("dark", data)
    card = stats("dark", data)
    for xml in (graph, card):
        root = ET.fromstring(xml)
        if root.tag != "{http://www.w3.org/2000/svg}svg":
            raise ValueError("Unexpected SVG namespace")
        if "<script" in xml.lower() or "<foreignobject" in xml.lower():
            raise ValueError("Active XML is forbidden")
        if len(xml.encode("utf-8")) >= 500_000:
            raise ValueError("Oversized generated illustration")
    return {"contributions.svg": graph + "\n", "stats.svg": card + "\n",
            "contributions.json": json.dumps(data, indent=2, ensure_ascii=False) + "\n"}


def publish(folder: Path, data: dict) -> None:
    validate_live_snapshot(data)
    folder.mkdir(parents=True, exist_ok=True)
    for name, text in render(data).items():
        (folder / name).write_text(text, encoding="utf-8")


def verify(folder: Path) -> dict:
    data = json.loads((folder / "contributions.json").read_text(encoding="utf-8"))
    for name, expected in render(data).items():
        actual = (folder / name).read_text(encoding="utf-8")
        if actual != expected:
            raise ValueError("Generated contribution artifact does not match its source: " + name)
    return data


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--build", action="store_true")
    group.add_argument("--verify", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.build:
        import os
        data = read_data(os.getenv("GITHUB_TOKEN", ""))
        publish(args.output, data)
    verified = verify(args.output)
    print("PASS: trusted GraphQL contribution art; {} days verified".format(len(verified["days"])))


if __name__ == "__main__":
    main()
