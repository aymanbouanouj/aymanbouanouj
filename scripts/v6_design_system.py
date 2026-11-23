"""Shared V6 reference-based design contract.

Measurements are from the supplied 810 x 1393 mockup (content x=10..790).
Keep SVG and PNG renders visually consistent while preserving their independent
GitHub links and the verified, automatically refreshed data collectors.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType

REFERENCE_CONTENT_WIDTH = 780
SVG_PANEL_WIDTH = 1000

# Bands include a heading where the reference has one; all values measured
# in reference-image pixels, not the GitHub document viewport.
REFERENCE_BANDS = MappingProxyType({
    "hero": (53, 222),
    "metrics": (232, 307),
    "calendar": (317, 465),
    "languages": (478, 595),
    "frameworks": (608, 687),
    "projects": (696, 950),
    "opensource": (961, 1078),
    "building": (1086, 1151),
    "pinned": (1157, 1370),
})


@dataclass(frozen=True)
class VisualTokens:
    background: str = "#0a0d18"
    card: str = "#151a2b"
    border: str = "#42415d"
    accent: str = "#b46aff"
    text: str = "#f6f7ff"
    muted: str = "#bdc2d5"
    gradient_dark: str = "#17162c"
    gradient_end: str = "#101827"
    image_pending: str = "#c8a2ff"
    panel_radius: int = 18
    card_radius: int = 14
    font_stack: str = "Arial,Helvetica,sans-serif"
    # Project card dimension ratio approximates reference cards:
    # 245 x 218 effective image pixels at full 780px content width.
    project_card_width: int = 640
    project_card_height: int = 560

    def validate(self) -> None:
        for field in (
            "background", "card", "border", "accent", "text", "muted",
            "gradient_dark", "gradient_end", "image_pending",
        ):
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", getattr(self, field)):
                raise ValueError("Invalid V6 palette field: " + field)
        if not 8 <= self.card_radius <= self.panel_radius <= 24:
            raise ValueError("Invalid V6 corner-radius hierarchy")
        ratio = self.project_card_width / self.project_card_height
        reference_card_ratio = 245 / 218
        if abs(ratio - reference_card_ratio) > 0.10:
            raise ValueError("Project card does not preserve reference aspect ratio")


TOKENS = VisualTokens()
TOKENS.validate()


def reference_panel_height(section: str, width: int = SVG_PANEL_WIDTH) -> int:
    """Scaled target total height for a complete reference band."""
    if type(width) is not int or not 100 <= width <= 5000:
        raise ValueError("Invalid width")
    if section not in REFERENCE_BANDS:
        raise KeyError(section)
    start, end = REFERENCE_BANDS[section]
    return round((end - start) / REFERENCE_CONTENT_WIDTH * width)


def validate_reference_bands() -> None:
    prior_end = -1
    for name, (top, bottom) in REFERENCE_BANDS.items():
        if not top > prior_end or not top < bottom:
            raise ValueError("Overlapping or inverted reference band: " + name)
        prior_end = bottom


validate_reference_bands()
