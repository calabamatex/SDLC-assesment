"""Category radar / spider chart (SDLC-072)."""

from __future__ import annotations

import math
from collections.abc import Sequence

from sdlc_assessor.renderer.charts._palette import (
    ACCENT,
    GRID,
    INK,
    MUTED,
    font,
)


def _polar_to_xy(
    cx: float, cy: float, r: float, angle_rad: float
) -> tuple[float, float]:
    return cx + r * math.cos(angle_rad), cy + r * math.sin(angle_rad)


def category_radar(
    *,
    axes: Sequence[tuple[str, float, float]],
    baseline: Sequence[float] | None = None,
    width: int = 380,
    height: int = 340,
    title: str = "Category scores vs archetype baseline",
) -> str:
    """Spider/radar chart for category scores.

    ``axes``: ordered iterable of ``(label, score, max_score)`` tuples.
    Scores are normalised to ``score / max_score`` for plotting; max=0
    axes draw at the centre.

    ``baseline``: optional same-length iterable of ``[0..1]`` ratios
    representing the archetype-typical score (e.g. "median library
    repo at production maturity hits these category ratios"). Drawn as
    a subtle outline behind the actual polygon.
    """
    axes = list(axes)
    n = len(axes)
    if n < 3:
        # Radar needs at least 3 axes to be visually meaningful.
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}" role="img" aria-label="{title}">'
            f'<text x="{width / 2}" y="{height / 2}" {font(12, color=MUTED)} '
            f'text-anchor="middle">Need ≥3 axes for a radar chart.</text>'
            "</svg>"
        )

    cx = width / 2
    cy = height / 2 + 6
    r_outer = min(width, height) * 0.36

    # Compute axis end-points and normalised score points.
    angles = [(-math.pi / 2) + (2 * math.pi * i / n) for i in range(n)]

    score_points: list[tuple[float, float]] = []
    baseline_points: list[tuple[float, float]] = []
    for i, (_, score, maxv) in enumerate(axes):
        ratio = (score / maxv) if maxv > 0 else 0.0
        ratio = max(0.0, min(1.0, ratio))
        score_points.append(_polar_to_xy(cx, cy, ratio * r_outer, angles[i]))
        if baseline is not None and i < len(baseline):
            base_ratio = max(0.0, min(1.0, float(baseline[i])))
            baseline_points.append(
                _polar_to_xy(cx, cy, base_ratio * r_outer, angles[i])
            )

    # Concentric grid rings at 25/50/75/100.
    grid_svg: list[str] = []
    for ring in (0.25, 0.50, 0.75, 1.0):
        ring_pts = [
            _polar_to_xy(cx, cy, ring * r_outer, ang) for ang in angles
        ]
        d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in ring_pts) + " Z"
        grid_svg.append(
            f'<path d="{d}" fill="none" stroke="{GRID}" stroke-width="1" '
            f'stroke-dasharray="{1 if ring < 1.0 else 0} {2 if ring < 1.0 else 0}" />'
        )

    # Spokes from centre to each outer-ring tip.
    spoke_svg: list[str] = []
    for ang in angles:
        ex, ey = _polar_to_xy(cx, cy, r_outer, ang)
        spoke_svg.append(
            f'<line x1="{cx}" y1="{cy}" x2="{ex:.1f}" y2="{ey:.1f}" '
            f'stroke="{GRID}" stroke-width="1" />'
        )

    # Labels at each axis tip.
    label_svg: list[str] = []
    for i, (label, score, maxv) in enumerate(axes):
        lx, ly = _polar_to_xy(cx, cy, r_outer + 14, angles[i])
        # Anchor label sensibly relative to position around the circle.
        ang_deg = (math.degrees(angles[i]) % 360 + 360) % 360
        if 60 <= ang_deg <= 120 or 240 <= ang_deg <= 300:
            anchor = "middle"
        elif ang_deg < 90 or ang_deg > 270:
            anchor = "start"
        else:
            anchor = "end"
        score_text = f"{int(round(score))}/{int(round(maxv))}" if maxv > 0 else "n/a"
        label_svg.append(
            f'<text x="{lx:.1f}" y="{ly - 4:.1f}" {font(10, weight=600, color=INK)} '
            f'text-anchor="{anchor}">{label}</text>'
        )
        label_svg.append(
            f'<text x="{lx:.1f}" y="{ly + 8:.1f}" {font(9, color=MUTED)} '
            f'text-anchor="{anchor}">{score_text}</text>'
        )

    # Baseline polygon (drawn behind the score polygon).
    baseline_d = ""
    if baseline_points:
        baseline_d = (
            "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in baseline_points) + " Z"
        )

    # Score polygon.
    score_d = (
        "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in score_points) + " Z"
    )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" aria-label="{title}">',
        f'<title>{title}</title>',
        "".join(grid_svg),
        "".join(spoke_svg),
    ]
    if baseline_d:
        parts.append(
            f'<path d="{baseline_d}" fill="{GRID}" fill-opacity="0.45" '
            f'stroke="{MUTED}" stroke-width="1.2" stroke-dasharray="3 3" />'
        )
    parts.append(
        f'<path d="{score_d}" fill="{ACCENT}" fill-opacity="0.18" '
        f'stroke="{ACCENT}" stroke-width="2" />'
    )
    # Score-point dots for sharper legibility.
    for sx, sy in score_points:
        parts.append(
            f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="3" '
            f'fill="{ACCENT}" />'
        )
    parts.append("".join(label_svg))
    parts.append("</svg>")
    return "".join(parts)


__all__ = ["category_radar"]
