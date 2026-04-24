"""Scoring engine implementing PLANS scoring formula."""

from __future__ import annotations

from collections import defaultdict

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

SEVERITY_WEIGHTS = {"info": 0, "low": 1, "medium": 2, "high": 4, "critical": 6}
CONFIDENCE_MULTIPLIERS = {"high": 1.0, "medium": 0.75, "low": 0.5}


def _resolve_applicability(maturity_profile: dict, repo_type_profile: dict) -> dict:
    result = dict(maturity_profile.get("category_applicability", {}))
    result.update(repo_type_profile.get("applicability_overrides", {}))
    return result


def score_evidence(
    evidence: dict,
    use_case: str,
    maturity: str,
    repo_type: str,
    policy_overrides: dict | None = None,
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

    deductions_by_cat = defaultdict(float)
    maturity_multiplier = float(maturity_profile.get("severity_multiplier", 1.0))

    for f in evidence.get("findings", []):
        cat = f.get("category")
        if cat not in normalized_max:
            continue

        score_impact = f.get("score_impact", {})
        direction = score_impact.get("direction", "negative")
        magnitude = float(score_impact.get("magnitude", 3))
        magnitude_modifier = max(0.0, min(10.0, magnitude)) / 10.0

        sev = SEVERITY_WEIGHTS.get(f.get("severity", "low"), 1)
        conf = CONFIDENCE_MULTIPLIERS.get(f.get("confidence", "medium"), 0.75)
        effective_delta = sev * conf * maturity_multiplier * magnitude_modifier

        if direction == "positive":
            deductions_by_cat[cat] -= effective_delta
        elif direction == "neutral":
            continue
        else:
            deductions_by_cat[cat] += effective_delta

    category_scores = []
    overall = 0.0
    for cat, max_points in normalized_max.items():
        score = max_points - deductions_by_cat[cat]
        score = max(0.0, min(max_points, score))
        overall += score
        category_scores.append(
            {
                "category": cat,
                "applicable": applicability.get(cat, "applicable") != "not_applicable",
                "score": int(round(score)),
                "max_score": int(round(max_points)),
                "summary": "Score derived from weighted evidence deductions/credits.",
                "key_findings": [f.get("id", "") for f in evidence.get("findings", []) if f.get("category") == cat][:5],
            }
        )

    overall_score = int(round(max(0.0, min(100.0, overall))))
    blockers = detect_hard_blockers(evidence.get("findings", []))

    pass_threshold = int(use_case_profile.get("pass_threshold", 70))
    distinction_threshold = int(use_case_profile.get("distinction_threshold", 85))

    if overall_score >= distinction_threshold and not blockers:
        verdict = "pass_with_distinction"
    elif overall_score >= pass_threshold and not blockers:
        verdict = "pass"
    elif overall_score >= pass_threshold:
        verdict = "conditional_pass"
    else:
        verdict = "fail"

    scored = dict(evidence)
    scored["scoring"] = {
        "base_weights": BASE_WEIGHTS,
        "applied_weights": {k: round(v, 4) for k, v in normalized_max.items()},
        "effective_profile": {
            "use_case": use_case,
            "maturity": maturity,
            "repo_type": repo_type,
            "merge_order": ["use_case", "maturity", "repo_type"],
            "policy_overrides_applied": bool(policy_overrides),
        },
        "category_scores": category_scores,
        "overall_score": overall_score,
        "verdict": verdict,
        "score_confidence": "medium",
    }
    scored["hard_blockers"] = blockers
    return scored
