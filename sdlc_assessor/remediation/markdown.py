"""Render the remediation plan as Markdown (SDLC-025).

List-valued task fields are rendered as nested Markdown lists so the output
no longer leaks Python ``repr`` of lists / dicts into the report. Tasks are
grouped by phase under ``## Phase X — <name>`` headers.
"""

from __future__ import annotations

from collections import defaultdict

PHASE_TITLES = {
    "phase_1_security": "Phase 1 — Security",
    "phase_2_contracts": "Phase 2 — Contracts & validation",
    "phase_3_tests": "Phase 3 — Tests",
    "phase_4_ci": "Phase 4 — CI & release hygiene",
    "phase_5_docs": "Phase 5 — Documentation",
}

LIST_KEYS = (
    "linked_finding_ids",
    "target_paths",
    "implementation_steps",
    "test_requirements",
    "verification_commands",
)

PROSE_KEYS = ("anchor_guidance", "rationale")

SCALAR_KEYS = ("phase", "priority", "change_type", "effort", "expected_score_delta")


def _render_task(task: dict) -> list[str]:
    out: list[str] = []
    title = f"### {task.get('id', 'R-???')} — {task.get('change_type', '?')}"
    out.append(title)

    metadata = " · ".join(
        f"**{key.replace('_', ' ')}**: `{task.get(key, 'n/a')}`"
        for key in SCALAR_KEYS
    )
    out.append(metadata)
    out.append("")

    for prose_key in PROSE_KEYS:
        value = task.get(prose_key)
        if value:
            out.append(f"**{prose_key.replace('_', ' ').title()}**")
            out.append("")
            out.append(str(value))
            out.append("")

    for list_key in LIST_KEYS:
        items = task.get(list_key) or []
        if not items:
            continue
        out.append(f"**{list_key.replace('_', ' ').title()}**")
        for item in items:
            out.append(f"- {item}")
        out.append("")
    return out


def render_remediation_markdown(plan: dict) -> str:
    lines: list[str] = ["# Remediation Plan", ""]

    summary = plan.get("summary", {})
    lines.append("## Summary")
    lines.append(f"- Phase count: {summary.get('phase_count', 0)}")
    lines.append(f"- Task count: {summary.get('task_count', 0)}")
    lines.append(f"- Blocker count: {summary.get('blocker_count', 0)}")
    lines.append(f"- Expected total score delta: +{summary.get('expected_score_delta', 0)}")
    per_phase = summary.get("per_phase") or {}
    if per_phase:
        lines.append("")
        lines.append("Per-phase breakdown:")
        lines.append("")
        lines.append("| Phase | Tasks | Expected delta |")
        lines.append("|---|---:|---:|")
        for phase, info in per_phase.items():
            tasks_n = info.get("task_count", 0)
            delta = info.get("expected_score_delta", 0)
            lines.append(f"| {PHASE_TITLES.get(phase, phase)} | {tasks_n} | +{delta} |")
    lines.append("")

    by_phase: dict[str, list[dict]] = defaultdict(list)
    for task in plan.get("tasks", []):
        by_phase[task.get("phase", "phase_2_contracts")].append(task)

    for phase in [
        "phase_1_security",
        "phase_2_contracts",
        "phase_3_tests",
        "phase_4_ci",
        "phase_5_docs",
    ]:
        tasks = by_phase.get(phase, [])
        if not tasks:
            continue
        lines.append(f"## {PHASE_TITLES.get(phase, phase)}")
        lines.append("")
        for task in tasks:
            lines.extend(_render_task(task))

    lines.append("## Verification Checklist")
    for item in plan.get("verification_checklist", []) or []:
        lines.append(f"- {item}")
    lines.append("")

    return "\n".join(lines) + "\n"


__all__ = ["render_remediation_markdown"]
