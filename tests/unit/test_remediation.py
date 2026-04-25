"""Remediation planner + markdown tests (SDLC-024 / SDLC-025)."""

from sdlc_assessor.remediation.markdown import render_remediation_markdown
from sdlc_assessor.remediation.planner import (
    ALLOWED_CHANGE_TYPES,
    ALLOWED_PHASES,
    build_remediation_plan,
)

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
    "effort",
    "expected_score_delta",
}


def _scored_with(findings: list[dict], maturity: str = "production") -> dict:
    return {
        "findings": findings,
        "scoring": {"effective_profile": {"maturity": maturity}},
        "hard_blockers": [],
    }


def test_remediation_plan_uses_required_task_schema() -> None:
    scored = _scored_with(
        [
            {
                "id": "F-0001",
                "subcategory": "probable_secrets",
                "severity": "high",
                "confidence": "medium",
                "statement": "Probable hardcoded secret detected.",
                "evidence": [{"path": "src/app.py"}],
                "score_impact": {"direction": "negative", "magnitude": 7},
            }
        ]
    )
    plan = build_remediation_plan(scored)
    assert plan["tasks"]
    assert REQUIRED_TASK_KEYS.issubset(plan["tasks"][0].keys())


def test_remediation_change_types_within_allowlist() -> None:
    scored = _scored_with(
        [
            {"id": "F-1", "subcategory": s, "severity": "high",
             "confidence": "high", "statement": "x", "evidence": [{"path": "p"}],
             "score_impact": {"direction": "negative", "magnitude": 7}}
            for s in (
                "probable_secrets", "missing_ci", "missing_readme", "missing_security_md",
                "committed_artifacts", "subprocess_shell_true", "exec_usage",
                "bare_except", "broad_except_exception", "any_usage", "type_ignore",
                "print_usage", "console_usage", "missing_strict_mode", "json_parse",
                "empty_catch", "large_files", "committed_credential",
            )
        ]
    )
    plan = build_remediation_plan(scored)
    for task in plan["tasks"]:
        assert task["change_type"] in ALLOWED_CHANGE_TYPES, task["change_type"]
        assert task["phase"] in ALLOWED_PHASES, task["phase"]
        assert task["verification_commands"], "verification_commands must be non-empty"


def test_remediation_groups_tasks_by_phase() -> None:
    scored = _scored_with(
        [
            {"id": "F-1", "subcategory": "probable_secrets", "severity": "high",
             "statement": "secret", "evidence": [{"path": "a"}], "confidence": "high",
             "score_impact": {"direction": "negative", "magnitude": 7}},
            {"id": "F-2", "subcategory": "missing_readme", "severity": "medium",
             "statement": "no readme", "evidence": [{"path": "b"}], "confidence": "high",
             "score_impact": {"direction": "negative", "magnitude": 4}},
        ]
    )
    plan = build_remediation_plan(scored)
    phases = [p["phase"] for p in plan["phases"]]
    assert "phase_1_security" in phases
    assert "phase_5_docs" in phases


def test_remediation_markdown_contains_sections() -> None:
    plan = {
        "summary": {
            "phase_count": 2,
            "task_count": 2,
            "blocker_count": 0,
            "expected_score_delta": 6.5,
            "per_phase": {
                "phase_1_security": {"task_count": 1, "expected_score_delta": 4.5},
                "phase_5_docs": {"task_count": 1, "expected_score_delta": 2.0},
            },
        },
        "tasks": [
            {
                "id": "R-001",
                "phase": "phase_1_security",
                "priority": "high",
                "linked_finding_ids": ["F-0001"],
                "target_paths": ["src/app.py"],
                "anchor_guidance": "Probable hardcoded secret detected.",
                "change_type": "tighten_validation",
                "rationale": "Address detected risk.",
                "implementation_steps": ["step a", "step b"],
                "test_requirements": ["test req"],
                "verification_commands": ["pytest -q"],
                "effort": "M",
                "expected_score_delta": 4.5,
            },
            {
                "id": "R-002",
                "phase": "phase_5_docs",
                "priority": "medium",
                "linked_finding_ids": ["F-0002"],
                "target_paths": ["README.md"],
                "anchor_guidance": "README missing.",
                "change_type": "update_docs",
                "rationale": "Documentation hygiene.",
                "implementation_steps": ["write README"],
                "test_requirements": ["wc -l README.md"],
                "verification_commands": ["test -f README.md"],
                "effort": "S",
                "expected_score_delta": 2.0,
            },
        ],
        "phases": [
            {"phase": "phase_1_security", "tasks": ["R-001"]},
            {"phase": "phase_5_docs", "tasks": ["R-002"]},
        ],
        "verification_checklist": ["Run tests"],
    }

    md = render_remediation_markdown(plan)
    assert "# Remediation Plan" in md
    assert "## Summary" in md
    assert "Phase 1 — Security" in md
    assert "Phase 5 — Documentation" in md
    assert "## Verification Checklist" in md


def test_remediation_markdown_renders_lists_not_python_repr() -> None:
    plan = build_remediation_plan(
        _scored_with(
            [
                {
                    "id": "F-1",
                    "subcategory": "probable_secrets",
                    "severity": "high",
                    "confidence": "medium",
                    "statement": "secret",
                    "evidence": [{"path": "src/app.py"}],
                    "score_impact": {"direction": "negative", "magnitude": 7},
                }
            ]
        )
    )
    md = render_remediation_markdown(plan)
    # Python list/dict repr should never leak through.
    assert "['" not in md
    assert "{'" not in md


def test_remediation_expected_score_delta_is_numeric_and_positive() -> None:
    plan = build_remediation_plan(
        _scored_with(
            [
                {
                    "id": "F-1",
                    "subcategory": "missing_ci",
                    "severity": "medium",
                    "confidence": "high",
                    "statement": "no ci",
                    "evidence": [{"path": ".github/workflows"}],
                    "score_impact": {"direction": "negative", "magnitude": 4},
                }
            ]
        )
    )
    delta = plan["tasks"][0]["expected_score_delta"]
    assert isinstance(delta, (int, float))
    assert delta > 0


def test_remediation_run_pipeline_end_to_end_against_secret_fixture(tmp_path) -> None:
    """Sanity check that the planner consumes a real scored payload."""
    from sdlc_assessor.classifier.engine import classify_repo
    from sdlc_assessor.collector.engine import collect_evidence
    from sdlc_assessor.core.io import write_json
    from sdlc_assessor.scorer.engine import score_evidence

    p = classify_repo("tests/fixtures/fixture_probable_secret")
    cp = tmp_path / "c.json"
    write_json(cp, p)
    e = collect_evidence("tests/fixtures/fixture_probable_secret", str(cp))
    s = score_evidence(e, "engineering_triage", "production", "service")
    plan = build_remediation_plan(s)
    md = render_remediation_markdown(plan)
    assert "phase_1_security" in {t["phase"] for t in plan["tasks"]} or "Phase 1" in md
    assert plan["summary"]["task_count"] == len(plan["tasks"])
