"""Persona dispatch + narrative-block builder tests (SDLC-068)."""

from __future__ import annotations

import pytest

from sdlc_assessor.normalizer.findings import (
    classify_path,
    fixture_findings,
    is_fixture_finding,
    normalize_findings,
    production_findings,
)
from sdlc_assessor.renderer import narrative_blocks  # noqa: F401  (registers builders)
from sdlc_assessor.renderer.persona import (
    block_to_dict,
    narrate_for_persona,
    registered_keys,
)

# ---------------------------------------------------------------------------
# Path-class tagging (SDLC-067)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("tests/fixtures/fixture_x/main.py", "test_fixture"),
        ("./tests/fixtures/foo/bar.py", "test_fixture"),
        ("examples/quickstart.py", "example"),
        ("samples/run.py", "example"),
        ("vendor/leftpad/index.js", "vendor"),
        ("third_party/lib.go", "vendor"),
        ("docs/architecture.md", "docs"),
        ("benchmark/run.py", "benchmark"),
        ("sdlc_assessor/cli.py", None),
        ("README.md", None),
        (None, None),
        ("", None),
    ],
)
def test_classify_path(path: str | None, expected: str | None) -> None:
    assert classify_path(path) == expected


def test_normalize_findings_tags_fixture_paths() -> None:
    raw = [
        {
            "category": "x",
            "subcategory": "y",
            "severity": "low",
            "statement": "z",
            "evidence": [{"path": "tests/fixtures/fixture_x/main.py", "line_start": 1}],
            "confidence": "high",
        },
        {
            "category": "x",
            "subcategory": "z",
            "severity": "low",
            "statement": "w",
            "evidence": [{"path": "sdlc_assessor/cli.py", "line_start": 5}],
            "confidence": "high",
        },
    ]
    out = normalize_findings(raw)
    assert any(t == "source:test_fixture" for t in (out[0].get("tags") or []))
    assert "source:test_fixture" not in (out[1].get("tags") or [])


def test_is_fixture_and_partition_helpers() -> None:
    findings = [
        {"tags": ["source:test_fixture"]},
        {"tags": []},
        {"tags": ["source:vendor"]},
        {},  # no tags → production
    ]
    assert is_fixture_finding(findings[0]) is True
    assert is_fixture_finding(findings[1]) is False
    assert is_fixture_finding(findings[2]) is True
    assert is_fixture_finding(findings[3]) is False
    assert len(production_findings(findings)) == 2
    assert len(fixture_findings(findings)) == 2


# ---------------------------------------------------------------------------
# Persona dispatch (SDLC-068)
# ---------------------------------------------------------------------------


def test_registered_keys_covers_all_shipped_emphasis_terms() -> None:
    keys = set(registered_keys())
    expected = {
        # acquisition_diligence
        "integration_risk",
        "maintenance_burden",
        "release_hygiene",
        "dependency_concentration",
        "knowledge_transfer_risk",
        # vc_diligence
        "credibility",
        "technical_moat_support",
        "execution_maturity",
        "risk_concentration",
        "overclaim_detection",
        # engineering_triage
        "technical_debt",
        "failure_modes",
        "code_level_evidence",
        "implementation_priority",
        # remediation_agent
        "task_order",
        "verification",
        "patch_safety",
        "expected_score_lift",
    }
    missing = expected - keys
    assert not missing, f"missing builders: {missing}"


def test_narrate_for_persona_builds_blocks_for_each_emphasis_term() -> None:
    scored = _minimal_scored()
    profile = {"narrative_emphasis": ["integration_risk", "maintenance_burden"]}
    blocks = narrate_for_persona(scored, profile)
    assert len(blocks) == 2
    titles = [b.title for b in blocks]
    assert "Integration risk" in titles
    assert "Maintenance burden" in titles


def test_narrate_for_persona_falls_back_for_unknown_term() -> None:
    scored = _minimal_scored()
    profile = {"narrative_emphasis": ["totally_made_up_term"]}
    blocks = narrate_for_persona(scored, profile)
    assert len(blocks) == 1
    assert "fall back" in blocks[0].summary.lower() or "fallback" in blocks[0].summary.lower() or "no persona-specific" in blocks[0].summary.lower()


def test_narrate_for_persona_handles_space_separated_terms() -> None:
    """Profile JSONs sometimes use phrases like 'integration risk' rather than snake_case."""
    scored = _minimal_scored()
    profile = {"narrative_emphasis": ["integration risk"]}
    blocks = narrate_for_persona(scored, profile)
    assert blocks[0].title == "Integration risk"


def test_block_to_dict_is_json_serialisable() -> None:
    import json

    scored = _minimal_scored()
    blocks = narrate_for_persona(scored, {"narrative_emphasis": ["risk_concentration"]})
    json.dumps([block_to_dict(b) for b in blocks])  # raises if not serialisable


# ---------------------------------------------------------------------------
# Persona-block content sanity (SDLC-068)
# ---------------------------------------------------------------------------


def test_integration_risk_calls_out_critical_blocker() -> None:
    scored = _minimal_scored(blockers=[{"severity": "critical", "title": "x", "reason": "y"}])
    blocks = narrate_for_persona(scored, {"narrative_emphasis": ["integration_risk"]})
    callouts = [c for b in blocks for c in b.callouts]
    assert any(c.severity == "critical" for c in callouts)


def test_maintenance_burden_flags_zero_tests() -> None:
    scored = _minimal_scored(inventory={"source_files": 50, "test_files": 0, "workflow_files": 0})
    blocks = narrate_for_persona(scored, {"narrative_emphasis": ["maintenance_burden"]})
    assert blocks[0].summary  # non-empty
    facts = {f.label: f.value for f in blocks[0].facts}
    assert facts.get("Test files") == "0"


def test_dependency_concentration_summarises_runtime_count() -> None:
    deps = [{"name": f"pkg-{i}", "ecosystem": "pip"} for i in range(60)]
    scored = _minimal_scored(inventory={"dependency_graph": {"runtime": deps, "dev": [], "lockfiles": []}})
    blocks = narrate_for_persona(scored, {"narrative_emphasis": ["dependency_concentration"]})
    facts = {f.label: f.value for f in blocks[0].facts}
    assert facts["Runtime dependencies"] == "60"


def test_overclaim_detection_flags_service_with_zero_tests() -> None:
    scored = _minimal_scored(
        classification={"repo_archetype": "service", "maturity_profile": "production"},
        inventory={"test_files": 0, "workflow_files": 0},
    )
    blocks = narrate_for_persona(scored, {"narrative_emphasis": ["overclaim_detection"]})
    assert any(c.severity in {"high", "medium"} for c in blocks[0].callouts)


def test_failure_modes_block_lists_critical_subcats() -> None:
    findings = [
        {
            "id": "F-1",
            "category": "security_posture",
            "subcategory": "subprocess_shell_true",
            "severity": "critical",
            "confidence": "high",
            "statement": "shell=True",
            "evidence": [{"path": "src/x.py", "line_start": 12}],
            "score_impact": {"direction": "negative", "magnitude": 10},
        }
    ]
    scored = _minimal_scored(findings=findings)
    blocks = narrate_for_persona(scored, {"narrative_emphasis": ["failure_modes"]})
    assert blocks[0].callouts  # at least one callout
    facts = {f.label: f.value for f in blocks[0].facts}
    assert facts["Failure-mode findings"] == "1"


def test_expected_score_lift_uses_remediation_planner() -> None:
    findings = [
        {
            "id": "F-1",
            "category": "security_posture",
            "subcategory": "probable_secrets",
            "severity": "high",
            "confidence": "medium",
            "statement": "x",
            "evidence": [{"path": "src/x.py", "line_start": 1}],
            "score_impact": {"direction": "negative", "magnitude": 7},
        }
    ]
    scored = _minimal_scored(findings=findings)
    scored["scoring"]["effective_profile"] = {"maturity": "production"}
    blocks = narrate_for_persona(scored, {"narrative_emphasis": ["expected_score_lift"]})
    facts = {f.label: f.value for f in blocks[0].facts}
    assert facts["Remediation tasks"] != "0"
    # The lift fact's value starts with "+" by construction.
    assert facts["Expected total score lift"].startswith("+")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_scored(
    *,
    findings: list[dict] | None = None,
    inventory: dict | None = None,
    classification: dict | None = None,
    blockers: list[dict] | None = None,
) -> dict:
    return {
        "repo_meta": {"name": "demo", "default_branch": "main"},
        "classification": classification or {
            "repo_archetype": "library",
            "maturity_profile": "prototype",
            "deployment_surface": "package_only",
            "release_surface": "internal_only",
            "network_exposure": False,
            "classification_confidence": 0.8,
        },
        "inventory": inventory or {
            "source_files": 10,
            "test_files": 5,
            "workflow_files": 1,
            "test_to_source_ratio": 0.5,
            "dependency_graph": {"runtime": [], "dev": [], "lockfiles": []},
        },
        "findings": findings or [],
        "scoring": {
            "overall_score": 80,
            "verdict": "pass",
            "score_confidence": "medium",
            "category_scores": [
                {"category": "security_posture", "applicable": True, "score": 18, "max_score": 20, "summary": "x"},
                {"category": "documentation_truthfulness", "applicable": True, "score": 10, "max_score": 12, "summary": "x"},
                {"category": "architecture_design", "applicable": True, "score": 10, "max_score": 14, "summary": "x"},
                {"category": "code_quality_contracts", "applicable": True, "score": 13, "max_score": 14, "summary": "x"},
            ],
        },
        "hard_blockers": blockers or [],
    }
