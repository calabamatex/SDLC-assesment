"""Scoring engine for Phase 4/8."""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Any

from sdlc_assessor.scorer.blockers import detect_hard_blockers
from sdlc_assessor.scorer.precedence import build_effective_profile

BASE_WEIGHTS = {
    "architecture_design": 15,
    "code_quality_contracts": 15,
    "testing_quality_gates": 15,
    "security_posture": 20,
    "dependency_release_hygiene": 10,
    "documentation_truthfulness": 10,
    "maintainability_operability": 10,
    "reproducibility_research_rigor": 5,
}

# Phase 6 calibration (SDLC-026) raises these from {1, 2, 4, 6} → {2, 5, 10, 20}.
SEVERITY_WEIGHTS = {"info": 0, "low": 2, "medium": 5, "high": 10, "critical": 20}
# Phase 6 calibration tightens dampening.
CONFIDENCE_MULTIPLIERS = {"high": 1.0, "medium": 0.9, "low": 0.7}

# Production-maturity flat penalties (SDLC-026). Each fires only when the
# corresponding finding is present AND maturity is "production".
PRODUCTION_FLAT_PENALTIES = {
    "missing_ci": 10,
    "missing_readme": 8,
    "missing_tests": 15,
}


def _resolve_applicability(maturity_profile: dict, repo_type_profile: dict) -> dict:
    result = dict(maturity_profile.get("category_applicability", {}))
    result.update(repo_type_profile.get("applicability_overrides", {}))
    return result


def _build_category_summary(
    category: str,
    applicability: str,
    findings_in_cat: list[dict],
    deduction_total: float,
    score: float,
    max_score: float,
) -> str:
    """Compose a 2-5 sentence narrative for a category score row.

    Required by docs/scoring_engine_spec.md §Narrative rules and the
    ``category_scores[].summary`` schema field.
    """
    if applicability == "not_applicable":
        return (
            f"Category '{category}' is not applicable to this repo archetype/maturity; "
            "excluded from the weighted maximum."
        )
    if not findings_in_cat:
        if max_score > 0 and score >= max_score:
            return "No findings in this category; full points retained."
        return "No findings in this category."

    sorted_findings = sorted(
        findings_in_cat,
        key=lambda f: (
            -SEVERITY_WEIGHTS.get(f.get("severity", "low"), 0),
            -CONFIDENCE_MULTIPLIERS.get(f.get("confidence", "medium"), 0.0),
            -float(f.get("score_impact", {}).get("magnitude", 0)),
        ),
    )
    strongest = sorted_findings[0]
    strongest_stmt = strongest.get("statement", "<unspecified>")
    strongest_sev = strongest.get("severity", "low")
    other_count = len(sorted_findings) - 1
    secondary_dedux = max(0.0, deduction_total - _expected_strongest_deduction(strongest))
    parts = [
        f"Category '{category}' is {applicability} for this repo.",
        f"Strongest issue: {strongest_stmt} (severity={strongest_sev}).",
    ]
    if other_count > 0:
        parts.append(
            f"{other_count} other finding{'s' if other_count != 1 else ''} contributed "
            f"{secondary_dedux:.1f} additional points of deduction."
        )
    if score == 0 and max_score > 0:
        parts.append("Category score is bounded at 0; deductions exceeded available points.")
    return " ".join(parts)


def _expected_strongest_deduction(finding: dict) -> float:
    sev = SEVERITY_WEIGHTS.get(finding.get("severity", "low"), 0)
    conf = CONFIDENCE_MULTIPLIERS.get(finding.get("confidence", "medium"), 0.0)
    mag = float(finding.get("score_impact", {}).get("magnitude", 0)) / 10.0
    return sev * conf * mag


def _key_findings(findings_in_cat: list[dict]) -> list[str]:
    """Top-3 finding ids in the category by deduction magnitude."""
    ranked = sorted(
        findings_in_cat,
        key=lambda f: -(_expected_strongest_deduction(f)),
    )
    return [f.get("id", "") for f in ranked[:3] if f.get("id")]


def _missing_subcats(findings: list[dict], inventory: dict) -> set[str]:
    """Identify which production-essential signals are absent."""
    subcats = {f.get("subcategory") for f in findings}
    missing = set()
    if "missing_ci" in subcats:
        missing.add("missing_ci")
    if "missing_readme" in subcats:
        missing.add("missing_readme")
    if int(inventory.get("test_files", 0)) == 0:
        missing.add("missing_tests")
    return missing


def score_evidence(
    evidence: dict,
    use_case: str,
    maturity: str,
    repo_type: str,
    policy_overrides: dict | None = None,
    *,
    use_llm_narrator: bool = False,
    llm_model: str | None = None,
) -> dict:
    effective = build_effective_profile(use_case, maturity, repo_type, policy_overrides=policy_overrides)
    use_case_profile = effective["use_case_profile"]
    maturity_profile = effective["maturity_profile"]
    repo_type_profile = effective["repo_type_profile"]

    applicability = _resolve_applicability(maturity_profile, repo_type_profile)
    multipliers = use_case_profile.get("category_multipliers", {})

    weighted_max: dict[str, float] = {}
    for cat, base in BASE_WEIGHTS.items():
        app = applicability.get(cat, "applicable")
        if app == "not_applicable":
            continue
        weighted_max[cat] = base * multipliers.get(cat, 1.0)

    denominator = sum(weighted_max.values()) or 1.0
    normalized_max = {cat: (100.0 * w / denominator) for cat, w in weighted_max.items()}

    findings = list(evidence.get("findings", []))
    inventory = evidence.get("inventory", {}) or {}

    deductions_by_cat: dict[str, float] = defaultdict(float)
    findings_by_cat: dict[str, list[dict]] = defaultdict(list)
    maturity_multiplier = float(maturity_profile.get("severity_multiplier", 1.0))

    for f in findings:
        cat = f.get("category")
        if cat not in normalized_max:
            continue
        sev = SEVERITY_WEIGHTS.get(f.get("severity", "low"), 0)
        conf = CONFIDENCE_MULTIPLIERS.get(f.get("confidence", "medium"), 0.9)
        mag = float(f.get("score_impact", {}).get("magnitude", 0)) / 10.0
        deductions_by_cat[cat] += sev * conf * maturity_multiplier * mag
        findings_by_cat[cat].append(f)

    category_score_floats: dict[str, dict[str, float]] = {}
    for cat, max_points in normalized_max.items():
        score = max_points - deductions_by_cat[cat]
        score = max(0.0, min(max_points, score))
        category_score_floats[cat] = {
            "score": score,
            "max": max_points,
        }

    # Production-maturity flat penalties (SDLC-026).
    flat_penalty = 0.0
    if maturity == "production":
        missing = _missing_subcats(findings, inventory)
        for key, penalty in PRODUCTION_FLAT_PENALTIES.items():
            if key in missing:
                flat_penalty += penalty

    raw_total = sum(v["score"] for v in category_score_floats.values())
    final_score_precise = max(0.0, min(100.0, raw_total - flat_penalty))

    # Build schema-conformant category_scores list.
    category_scores: list[dict] = []
    for cat in BASE_WEIGHTS:
        app = applicability.get(cat, "applicable")
        is_applicable = app != "not_applicable"
        if is_applicable:
            entry_max = category_score_floats[cat]["max"]
            entry_score = category_score_floats[cat]["score"]
        else:
            entry_max = 0.0
            entry_score = 0.0
        summary = _build_category_summary(
            category=cat,
            applicability=app,
            findings_in_cat=findings_by_cat.get(cat, []),
            deduction_total=deductions_by_cat.get(cat, 0.0),
            score=entry_score,
            max_score=entry_max,
        )
        # SDLC-066: optional LLM-narrated summary that overrides the
        # deterministic one. Returns None on any activation gate / API
        # failure, in which case we keep the deterministic summary.
        if use_llm_narrator:
            from sdlc_assessor.scorer.llm_narrator import DEFAULT_MODEL, narrate_category

            narrative = narrate_category(
                category=cat,
                applicability=app,
                findings_in_cat=findings_by_cat.get(cat, []),
                deduction_total=deductions_by_cat.get(cat, 0.0),
                score=entry_score,
                max_score=entry_max,
                model=llm_model or DEFAULT_MODEL,
                use_llm=True,
            )
            if narrative:
                summary = narrative
        category_scores.append(
            {
                "category": cat,
                "applicable": is_applicable,
                "score": int(round(entry_score)),
                "max_score": int(round(entry_max)),
                "summary": summary,
                "key_findings": _key_findings(findings_by_cat.get(cat, [])),
            }
        )

    blockers = detect_hard_blockers(findings, maturity_profile=maturity_profile, inventory=inventory)

    pass_threshold = use_case_profile.get("pass_threshold", 70)
    distinction_threshold = use_case_profile.get("distinction_threshold", 85)

    critical_blockers = [b for b in blockers if b.get("severity") == "critical"]
    has_critical = bool(critical_blockers)
    any_blockers = bool(blockers)

    if final_score_precise >= distinction_threshold and not any_blockers:
        verdict = "pass_with_distinction"
    elif final_score_precise >= pass_threshold and not has_critical:
        verdict = "pass"
    elif final_score_precise >= pass_threshold and has_critical or any_blockers:
        verdict = "conditional_pass"
    else:
        verdict = "fail"

    score_confidence = _compute_score_confidence(
        findings=findings,
        inventory=inventory,
        classification=evidence.get("classification", {}) or {},
    )

    scored = dict(evidence)
    scored["scoring"] = {
        "effective_profile": {
            "use_case": use_case,
            "maturity": maturity,
            "repo_type": repo_type,
            "merge_order": ["use_case", "maturity", "repo_type"],
            "policy_overrides_applied": bool(policy_overrides),
        },
        "base_weights": dict(BASE_WEIGHTS),
        "applied_weights": {cat: round(w, 4) for cat, w in weighted_max.items()},
        "category_scores": category_scores,
        "overall_score": int(round(final_score_precise)),
        "overall_score_precise": round(final_score_precise, 2),
        "applicable_max_score": 100,
        "verdict": verdict,
        "score_confidence": score_confidence,
        "blocker_impact": {
            "critical_count": sum(1 for b in blockers if b.get("severity") == "critical"),
            "high_count": sum(1 for b in blockers if b.get("severity") == "high"),
        },
        "flat_penalty_applied": int(round(flat_penalty)),
    }
    scored["hard_blockers"] = blockers

    if os.environ.get("SDLC_STRICT") == "1":
        from sdlc_assessor.core.schema import validate_evidence_full

        errors = validate_evidence_full(scored)
        if errors:
            joined = "\n".join(f"  - {e}" for e in errors)
            raise ValueError(f"SDLC_STRICT: scored evidence failed schema validation:\n{joined}")

    return scored


def _compute_score_confidence(
    *,
    findings: list[dict],
    inventory: dict,
    classification: dict,
) -> str:
    """Per docs/scoring_engine_spec.md §Recommended score confidence logic.

    Drives the ``score_confidence`` field in the scoring block (SDLC-027).
    """
    source_files = max(int(inventory.get("source_files", 0)), 1)
    evidence_density = len(findings) / source_files
    proxy_count = sum(1 for f in findings if f.get("confidence") == "medium")
    proxy_ratio = proxy_count / max(len(findings), 1)
    classification_confidence = float(classification.get("classification_confidence", 0.2))

    if (
        classification_confidence >= 0.7
        and proxy_ratio <= 0.3
        and evidence_density >= 0.1
    ):
        return "high"
    if classification_confidence <= 0.3 or proxy_ratio >= 0.7:
        return "low"
    return "medium"


__all__ = ["score_evidence", "BASE_WEIGHTS", "SEVERITY_WEIGHTS", "CONFIDENCE_MULTIPLIERS"]


# Suppress unused-import warning when SDLC_STRICT is off.
_ = Any
