from sdlc_assessor.core.schema import load_evidence_schema, validate_evidence_top_level


def _valid_scored_evidence() -> dict:
    return {
        "repo_meta": {
            "name": "demo",
            "default_branch": "main",
            "analysis_timestamp": "2026-01-01T00:00:00Z",
        },
        "classification": {
            "repo_archetype": "unknown",
            "maturity_profile": "unknown",
            "deployment_surface": "unknown",
            "classification_confidence": 0.5,
        },
        "inventory": {
            "source_files": 0,
            "source_loc": 0,
            "test_files": 0,
            "workflow_files": 0,
            "runtime_dependencies": 0,
            "dev_dependencies": 0,
        },
        "findings": [],
        "scoring": {
            "base_weights": {},
            "applied_weights": {},
            "category_scores": [],
            "overall_score": 0,
            "verdict": "fail",
        },
        "hard_blockers": [],
    }


def test_core_can_load_docs_schema() -> None:
    schema = load_evidence_schema()
    assert schema["title"] == "SDLC Framework v2 Evidence Schema"


def test_core_validate_evidence_top_level_passes() -> None:
    validate_evidence_top_level(_valid_scored_evidence())


def test_core_validate_evidence_top_level_fails_on_missing() -> None:
    evidence = {
        "repo_meta": {},
        "classification": {},
    }
    try:
        validate_evidence_top_level(evidence)
    except ValueError as exc:
        assert "Schema validation failed" in str(exc)
    else:
        raise AssertionError("Expected validation failure")
