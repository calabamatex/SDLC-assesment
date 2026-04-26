"""Tests for the score-decomposition builder (0.11.0 depth pass)."""

from __future__ import annotations

from sdlc_assessor.renderer.deliverables._decomposition import build_score_decomposition
from sdlc_assessor.scorer.engine import (
    BASE_WEIGHTS,
    CONFIDENCE_MULTIPLIERS,
    PRODUCTION_FLAT_PENALTIES,
    SEVERITY_WEIGHTS,
)


def _scored_minimal(*, use_case: str, maturity: str = "production", overall: int = 59) -> dict:
    return {
        "classification": {
            "repo_archetype": "service",
            "maturity_profile": maturity,
            "classification_confidence": 0.9,
        },
        "inventory": {"source_files": 100, "test_files": 12},
        "findings": [
            {
                "id": "F-1",
                "category": "security_posture",
                "subcategory": "probable_secrets",
                "severity": "high",
                "confidence": "high",
                "score_impact": {"magnitude": 7},
            },
            {
                "id": "F-2",
                "category": "code_quality_contracts",
                "subcategory": "broad_except_exception",
                "severity": "medium",
                "confidence": "medium",
                "score_impact": {"magnitude": 4},
            },
        ],
        "scoring": {
            "effective_profile": {"use_case": use_case, "maturity": maturity},
            "overall_score": overall,
            "score_confidence": "high",
            "category_scores": [
                {"category": cat, "applicable": True, "score": 5.0, "max_score": 10}
                for cat in BASE_WEIGHTS
            ],
        },
    }


def test_thresholds_come_from_use_case_profile() -> None:
    scored = _scored_minimal(use_case="acquisition_diligence")
    decomp = build_score_decomposition(scored)
    # Real values from use_case_profiles.json — not made up.
    assert decomp.pass_threshold == 74
    assert decomp.distinction_threshold == 88
    assert "use_case_profiles.json:acquisition_diligence.pass_threshold" in decomp.threshold_source
    assert "=74" in decomp.threshold_source


def test_thresholds_per_persona_differ() -> None:
    for use_case, expected_pass in [
        ("engineering_triage", 70),
        ("vc_diligence", 72),
        ("acquisition_diligence", 74),
        ("remediation_agent", 70),
    ]:
        decomp = build_score_decomposition(_scored_minimal(use_case=use_case))
        assert decomp.pass_threshold == expected_pass


def test_per_finding_deduction_matches_scorer_formula() -> None:
    """Each finding's deduction equals SEV × CONF × MATURITY × magnitude/10."""
    scored = _scored_minimal(use_case="engineering_triage", maturity="production")
    decomp = build_score_decomposition(scored)

    sec_cat = next(c for c in decomp.categories if c.category == "security_posture")
    f1_dedux = sec_cat.deductions[0]
    expected = (
        SEVERITY_WEIGHTS["high"]
        * CONFIDENCE_MULTIPLIERS["high"]
        * 1.2  # production maturity multiplier
        * (7 / 10.0)
    )
    assert abs(f1_dedux["deduction"] - expected) < 0.001
    assert f1_dedux["severity_weight"] == SEVERITY_WEIGHTS["high"]
    assert f1_dedux["confidence_multiplier"] == CONFIDENCE_MULTIPLIERS["high"]
    assert f1_dedux["maturity_multiplier"] == 1.2


def test_maturity_factor_changes_with_profile() -> None:
    prod = build_score_decomposition(_scored_minimal(use_case="engineering_triage", maturity="production"))
    proto = build_score_decomposition(_scored_minimal(use_case="engineering_triage", maturity="prototype"))
    research = build_score_decomposition(_scored_minimal(use_case="engineering_triage", maturity="research"))
    # Real values from maturity_profiles.json.
    assert prod.maturity_factor == 1.2
    assert proto.maturity_factor == 0.95
    assert research.maturity_factor == 0.9


def test_severity_and_confidence_tables_match_scorer() -> None:
    decomp = build_score_decomposition(_scored_minimal(use_case="engineering_triage"))
    assert decomp.severity_weight_table == dict(SEVERITY_WEIGHTS)
    assert decomp.confidence_multiplier_table == dict(CONFIDENCE_MULTIPLIERS)


def test_flat_penalties_fire_only_on_production() -> None:
    """missing_ci / missing_readme / missing_tests fire only under production."""
    scored = _scored_minimal(use_case="engineering_triage", maturity="production")
    scored["findings"].append(
        {
            "id": "F-3",
            "category": "documentation_truthfulness",
            "subcategory": "missing_ci",
            "severity": "high",
            "confidence": "high",
            "score_impact": {"magnitude": 6},
        }
    )
    prod = build_score_decomposition(scored)
    assert ("missing_ci", PRODUCTION_FLAT_PENALTIES["missing_ci"]) in prod.flat_penalties

    scored["scoring"]["effective_profile"]["maturity"] = "prototype"
    scored["classification"]["maturity_profile"] = "prototype"
    proto = build_score_decomposition(scored)
    assert proto.flat_penalties == []


def test_normalized_weights_sum_to_100_for_applicable_categories() -> None:
    decomp = build_score_decomposition(_scored_minimal(use_case="acquisition_diligence"))
    applicable_total = sum(c.normalized_weight for c in decomp.categories if c.applicability == "applicable")
    # Rounding to int per category may drift ±1; tolerate that.
    assert 99 <= applicable_total <= 101


def test_category_label_is_persona_specific() -> None:
    """Acquisition relabels 'maintainability_operability' to 'Day-1 ownership cost'."""
    decomp = build_score_decomposition(_scored_minimal(use_case="acquisition_diligence"))
    label_by_cat = {c.category: c.label for c in decomp.categories}
    assert "Day-1 ownership cost" in label_by_cat["maintainability_operability"]


def test_score_confidence_rationale_names_real_inputs() -> None:
    decomp = build_score_decomposition(_scored_minimal(use_case="engineering_triage"))
    rationale = decomp.score_confidence_rationale
    assert "classification_confidence" in rationale
    assert "proxy_ratio" in rationale
    assert "evidence_density" in rationale
    assert "scorer/engine.py" in rationale


def test_per_category_deductions_are_sorted_by_impact() -> None:
    scored = _scored_minimal(use_case="engineering_triage")
    # Add a smaller finding to the same category.
    scored["findings"].append(
        {
            "id": "F-low",
            "category": "code_quality_contracts",
            "subcategory": "print_usage",
            "severity": "low",
            "confidence": "low",
            "score_impact": {"magnitude": 1},
        }
    )
    decomp = build_score_decomposition(scored)
    cqc = next(c for c in decomp.categories if c.category == "code_quality_contracts")
    deductions = cqc.deductions
    for i in range(len(deductions) - 1):
        assert deductions[i]["deduction"] >= deductions[i + 1]["deduction"]
