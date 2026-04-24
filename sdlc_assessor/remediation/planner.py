"""Phase 6 remediation planner."""

from __future__ import annotations


def _task_from_finding(index: int, finding: dict) -> dict:
    path = "unknown"
    evidence = finding.get("evidence", [])
    if evidence and isinstance(evidence[0], dict):
        path = evidence[0].get("path", "unknown")

    return {
        "id": f"R-{index:03d}",
        "phase": "phase_1_safety",
        "priority": "high" if finding.get("severity") in {"high", "critical"} else "medium",
        "linked_finding_ids": [finding.get("id", f"F-{index:04d}")],
        "target_paths": [path],
        "anchor_guidance": finding.get("statement", "Refer to finding context."),
        "change_type": "modify_block",
        "rationale": finding.get("statement", "Address detected risk."),
        "implementation_steps": [
            "Identify the unsafe or missing control path.",
            "Apply the minimal targeted code/config change.",
            "Confirm behavior remains correct.",
        ],
        "test_requirements": [
            "Add or update a test that reproduces the finding before the fix.",
            "Assert the finding condition is resolved after the fix.",
        ],
        "verification_commands": ["pytest -q"],
    }


def build_remediation_plan(scored: dict) -> dict:
    findings = scored.get("findings", [])
    tasks = [_task_from_finding(i + 1, f) for i, f in enumerate(findings)]

    blockers = scored.get("hard_blockers", [])
    summary = {
        "phase_count": 1,
        "task_count": len(tasks),
        "blocker_count": len(blockers),
        "expected_score_delta": "likely +5 to +8",
    }

    return {
        "summary": summary,
        "tasks": tasks,
        "verification_checklist": [
            "Run tests",
            "Run lint if configured",
            "Run focused verification commands per task",
        ],
    }
