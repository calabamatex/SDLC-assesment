"""Gap-analysis builder (0.11.0 depth pass).

Computes ``gap_to_pass`` / ``gap_to_distinction`` against the persona's
real thresholds, plus the remediation phases that close the gap with
their projected lifts (from ``planner.py``'s arithmetic, marked as
projections — not historical outcomes).

No invented values. The phase ordering and projected lifts are read
from ``scored.remediation_plan.tasks[].expected_score_delta`` and
``scored.remediation_plan.tasks[].phase`` exactly as the planner emitted
them.
"""

from __future__ import annotations

from sdlc_assessor.renderer.deliverables.base import GapAnalysis, ScoreDecomposition

_PHASE_ORDER = [
    "phase_1_security",
    "phase_2_contracts",
    "phase_3_tests",
    "phase_4_ci",
    "phase_5_docs",
]


def build_gap_analysis(scored: dict, decomposition: ScoreDecomposition) -> GapAnalysis:
    overall = decomposition.overall
    pass_threshold = decomposition.pass_threshold
    distinction_threshold = decomposition.distinction_threshold

    plan = scored.get("remediation_plan") or scored.get("remediation") or {}
    tasks = plan.get("tasks") or []

    deltas: dict[str, float] = {}
    counts: dict[str, int] = {}
    for t in tasks:
        phase = t.get("phase") or "phase_other"
        deltas[phase] = deltas.get(phase, 0.0) + float(t.get("expected_score_delta") or 0.0)
        counts[phase] = counts.get(phase, 0) + 1

    closing_phases: list[dict] = []
    running = float(overall)
    for phase in _PHASE_ORDER + sorted(p for p in deltas if p not in _PHASE_ORDER):
        if phase not in deltas:
            continue
        lift = deltas[phase]
        if lift <= 0:
            continue
        after = min(100.0, running + lift)
        closing_phases.append(
            {
                "phase": phase,
                "task_count": counts.get(phase, 0),
                "projected_lift": round(lift, 2),
                "before": round(running, 2),
                "after": round(after, 2),
                "clears": after >= pass_threshold,
            }
        )
        running = after

    minimum_phases_to_pass: list[str] = []
    if overall < pass_threshold:
        running = float(overall)
        for entry in closing_phases:
            minimum_phases_to_pass.append(entry["phase"])
            running = entry["after"]
            if running >= pass_threshold:
                break

    return GapAnalysis(
        gap_to_pass=max(0, pass_threshold - overall),
        gap_to_distinction=max(0, distinction_threshold - overall),
        closing_phases=closing_phases,
        minimum_phases_to_pass=minimum_phases_to_pass,
        on_call_delta_if_unfixed="",  # populated by the engineering builder
    )


__all__ = ["build_gap_analysis"]
