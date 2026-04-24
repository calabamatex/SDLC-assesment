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


def test_scorer_outputs_schema_required_scoring_fields() -> None:
    evidence = {
        "repo_meta": {"name": "demo", "default_branch": "main", "analysis_timestamp": "2026-01-01T00:00:00Z"},
        "classification": {
            "repo_archetype": "service",
            "maturity_profile": "production",
            "deployment_surface": "networked",
            "classification_confidence": 0.9,
        },
        "inventory": {
            "source_files": 1,
            "source_loc": 5,
            "test_files": 1,
            "workflow_files": 1,
            "runtime_dependencies": 0,
            "dev_dependencies": 0,
        },
        "findings": [
            {
                "id": "F-1",
                "category": "security_posture",
                "subcategory": "probable_secrets",
                "severity": "high",
                "statement": "Probable hardcoded secret detected.",
                "confidence": "medium",
                "applicability": "applicable",
                "score_impact": {"direction": "negative", "magnitude": 5},
                "detector_source": "common",
                "evidence": [{"path": "app.py"}],
            }
        ],
        "scoring": {},
        "hard_blockers": [],
    }

    scored = score_evidence(evidence, "engineering_triage", "production", "service")
    scoring = scored["scoring"]
    assert {"base_weights", "applied_weights", "category_scores", "overall_score", "verdict"}.issubset(scoring.keys())
    assert isinstance(scoring["overall_score"], int)
    assert isinstance(scoring["category_scores"], list)
    assert len(scored["hard_blockers"]) >= 1
