"""Remediation planner."""

from __future__ import annotations


def _task_from_finding(index: int, finding: dict) -> dict:
    evidence = finding.get("evidence", [])
    path = "unknown"
    if evidence and isinstance(evidence[0], dict):
        path = evidence[0].get("path", "unknown")

    severity = finding.get("severity", "medium")
    priority = "high" if severity in {"critical", "high"} else "medium"

    verification = ["pytest -q"]
    if path.endswith((".ts", ".tsx", ".js", ".jsx")):
        verification.append("npm test || true")
    if path.endswith(".py"):
        verification.append("python -m pytest -q || true")

    return {
        "id": f"R-{index:03d}",
        "phase": "phase_1_safety" if priority == "high" else "phase_2_quality",
        "priority": priority,
        "linked_finding_ids": [finding.get("id", f"F-{index:04d}")],
        "target_paths": [path],
        "anchor_guidance": f"Locate code matching: {finding.get('statement', 'finding statement')}",
        "change_type": "replace_unsafe_pattern" if severity in {"critical", "high"} else "modify_block",
        "rationale": finding.get("statement", "Address detected risk."),
        "implementation_steps": [
            f"Open `{path}` and locate the risky pattern referenced by finding {finding.get('id', 'unknown')}",
            "Replace unsafe behavior with validated/safe default behavior.",
            "Add regression coverage to prevent recurrence.",
        ],
        "test_requirements": [
            "Create failing test that reproduces current issue.",
            "Update assertions to prove remediation closes the issue.",
        ],
        "verification_commands": verification,
    }


def build_remediation_plan(scored: dict) -> dict:
    findings = scored.get("findings", [])
    tasks = [_task_from_finding(i + 1, f) for i, f in enumerate(findings)]

    blockers = scored.get("hard_blockers", [])
    return {
        "summary": {
            "phase_count": 2 if tasks else 1,
            "task_count": len(tasks),
            "blocker_count": len(blockers),
            "expected_score_delta": "likely +5 to +8",
        },
        "tasks": tasks,
        "verification_checklist": [
            "Run unit and integration tests",
            "Run lint/static checks if configured",
            "Run task verification commands",
            "Regenerate report and confirm blocker status",
        ],
    }
