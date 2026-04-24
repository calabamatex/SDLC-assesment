from sdlc_assessor.scorer.blockers import detect_hard_blockers
from sdlc_assessor.scorer.engine import score_evidence


def test_blockers_detect_probable_secret() -> None:
    findings = [
        {
            "id": "F-1",
            "subcategory": "probable_secrets",
            "severity": "high",
            "statement": "Probable hardcoded secret detected.",
        }
    ]
    blockers = detect_hard_blockers(findings)
    assert len(blockers) == 1


def test_scorer_outputs_scoring_and_verdict() -> None:
    evidence = {
        "repo_meta": {},
        "classification": {},
        "inventory": {},
        "findings": [
            {
                "id": "F-1",
                "category": "security_posture",
                "subcategory": "probable_secrets",
                "severity": "high",
                "statement": "Probable hardcoded secret detected.",
                "confidence": "medium",
                "score_impact": {"magnitude_modifier": 1.0},
            }
        ],
        "scoring": {},
        "hard_blockers": [],
    }

    scored = score_evidence(evidence, "engineering_triage", "production", "service")
    assert "scoring" in scored
    assert "overall_score" in scored["scoring"]
    assert scored["scoring"]["verdict"] in {
        "pass_with_distinction",
        "pass",
        "conditional_pass",
        "fail",
    }
    assert len(scored["hard_blockers"]) >= 1
