"""Score-decomposition builder (0.11.0 depth pass).

Reconstructs the arithmetic the scorer used to land at ``overall_score``
so the deliverable can show its math instead of saying "below the
diligence bar."

Every value here is **real** — pulled from :mod:`sdlc_assessor.scorer.engine`
constants (``BASE_WEIGHTS``, ``SEVERITY_WEIGHTS``, ``CONFIDENCE_MULTIPLIERS``,
``PRODUCTION_FLAT_PENALTIES``), the use-case profile multipliers, the
maturity severity multiplier, the per-finding contributions, and the
``scoring`` block already emitted to ``scored.json``.

Nothing in this module is editorial or invented. The 0.11.0 plan
explicitly excludes the cost frame (engineer-day conversions, holdback
formulas) because those would be invented; they're deferred to 0.16.0.
"""

from __future__ import annotations

from sdlc_assessor.profiles.loader import load_maturity_profiles, load_use_case_profiles
from sdlc_assessor.renderer.deliverables.base import (
    CategoryArithmetic,
    ScoreDecomposition,
)
from sdlc_assessor.scorer.engine import (
    BASE_WEIGHTS,
    CONFIDENCE_MULTIPLIERS,
    PRODUCTION_FLAT_PENALTIES,
    SEVERITY_WEIGHTS,
)


def _maturity_severity_multiplier(maturity: str) -> float:
    """Read severity_multiplier for the given maturity profile.

    Falls back to 1.0 if the profile can't be loaded — matches the
    scorer's own fallback in ``score_evidence``.
    """
    try:
        profiles = load_maturity_profiles()
    except Exception:
        return 1.0
    profile = profiles.get(maturity, {})
    return float(profile.get("severity_multiplier", 1.0))


def _per_finding_deductions(
    findings_in_cat: list[dict], *, maturity_multiplier: float
) -> list[dict]:
    """Reconstruct each finding's contribution to the category deduction.

    Mirrors the arithmetic in ``scorer.engine.score_evidence``:

        deduction = SEVERITY_WEIGHTS[sev]
                  * CONFIDENCE_MULTIPLIERS[conf]
                  * maturity_severity_multiplier
                  * (magnitude / 10)
    """
    rows: list[dict] = []
    for f in findings_in_cat:
        sev = f.get("severity", "low")
        conf = f.get("confidence", "medium")
        mag = float(f.get("score_impact", {}).get("magnitude", 0))
        sev_w = SEVERITY_WEIGHTS.get(sev, 0)
        conf_m = CONFIDENCE_MULTIPLIERS.get(conf, 0.9)
        deduction = sev_w * conf_m * maturity_multiplier * (mag / 10.0)
        rows.append(
            {
                "finding_id": f.get("id"),
                "subcategory": f.get("subcategory"),
                "severity": sev,
                "confidence": conf,
                "magnitude": mag,
                "severity_weight": sev_w,
                "confidence_multiplier": conf_m,
                "maturity_multiplier": maturity_multiplier,
                "deduction": round(deduction, 3),
            }
        )
    rows.sort(key=lambda r: -r["deduction"])
    return rows


def _category_label(use_case: str, category: str) -> str:
    """Persona-relabelled category title; falls back to the raw category id."""
    try:
        from sdlc_assessor.renderer.deliverables._vocab import vocab_for
    except Exception:
        return category.replace("_", " ").title()
    vocab = vocab_for(use_case)
    return vocab.category_labels.get(category) or category.replace("_", " ").title()


def _which_flat_penalties_fired(scored: dict, *, maturity: str) -> list[tuple[str, int]]:
    """Identify which production flat penalties contributed to the score.

    The scorer reports the *total* in ``scoring.flat_penalty_applied`` but
    not the breakdown. We re-derive the breakdown from the same sources
    the scorer uses: the inventory + findings (for `missing_*` subcategory
    presence) and the maturity. Only fires for production maturity.
    """
    if maturity != "production":
        return []

    findings = scored.get("findings") or []
    inventory = scored.get("inventory") or {}
    fired: list[tuple[str, int]] = []

    has_missing_ci = any(
        (f.get("subcategory") or "").lower() == "missing_ci" for f in findings
    )
    has_missing_readme = any(
        (f.get("subcategory") or "").lower() == "missing_readme" for f in findings
    )
    no_tests = (inventory.get("test_files", 0) or 0) == 0
    has_missing_tests_finding = any(
        (f.get("subcategory") or "").lower() == "missing_tests" for f in findings
    )

    if has_missing_ci:
        fired.append(("missing_ci", PRODUCTION_FLAT_PENALTIES["missing_ci"]))
    if has_missing_readme:
        fired.append(("missing_readme", PRODUCTION_FLAT_PENALTIES["missing_readme"]))
    if has_missing_tests_finding or no_tests:
        fired.append(("missing_tests", PRODUCTION_FLAT_PENALTIES["missing_tests"]))

    return fired


def _score_confidence_rationale(scored: dict) -> str:
    """Reconstruct the rationale for the ``score_confidence`` value.

    Mirrors ``scorer.engine._compute_score_confidence`` — the three
    inputs are ``classification_confidence``, ``proxy_ratio`` (fraction of
    findings with confidence "medium"), and ``evidence_density``
    (findings / source_files). We don't invent thresholds; we name the
    actual values that produced the bucket.
    """
    findings = scored.get("findings") or []
    inventory = scored.get("inventory") or {}
    classification = scored.get("classification") or {}

    source_files = max(int(inventory.get("source_files", 0) or 0), 1)
    evidence_density = len(findings) / source_files
    proxy_count = sum(1 for f in findings if f.get("confidence") == "medium")
    proxy_ratio = proxy_count / max(len(findings), 1)
    classification_confidence = float(classification.get("classification_confidence", 0.2))

    bucket = (scored.get("scoring") or {}).get("score_confidence", "medium")
    return (
        f"score_confidence={bucket} from "
        f"classification_confidence={classification_confidence:.2f}, "
        f"proxy_ratio={proxy_ratio:.2f}, "
        f"evidence_density={evidence_density:.2f}; thresholds in "
        f"scorer/engine.py:_compute_score_confidence"
    )


def build_score_decomposition(
    scored: dict, use_case_profile: dict | None = None
) -> ScoreDecomposition:
    """Construct the :class:`ScoreDecomposition` for a scored payload.

    Reads everything from ``scored.json`` + the canonical scoring
    constants. ``use_case_profile`` is optional; if omitted, it's loaded
    from ``profiles/data/use_case_profiles.json`` using the profile name
    in ``scored.scoring.effective_profile.use_case``.
    """
    scoring = scored.get("scoring") or {}
    effective_profile = scoring.get("effective_profile") or {}
    use_case = effective_profile.get("use_case", "engineering_triage")
    maturity = effective_profile.get("maturity", "production")

    if use_case_profile is None:
        try:
            all_profiles = load_use_case_profiles()
        except Exception:
            all_profiles = {}
        use_case_profile = all_profiles.get(use_case) or {}

    pass_threshold = int(use_case_profile.get("pass_threshold", 70))
    distinction_threshold = int(use_case_profile.get("distinction_threshold", 85))
    threshold_source = (
        f"sdlc_assessor/profiles/data/use_case_profiles.json:"
        f"{use_case}.pass_threshold (={pass_threshold})"
    )

    multipliers = use_case_profile.get("category_multipliers", {}) or {}
    maturity_multiplier = _maturity_severity_multiplier(maturity)

    # Compute the same denominator the scorer uses, so normalized_weight
    # matches what the scorer applied (subject to applicability).
    category_scores_list = scoring.get("category_scores") or []
    by_cat = {
        c.get("category"): c
        for c in category_scores_list
        if isinstance(c, dict) and c.get("category")
    }

    findings_by_cat: dict[str, list[dict]] = {}
    for f in scored.get("findings") or []:
        cat = f.get("category")
        if not cat:
            continue
        findings_by_cat.setdefault(cat, []).append(f)

    # Re-derive applicability + weighted_max so we can emit normalized
    # weights for each category.
    applicable_cats: dict[str, float] = {}
    for cat, base in BASE_WEIGHTS.items():
        c = by_cat.get(cat) or {}
        is_applicable = bool(c.get("applicable", True))
        if not is_applicable:
            continue
        applicable_cats[cat] = base * float(multipliers.get(cat, 1.0))

    denominator = sum(applicable_cats.values()) or 1.0

    categories: list[CategoryArithmetic] = []
    for cat, base in BASE_WEIGHTS.items():
        c = by_cat.get(cat) or {}
        applicable = bool(c.get("applicable", True))
        applicability = "applicable" if applicable else "not_applicable"
        multiplier = float(multipliers.get(cat, 1.0))

        if applicable:
            normalized_weight = round(100.0 * applicable_cats[cat] / denominator)
        else:
            normalized_weight = 0

        deductions = (
            _per_finding_deductions(
                findings_by_cat.get(cat, []), maturity_multiplier=maturity_multiplier
            )
            if applicable
            else []
        )

        categories.append(
            CategoryArithmetic(
                category=cat,
                label=_category_label(use_case, cat),
                base_max=int(base),
                multiplier=multiplier,
                applicability=applicability,
                earned=float(c.get("score", 0) or 0),
                deductions=deductions,
                normalized_weight=int(normalized_weight),
            )
        )

    overall = int(scoring.get("overall_score", 0) or 0)

    return ScoreDecomposition(
        overall=overall,
        pass_threshold=pass_threshold,
        distinction_threshold=distinction_threshold,
        threshold_source=threshold_source,
        flat_penalties=_which_flat_penalties_fired(scored, maturity=maturity),
        confidence_multiplier_table=dict(CONFIDENCE_MULTIPLIERS),
        severity_weight_table=dict(SEVERITY_WEIGHTS),
        maturity_factor=maturity_multiplier,
        categories=categories,
        score_confidence=str(scoring.get("score_confidence") or ""),
        score_confidence_rationale=_score_confidence_rationale(scored),
    )


__all__ = ["build_score_decomposition"]
