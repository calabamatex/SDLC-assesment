from sdlc_assessor.remediation.markdown import render_remediation_markdown
from sdlc_assessor.remediation.planner import build_remediation_plan


REQUIRED_TASK_KEYS = {
    "id",
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
}


def test_remediation_plan_uses_required_task_schema() -> None:
    scored = {
        "findings": [
            {
                "id": "F-0001",
                "severity": "high",
                "statement": "Probable hardcoded secret detected.",
                "evidence": [{"path": "src/app.py"}],
            }
        ],
        "hard_blockers": [{"finding_id": "F-0001"}],
    }
    plan = build_remediation_plan(scored)
    assert plan["tasks"]
    assert REQUIRED_TASK_KEYS.issubset(plan["tasks"][0].keys())


def test_remediation_markdown_contains_sections() -> None:
    plan = {
        "summary": {"phase_count": 1, "task_count": 1, "blocker_count": 0, "expected_score_delta": "likely +5 to +8"},
        "tasks": [
            {
                "id": "R-001",
                "phase": "phase_1_safety",
                "priority": "high",
                "linked_finding_ids": ["F-0001"],
                "target_paths": ["src/app.py"],
                "anchor_guidance": "Probable hardcoded secret detected.",
                "change_type": "modify_block",
                "rationale": "Address detected risk.",
                "implementation_steps": ["step"],
                "test_requirements": ["test"],
                "verification_commands": ["pytest -q"],
            }
        ],
        "verification_checklist": ["Run tests"],
    }

    md = render_remediation_markdown(plan)
    assert "# Remediation Plan" in md
    assert "## Tasks" in md
    assert "## Verification Checklist" in md
