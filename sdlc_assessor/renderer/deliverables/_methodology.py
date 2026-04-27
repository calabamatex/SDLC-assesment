"""Methodology box + glossary registry (0.11.0 depth pass).

Every entry here is **grounded** — it cites a source path in this
repository where the term is actually defined. No editorial
definitions. No "industry standard" handwaves.

Rule: if I can't cite a file:line where the rule is implemented, the
entry doesn't ship in 0.11.0. Things that would require a real
calibration corpus or peer-reviewed methodology (e.g. *what does a
pass_threshold of 74 mean against historical M&A outcomes*) are out
of scope here; they ship in 0.14.0+.
"""

from __future__ import annotations

from sdlc_assessor.renderer.deliverables.base import (
    GlossaryEntry,
    MethodologyNote,
)

# ---------------------------------------------------------------------------
# Methodology
# ---------------------------------------------------------------------------


_SCORE_FORMULA = (
    "RSF v1.0 §4 — Aggregation\n"
    "\n"
    "Per-dimension score:\n"
    "  D_i = (Σ_j s_ij) / (n_i × 5) × 5\n"
    "  where s_ij is the score (0..5) for sub-criterion j of dimension i,\n"
    "  and n_i is the count of sub-criteria scored (excluding N/A).\n"
    "\n"
    "Persona-weighted total:\n"
    "  T = Σ_i D_i × w_i\n"
    "  where w_i is the persona's weight for dimension i (RSF §3 matrix,\n"
    "  weights sum to 100 per persona). T is on a 0..500 scale.\n"
    "\n"
    "Normalized presentation:\n"
    "  T_% = T / 500 × 100\n"
    "\n"
    "Special values (RSF §1):\n"
    "  ? = evidence not collected — treated as 0 in the math but flagged.\n"
    "  N/A = criterion does not apply — excluded from the dimension's\n"
    "        denominator; persona weights for N/A dimensions are\n"
    "        proportionally redistributed across remaining dimensions."
)


def _verdict_rule_table() -> list[dict]:
    """RSF v1.0 does not define a single verdict ladder; consumers compare
    persona-weighted totals against peer benchmarks.

    The table below names the RSF *confidence* rules instead — these ARE
    framework-defined and gate report disclosures.
    """
    return [
        {
            "condition": "Any sub-criterion in a dimension is `?` (unverified)",
            "verdict": "dimension flagged for confidence",
            "source": "RSF §4 — confidence flag",
        },
        {
            "condition": ">25% of a persona's weight maps to flagged dimensions",
            "verdict": "report header carries a 'limited confidence' warning",
            "source": "RSF §4 — limited-confidence warning",
        },
        {
            "condition": "All sub-criteria in a dimension are N/A",
            "verdict": "dimension excluded; persona weights redistributed across remaining dims",
            "source": "RSF §3 + §4 — N/A redistribution",
        },
        {
            "condition": (
                "Inter-rater disagreement >1 point per sub-criterion (multi-assessor)"
            ),
            "verdict": "evidence review triggered; lower score recorded if persists",
            "source": "RSF §5 — inter-rater protocol",
        },
    ]


def _calibration_band_for(scored: dict) -> str | None:
    """Surface RSF §5's calibration-set guidance.

    RSF §5 prescribes scoring against three reference points before
    assessing a target: a widely-used OSS project with published
    Scorecard/SLSA/SAMM evidence (expected RSF total 4.0+), a typical
    mid-stage SaaS company repo (2.5–3.5), and a neglected internal
    repo with no CI/CD discipline (0.5–1.5). This assessor has not yet
    integrated those reference scores; flag the gap explicitly.
    """
    cls = scored.get("classification") or {}
    maturity = cls.get("maturity_profile", "unknown")
    archetype = cls.get("repo_archetype", "unknown")

    return (
        f"Asset profile: archetype={archetype}, maturity={maturity}. "
        "RSF §5 calibration-set scoring (vs. a published-evidence OSS project, "
        "a typical mid-stage SaaS, and a neglected internal repo) is not yet "
        "integrated into this assessor's pipeline; the per-persona total below "
        "is an absolute reading against the framework's anchors, not a relative "
        "reading against a peer corpus."
    )


def methodology_for(scored: dict, use_case: str) -> MethodologyNote:
    """Construct the methodology box for the given persona.

    The box names the formula, the threshold (via the persona's
    use-case profile), the multiplier composition, and the verdict
    rule. Every claim cites a source path.
    """
    return MethodologyNote(
        score_formula=_SCORE_FORMULA,
        threshold_explanation=(
            "The Repository Scoring Framework v1.0 does not define a single "
            "fixed pass threshold. Each persona has a weight matrix (RSF §3) "
            "that produces a 0–100% total from the 8 dimension scores. "
            "Consumers compare a target's total against peer benchmarks "
            "(RSF §5 calibration set) rather than against a single bar. "
            "Per-criterion level anchors (0..5) come from the published "
            "industry standards in §11's framework-to-criterion mapping: "
            "OpenSSF Scorecard, OWASP ASVS, OWASP Top 10, NIST SSDF, SLSA, "
            "CycloneDX/SPDX, Sigstore, DORA, ISO/IEC 27001, AICPA SOC 2, "
            "CSA CAIQ. See docs/frameworks/rsf_v1.0.md for the full spec."
        ),
        multiplier_explanation=(
            "RSF §4 has no severity / confidence / maturity multipliers. "
            "Aggregation is the unweighted mean of sub-criterion scores per "
            "dimension (Σ_j s_ij / n_i, on the 0..5 scale), then a persona-"
            "weighted sum across dimensions (Σ_i D_i × w_i, on the 0..500 "
            "scale, normalized to 0..100%). The only inputs are: (a) the "
            "0..5 score against each sub-criterion's level anchors, (b) the "
            "persona's weight row from §3."
        ),
        verdict_rule_table=_verdict_rule_table(),
        calibration_band=_calibration_band_for(scored),
    )


# ---------------------------------------------------------------------------
# Glossary registry
#
# Each entry sources a code path where the term is actually defined.
# When a definition rests on speculation rather than code, the entry
# does not ship.
# ---------------------------------------------------------------------------

_GLOSSARY_REGISTRY: dict[str, GlossaryEntry] = {
    "rsf_persona_total": GlossaryEntry(
        term="persona-weighted total (T_%)",
        short_def="The 0–100% weighted sum of dimension scores using a persona's RSF §3 weight row.",
        long_def=(
            "Per RSF §4: T = Σ_i D_i · w_i where D_i is the dimension's mean "
            "(0..5) and w_i is the persona's weight for that dimension (sums "
            "to 100 across all 8 dimensions). T_% = T / 500 × 100. RSF does "
            "not specify a single 'pass threshold'; consumers compare T_% "
            "against peer benchmarks per RSF §5 (calibration set)."
        ),
        sources=["docs/frameworks/rsf_v1.0.md (§3, §4)"],
    ),
    "rsf_dimension_score": GlossaryEntry(
        term="dimension score (D_i)",
        short_def="The mean of a dimension's sub-criterion scores, on the 0..5 scale.",
        long_def=(
            "Per RSF §4: D_i = (Σ_j s_ij) / (n_i · 5) × 5, which simplifies "
            "to the unweighted mean of the dimension's scored sub-criteria "
            "(excluding N/A). Each sub-criterion's 0..5 score comes from the "
            "level anchors in RSF §2 — see the framework-to-criterion mapping "
            "in §11 for the published-standard reference per criterion."
        ),
        sources=["docs/frameworks/rsf_v1.0.md (§2, §4)"],
    ),
    "rsf_unverified": GlossaryEntry(
        term="unverified (`?`)",
        short_def="Sub-criterion the assessor could not collect evidence for.",
        long_def=(
            "Per RSF §1: `?` is treated as 0 in the math but flagged "
            "separately so the report distinguishes 'absent' (a real 0 "
            "score) from 'unverified' (no evidence collected). Any "
            "dimension with ≥1 `?` carries a confidence flag; if >25% of a "
            "persona's weight maps to flagged dimensions, the report header "
            "carries a 'limited confidence' warning."
        ),
        sources=["docs/frameworks/rsf_v1.0.md (§1, §4)"],
    ),
    # Legacy glossary entries (severity_weight, confidence_multiplier,
    # maturity_factor, production_flat_penalty, score_confidence) were
    # removed in the RSF cutover. They described the made-up multiplier
    # chain in the legacy scoring engine; under RSF, aggregation is the
    # unweighted mean of sub-criterion scores per dimension and the
    # persona-weighted sum across dimensions (RSF §4) — no multipliers,
    # no flat penalties.
    "expected_score_delta": GlossaryEntry(
        term="expected score delta",
        short_def="A remediation task's projected point gain when closed, computed by the planner.",
        long_def=(
            "Computed in remediation/planner.py from the finding's severity, "
            "confidence, maturity, and magnitude. This is a *projection* by "
            "the scoring engine, not a measurement against historical "
            "outcomes — the actual score change after closure may differ."
        ),
        sources=["sdlc_assessor/remediation/planner.py"],
    ),
    "applicability": GlossaryEntry(
        term="applicability",
        short_def="Whether a category counts toward the score for this archetype + maturity.",
        long_def=(
            "Categories can be marked 'applicable' or 'not_applicable' per "
            "(archetype, maturity) combination. Not-applicable categories "
            "are excluded from the weighted_max denominator so they don't "
            "drag down the score for archetypes where the category is "
            "irrelevant (e.g. reproducibility for a service archetype)."
        ),
        sources=[
            "sdlc_assessor/profiles/data/maturity_profiles.json",
            "sdlc_assessor/profiles/data/repo_type_profiles.json",
            "sdlc_assessor/scorer/engine.py:37",
        ],
    ),
    "hard_blocker": GlossaryEntry(
        term="hard blocker",
        short_def="A finding-class that gates the verdict regardless of score.",
        long_def=(
            "Detected by scorer/blockers.py — covers committed credentials, "
            "missing CI under production maturity, unsafe shell exec on a "
            "networked service, etc. Severity is 'critical' or 'high'. "
            "Critical blockers force the verdict below 'pass' even when the "
            "numeric score clears the threshold."
        ),
        sources=["sdlc_assessor/scorer/blockers.py"],
    ),
}


# ---------------------------------------------------------------------------
# Per-persona glossary selection
# ---------------------------------------------------------------------------


_PERSONA_GLOSSARY_KEYS: dict[str, list[str]] = {
    # Post-RSF: every persona's glossary leads with the RSF terms
    # (persona-weighted total, dimension score, unverified marker) since
    # those are what the report actually surfaces. Persona-specific
    # additions follow.
    "acquisition_diligence": [
        "rsf_persona_total",
        "rsf_dimension_score",
        "rsf_unverified",
        "applicability",
        "hard_blocker",
    ],
    "vc_diligence": [
        "rsf_persona_total",
        "rsf_dimension_score",
        "rsf_unverified",
        "hard_blocker",
    ],
    "engineering_triage": [
        "rsf_persona_total",
        "rsf_dimension_score",
        "rsf_unverified",
        "applicability",
        "expected_score_delta",
        "hard_blocker",
    ],
    "remediation_agent": [
        "rsf_persona_total",
        "rsf_dimension_score",
        "rsf_unverified",
        "expected_score_delta",
        "hard_blocker",
    ],
}


def glossary_for(use_case: str) -> list[GlossaryEntry]:
    """Return the glossary slice this persona's report should ship with."""
    keys = _PERSONA_GLOSSARY_KEYS.get(use_case) or list(_GLOSSARY_REGISTRY.keys())
    return [_GLOSSARY_REGISTRY[k] for k in keys if k in _GLOSSARY_REGISTRY]


def all_glossary_terms() -> list[str]:
    """All glossary keys; used by tests."""
    return list(_GLOSSARY_REGISTRY.keys())


__all__ = ["all_glossary_terms", "glossary_for", "methodology_for"]
