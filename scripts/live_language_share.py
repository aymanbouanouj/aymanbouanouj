"""Render a compact, optional language distribution from the verified V5 snapshot."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from live_portfolio import validate, language_share_label
from render_svg_cards import Card, COPY, VIOLET, box, panel, wrap_badge, verify_svg, same_svg

NAME = "portfolio-language-share"


def render(data):
    validate(data)
    rows = sorted(((name, amount) for name, amount in data["language_bytes"] if amount > 0),
                  key=lambda item: (-item[1], item[0].casefold(), item[0]))
    total = sum(amount for _, amount in rows)
    scope = {
        "public-plus-private": "Public + authorized private language aggregates",
        "public-only-private-unavailable": "Public only; private aggregates unavailable",
        "public-only": "Public repositories only",
    }[data.get("language_scope", "public-only")]
    prepared = [(name, amount, wrap_badge(name, size=24, width=450, weight=500))
                for name, amount in rows]
    height = 130 + sum(62 + (len(lines) - 1) * 30 for _, _, lines in prepared) + (0 if rows else 55)
    desc = scope + ". " + "; ".join(f"{name} — {language_share_label(amount, total)}" for name, amount in rows)
    card = Card(680, height, "Language distribution", desc)
    card.parts.extend((
        panel(0, 0, 680, height, 16),
        card.text(28, 43, "Language distribution", 32, weight=700),
        card.text(28, 76, "GitHub Linguist · share of detected code bytes", 20, fill=COPY),
        card.text(28, 103, scope, 18, fill=COPY),
    ))
    y = 118
    for name, amount, lines in prepared:
        for index, line in enumerate(lines):
            card.parts.append(card.text(28, y + 24 + index * 30, line, 24, weight=500))
        card.parts.append(card.text(652, y + 24, language_share_label(amount, total), 24,
                                    weight=600, fill=VIOLET, anchor="end"))
        bar_y = y + 36 + (len(lines) - 1) * 30
        card.parts.append(box(28, bar_y, 624, 10, "#353145", radius=5))
        card.parts.append(box(28, bar_y, round(624 * amount / total, 4), 10, VIOLET, radius=5))
        y += 62 + (len(lines) - 1) * 30
    if not rows:
        card.parts.append(card.text(28, 153, "No detected language bytes available.", 22, fill=COPY))
    svg = card.svg(static=True)
    verify_svg(svg, NAME, static=True)
    return svg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    data = json.loads((args.output / "portfolio.json").read_text(encoding="utf-8"))
    target = args.output / (NAME + ".svg")
    expected = render(data)
    if args.verify:
        actual = target.read_text(encoding="utf-8")
        verify_svg(actual, NAME, static=True)
        if not same_svg(actual, expected):
            raise ValueError("Language share SVG does not match verified snapshot")
    else:
        target.write_text(expected, encoding="utf-8", newline="\n")
    print("PASS: language distribution derived from verified portfolio bytes")


if __name__ == "__main__":
    main()
