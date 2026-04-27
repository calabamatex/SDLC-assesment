"""Tests for the methodology + glossary registry (post-RSF cutover).

The methodology box and glossary describe the RSF v1.0 framework, not
the legacy made-up rubric. Every entry / claim cites
``docs/frameworks/rsf_v1.0.md`` as the source of truth.
"""

from __future__ import annotations

import pathlib

from sdlc_assessor.renderer.deliverables._methodology import (
    _GLOSSARY_REGISTRY,
    all_glossary_terms,
    glossary_for,
    methodology_for,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _scored_for(use_case: str) -> dict:
    return {
        "classification": {"repo_archetype": "service", "maturity_profile": "production"},
        "scoring": {"effective_profile": {"use_case": use_case, "maturity": "production"}},
    }


# ---------------------------------------------------------------------------
# Methodology — describes the RSF framework
# ---------------------------------------------------------------------------


def test_methodology_formula_names_rsf_aggregation() -> None:
    """Formula must describe RSF §4 aggregation, not the legacy multipliers."""
    m = methodology_for(_scored_for("acquisition_diligence"), "acquisition_diligence")
    formula = m.score_formula
    # Per RSF §4: D_i = mean of sub-criteria; T = Σ D_i × w_i; T_% = T/500 × 100.
    assert "D_i" in formula
    assert "w_i" in formula
    assert "T_%" in formula or "T / 500" in formula
    # RSF special values per §1.
    assert "?" in formula
    assert "N/A" in formula


def test_methodology_threshold_explanation_drops_legacy_rubric() -> None:
    """No legacy made-up `pass_threshold` / `distinction_threshold` language."""
    for use_case in ("vc_diligence", "acquisition_diligence", "engineering_triage"):
        m = methodology_for(_scored_for(use_case), use_case)
        # The legacy "pass_threshold = 72" / "use_case_profiles.json" wording
        # is gone; the RSF framing is in.
        assert "RSF" in m.threshold_explanation or "Repository Scoring Framework" in m.threshold_explanation
        # Negative checks: the legacy phrases must not appear.
        assert "internal rubric" not in m.threshold_explanation
        assert "use_case_profiles.json" not in m.threshold_explanation


def test_methodology_explanation_lists_rsf_published_anchors() -> None:
    """The published-standard list from RSF §11 must be cited."""
    m = methodology_for(_scored_for("vc_diligence"), "vc_diligence")
    body = m.threshold_explanation
    # A non-trivial sample of the RSF §11 frameworks.
    for anchor in ("OpenSSF Scorecard", "OWASP", "NIST SSDF", "SLSA", "DORA"):
        assert anchor in body, f"methodology threshold-explanation missing {anchor}"


def test_methodology_multiplier_explanation_describes_rsf_aggregation() -> None:
    """No legacy three-multipliers language; instead, RSF §4 aggregation."""
    m = methodology_for(_scored_for("engineering_triage"), "engineering_triage")
    body = m.multiplier_explanation
    assert "RSF" in body
    # Negative checks.
    assert "SEVERITY_WEIGHTS" not in body
    assert "CONFIDENCE_MULTIPLIERS" not in body
    assert "severity_multiplier" not in body


def test_methodology_verdict_rule_table_describes_confidence_flagging() -> None:
    """Post-RSF the rule table is about confidence + N/A handling, not a
    pass/fail ladder. RSF doesn't define a single pass threshold."""
    m = methodology_for(_scored_for("acquisition_diligence"), "acquisition_diligence")
    sources = " ".join(rule["source"] for rule in m.verdict_rule_table)
    assert "RSF" in sources
    # No legacy verdict ladder.
    bodies = " ".join(rule["verdict"] for rule in m.verdict_rule_table)
    assert "pass_with_distinction" not in bodies
    assert "conditional_pass" not in bodies


def test_methodology_calibration_band_references_rsf_calibration_set() -> None:
    """RSF §5 prescribes a 3-point calibration set; methodology cites it."""
    m = methodology_for(_scored_for("acquisition_diligence"), "acquisition_diligence")
    assert m.calibration_band is not None
    body = m.calibration_band.lower()
    assert "rsf" in body or "calibration" in body
    # Negative: no legacy "internal rubric, n=26 fixtures" claim.
    assert "n=26" not in body
    assert "n≈26" not in body


# ---------------------------------------------------------------------------
# Glossary — RSF terms only; no legacy entries
# ---------------------------------------------------------------------------


def test_legacy_glossary_terms_are_gone() -> None:
    """diligence_bar / pass_threshold / distinction_threshold etc. must be removed."""
    forbidden = {
        "diligence_bar",
        "pass_threshold",
        "distinction_threshold",
        "severity_weight",
        "confidence_multiplier",
        "maturity_factor",
        "production_flat_penalty",
        "score_confidence",
    }
    actual = set(all_glossary_terms())
    leaked = forbidden & actual
    assert not leaked, f"legacy glossary entries still present: {sorted(leaked)}"


def test_rsf_glossary_terms_present() -> None:
    """The glossary leads with the RSF terms the report actually uses."""
    expected = {"rsf_persona_total", "rsf_dimension_score", "rsf_unverified"}
    actual = set(all_glossary_terms())
    missing = expected - actual
    assert not missing, f"missing RSF glossary entries: {sorted(missing)}"


def test_glossary_entries_cite_rsf_doc_or_real_paths() -> None:
    """Every source must be either ``docs/frameworks/rsf_v1.0.md`` or a real path."""
    for term, entry in _GLOSSARY_REGISTRY.items():
        for src in entry.sources:
            # Strip optional `:line` and parenthetical sections like `(§3, §4)`.
            path_only = src.split(":", 1)[0].split(" (", 1)[0]
            full_path = REPO_ROOT / path_only
            assert full_path.exists(), (
                f"glossary entry {term!r} cites missing path {src!r}"
            )


def test_glossary_for_each_persona_includes_the_rsf_basics() -> None:
    for use_case in (
        "acquisition_diligence",
        "vc_diligence",
        "engineering_triage",
        "remediation_agent",
    ):
        terms = {e.term for e in glossary_for(use_case)}
        # Every persona's glossary leads with the RSF terms.
        for required in (
            "persona-weighted total (T_%)",
            "dimension score (D_i)",
            "unverified (`?`)",
        ):
            assert required in terms, (
                f"{use_case} glossary missing RSF term: {required!r}"
            )
