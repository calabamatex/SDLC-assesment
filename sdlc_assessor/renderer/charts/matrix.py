"""2×2 matrix charts (SDLC-072).

Two flavours, both built on the same generic 2×2 plotter:

- :func:`risk_matrix` — likelihood × impact, with risks plotted as dots.
- :func:`effort_impact_matrix` — engineering effort × score impact for
  remediation tasks.
"""

from __future__ import annotations

import html as _html
from collections.abc import Sequence
from dataclasses import dataclass

from sdlc_assessor.renderer.charts._palette import (
    ACCENT,
    BG_ALT,
    GRID,
    INK,
    MUTED,
    SEVERITY_FILL,
    SEVERITY_STROKE,
    font,
)


@dataclass(slots=True)
class MatrixPoint:
    label: str
    x: float  # 0..1 horizontal axis
    y: float  # 0..1 vertical axis
    severity: str | None = None  # critical / high / medium / low / info
    note: str | None = None


def _quadrant_label_box(
    x: float, y: float, w: float, h: float, label: str, fill: str = BG_ALT
) -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" '
        f'stroke="{GRID}" stroke-width="1" />'
        f'<text x="{x + 8}" y="{y + 14}" {font(9, weight=600, color=MUTED)}>'
        f'{_html.escape(label)}</text>'
    )


def _plot_matrix(
    *,
    points: Sequence[MatrixPoint],
    x_label: str,
    y_label: str,
    quadrant_labels: tuple[str, str, str, str],
    width: int,
    height: int,
    title: str,
) -> str:
    """Generic 2×2 plotter.

    ``quadrant_labels`` ordering: (top-left, top-right, bottom-left, bottom-right).
    ``y`` is interpreted bottom-up (1.0 = top of grid).
    """
    margin_left = 80
    margin_top = 30
    margin_bottom = 40
    margin_right = 30
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    half_w = plot_w / 2
    half_h = plot_h / 2

    # Quadrant background tints.
    tl = _quadrant_label_box(margin_left, margin_top, half_w, half_h, quadrant_labels[0])
    tr = _quadrant_label_box(margin_left + half_w, margin_top, half_w, half_h, quadrant_labels[1], fill="#fff8d6")
    bl = _quadrant_label_box(margin_left, margin_top + half_h, half_w, half_h, quadrant_labels[2])
    br = _quadrant_label_box(margin_left + half_w, margin_top + half_h, half_w, half_h, quadrant_labels[3], fill="#fbe9e9")

    # Axis labels.
    axis_x_label = (
        f'<text x="{margin_left + plot_w / 2}" y="{height - 6}" '
        f'{font(11, weight=600, color=INK)} text-anchor="middle">{_html.escape(x_label)}</text>'
    )
    axis_y_label = (
        f'<text x="{16}" y="{margin_top + plot_h / 2}" '
        f'{font(11, weight=600, color=INK)} '
        f'text-anchor="middle" '
        f'transform="rotate(-90 16 {margin_top + plot_h / 2})">{_html.escape(y_label)}</text>'
    )

    # Tick marks: low / high on each axis.
    tick_svg = [
        f'<text x="{margin_left}" y="{margin_top + plot_h + 14}" {font(9, color=MUTED)} '
        'text-anchor="start">low</text>',
        f'<text x="{margin_left + plot_w}" y="{margin_top + plot_h + 14}" {font(9, color=MUTED)} '
        'text-anchor="end">high</text>',
        f'<text x="{margin_left - 6}" y="{margin_top + plot_h + 4}" {font(9, color=MUTED)} '
        'text-anchor="end">low</text>',
        f'<text x="{margin_left - 6}" y="{margin_top + 4}" {font(9, color=MUTED)} '
        'text-anchor="end">high</text>',
    ]

    # Plot points with jitter so overlapping coords don't fully overlap visually.
    point_svg: list[str] = []
    seen: dict[tuple[int, int], int] = {}
    for p in points:
        ux = max(0.0, min(1.0, p.x))
        uy = max(0.0, min(1.0, p.y))
        px = margin_left + ux * plot_w
        py = margin_top + (1.0 - uy) * plot_h
        bucket = (int(px / 14), int(py / 14))
        offset = seen.get(bucket, 0)
        seen[bucket] = offset + 1
        # Spiral-out jitter so subsequent overlaps don't pile up.
        if offset > 0:
            angle = 0.7 * offset
            radius = 6 + 3 * offset
            import math as _math
            px += radius * _math.cos(angle)
            py += radius * _math.sin(angle)

        sev = (p.severity or "info").lower()
        fill = SEVERITY_FILL.get(sev, SEVERITY_FILL["info"])
        stroke = SEVERITY_STROKE.get(sev, SEVERITY_STROKE["info"])
        tooltip = _html.escape(f"{p.label} — {p.note}" if p.note else p.label)
        point_svg.append(
            f'<g><title>{tooltip}</title>'
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="6" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="1.5" />'
            f'<text x="{px + 9:.1f}" y="{py + 3:.1f}" {font(9, color=INK)}>'
            f'{_html.escape(p.label)}</text>'
            f'</g>'
        )

    return "".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}" role="img" aria-label="{title}">',
            f'<title>{title}</title>',
            tl,
            tr,
            bl,
            br,
            *tick_svg,
            axis_x_label,
            axis_y_label,
            *point_svg,
            "</svg>",
        ]
    )


def risk_matrix(
    *,
    risks: Sequence[MatrixPoint],
    width: int = 480,
    height: int = 360,
    title: str = "Risk matrix — likelihood × impact",
    x_label: str = "Likelihood",
    y_label: str = "Impact",
    quadrant_labels: tuple[str, str, str, str] = (
        "Low likelihood · High impact",
        "High likelihood · High impact",
        "Low likelihood · Low impact",
        "High likelihood · Low impact",
    ),
) -> str:
    """Plot risks on an axis × axis grid.

    Axis and quadrant labels are caller-supplied so persona deliverables
    can frame the same data in their reader's voice (e.g., a VC sees
    "Likelihood we encounter in diligence" / "Downside to thesis"
    instead of the generic "Likelihood / Impact").
    """
    return _plot_matrix(
        points=risks,
        x_label=x_label,
        y_label=y_label,
        quadrant_labels=quadrant_labels,
        width=width,
        height=height,
        title=title,
    )


def effort_impact_matrix(
    *,
    tasks: Sequence[MatrixPoint],
    width: int = 480,
    height: int = 360,
    title: str = "Remediation tasks — effort × score impact",
    x_label: str = "Effort",
    y_label: str = "Score impact",
    quadrant_labels: tuple[str, str, str, str] = (
        "Low effort · High impact (DO FIRST)",
        "High effort · High impact",
        "Low effort · Low impact",
        "High effort · Low impact (DEFER)",
    ),
) -> str:
    """Plot tasks on a caller-framed effort × score-lift grid.

    Default labels match the engineering-triage frame; persona builders
    override to surface the right vocabulary (e.g., for an investor:
    "Founder time to address" vs "Thesis credibility lift").
    """
    return _plot_matrix(
        points=tasks,
        x_label=x_label,
        y_label=y_label,
        quadrant_labels=quadrant_labels,
        width=width,
        height=height,
        title=title,
    )


__all__ = ["MatrixPoint", "effort_impact_matrix", "risk_matrix"]
