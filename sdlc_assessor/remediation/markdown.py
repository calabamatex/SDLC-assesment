"""Render remediation plan as Markdown."""

from __future__ import annotations


def render_remediation_markdown(plan: dict) -> str:
    lines: list[str] = ["# Remediation Plan", ""]

    summary = plan.get("summary", {})
    lines.append("## Summary")
    lines.append(f"- Phase count: {summary.get('phase_count', 0)}")
    lines.append(f"- Task count: {summary.get('task_count', 0)}")
    lines.append(f"- Blocker count: {summary.get('blocker_count', 0)}")
    lines.append(f"- Expected score delta: {summary.get('expected_score_delta', 'n/a')}")
    lines.append("")

    lines.append("## Tasks")
    for task in plan.get("tasks", []):
        lines.append(f"### {task.get('id', 'R-???')}")
        for key in [
            "phase",
            "priority",
            "linked_finding_ids",
            "target_paths",
            "anchor_guidance",
            "change_type",
            "rationale",
            "implementation_steps",
            "test_requirements",
            "verification_commands",
        ]:
            lines.append(f"- {key}: {task.get(key)}")
        lines.append("")

    lines.append("## Verification Checklist")
    for item in plan.get("verification_checklist", []):
        lines.append(f"- {item}")

    return "\n".join(lines) + "\n"
