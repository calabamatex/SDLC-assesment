"""Comparison engine + Markdown renderer for `sdlc compare` (SDLC-061..063)."""

from __future__ import annotations

from sdlc_assessor.compare.engine import (
    CategoryDelta,
    Comparison,
    FindingFamilyDelta,
    build_comparison,
    comparison_to_dict,
)
from sdlc_assessor.compare.markdown import render_comparison_markdown

__all__ = [
    "CategoryDelta",
    "Comparison",
    "FindingFamilyDelta",
    "build_comparison",
    "comparison_to_dict",
    "render_comparison_markdown",
]
