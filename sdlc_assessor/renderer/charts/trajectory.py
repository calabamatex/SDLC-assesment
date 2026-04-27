"""Score-lift trajectory chart (SDLC-072).

A horizontal stacked-bar showing current score → projected score after
each phase of remediation, so a reviewer can see exactly which phase
buys which lift.
"""

from __future__ import annotations

import html as _html
from collections.abc import Sequence
from dataclasses import dataclass

from sdlc_assessor.renderer.charts._palette import (
    BAND_FILL,
    GRID,
    INK,
    MUTED,
    band_for,
    font,
)


@dataclass(slots=True)
class PhaseLift:
    """One step in the trajectory."""

    label: str
    delta: float


def score_lift_trajectory(
    *,
    current_score: float,
    phases: Sequence[PhaseLift],
    width: int = 540,
    height: int = 260,
    title: str = "Projected score lift by phase",
) -> str:
    """Render a stacked-bar trajectory.

    Each phase contributes ``delta`` points stacked atop the running
    cumulative score. Final cap at 100.
    """
    margin_left = 90
    margin_right = 30
    margin_top = 24
    margin_bottom = 70
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    current = max(0.0, min(100.0, float(current_score)))

    # Compute running total per phase, capped at 100.
    rows: list[tuple[str, float, float, float]] = []
    running = current
    for phase in phases:
        before = running
        after = max(0.0, min(100.0, running + float(phase.delta)))
        rows.append((phase.label, before, after, after - before))
        running = after

    # The bars all share a common 0..100 horizontal scale.
    def _x(score: float) -> float:
        return margin_left + (score / 100.0) * plot_w

    # Y positions for the bars.
    n_bars = 1 + len(rows)  # current + N phases
    bar_h = max(14.0, min(32.0, plot_h / max(n_bars, 1) - 6))
    y_step = bar_h + 8

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" aria-label="{title}">'
    )
    parts.append(f"<title>{title}</title>")

    # Vertical gridlines at 25/50/75/100.
    for v in (25, 50, 75, 100):
        gx = _x(v)
        parts.append(
            f'<line x1="{gx:.1f}" y1="{margin_top - 4}" x2="{gx:.1f}" '
            f'y2="{margin_top + plot_h:.1f}" stroke="{GRID}" stroke-width="1" '
            'stroke-dasharray="2 3" />'
        )
        parts.append(
            f'<text x="{gx:.1f}" y="{margin_top + plot_h + 12:.1f}" {font(9, color=MUTED)} '
            f'text-anchor="middle">{v}</text>'
        )

    # Current score bar.
    y: float = float(margin_top)
    band = band_for(current)
    parts.append(
        f'<rect x="{margin_left}" y="{y}" '
        f'width="{(current / 100.0) * plot_w:.1f}" height="{bar_h}" '
        f'fill="{BAND_FILL[band]}" stroke="{GRID}" stroke-width="1" rx="2" />'
    )
    parts.append(
        f'<text x="{margin_left - 6}" y="{y + bar_h / 2 + 3:.1f}" '
        f'{font(10, weight=600, color=INK)} text-anchor="end">Current</text>'
    )
    parts.append(
        f'<text x="{_x(current) + 6:.1f}" y="{y + bar_h / 2 + 3:.1f}" '
        f'{font(10, color=INK)}>{int(round(current))}</text>'
    )

    # Phase bars: cumulative track + delta segment highlighted.
    for label, before, after, delta in rows:
        y += y_step
        # Track up to "before" (light fill).
        track_w = (before / 100.0) * plot_w
        parts.append(
            f'<rect x="{margin_left}" y="{y}" width="{track_w:.1f}" '
            f'height="{bar_h}" fill="{GRID}" rx="2" />'
        )
        # Delta segment.
        delta_w = (delta / 100.0) * plot_w
        if delta_w > 0:
            band_after = band_for(after)
            parts.append(
                f'<rect x="{_x(before):.1f}" y="{y}" width="{delta_w:.1f}" '
                f'height="{bar_h}" fill="{BAND_FILL[band_after]}" '
                f'stroke="{GRID}" stroke-width="1" rx="2" />'
            )
        # Label on left.
        parts.append(
            f'<text x="{margin_left - 6}" y="{y + bar_h / 2 + 3:.1f}" '
            f'{font(10, weight=500, color=INK)} text-anchor="end">'
            f'{_html.escape(label)}</text>'
        )
        # End-point score text.
        parts.append(
            f'<text x="{_x(after) + 6:.1f}" y="{y + bar_h / 2 + 3:.1f}" '
            f'{font(10, color=INK)}>{int(round(after))} (+{delta:.1f})</text>'
        )

    # x-axis label.
    parts.append(
        f'<text x="{margin_left + plot_w / 2}" y="{height - 12}" '
        f'{font(11, weight=600, color=INK)} text-anchor="middle">'
        "Projected score (0–100)</text>"
    )

    parts.append("</svg>")
    return "".join(parts)


__all__ = ["PhaseLift", "score_lift_trajectory"]
