import os
from pathlib import Path

from sdlc_assessor.core.schema import (
    load_evidence_schema,
    validate_evidence_full,
    validate_evidence_top_level,
)


def test_core_can_load_docs_schema() -> None:
    schema = load_evidence_schema()
    assert schema["title"] == "SDLC Framework v2 Evidence Schema"


def test_core_can_load_schema_from_relative_docs_path_outside_cwd(tmp_path) -> None:
    original = os.getcwd()
    try:
        os.chdir(tmp_path)
        schema = load_evidence_schema("docs/evidence_schema.json")
        assert schema["title"] == "SDLC Framework v2 Evidence Schema"
    finally:
        os.chdir(original)


def test_core_can_load_schema_from_default_when_cwd_is_elsewhere(tmp_path) -> None:
    original = os.getcwd()
    try:
        os.chdir(tmp_path)
        schema = load_evidence_schema()
        assert schema["title"] == "SDLC Framework v2 Evidence Schema"
    finally:
        os.chdir(original)


def test_core_validate_evidence_top_level_passes() -> None:
    evidence = {
        "repo_meta": {},
        "classification": {},
        "inventory": {},
        "findings": [],
        "scoring": {},
        "hard_blockers": [],
    }
    validate_evidence_top_level(evidence)


def test_core_validate_evidence_top_level_fails_on_missing() -> None:
    evidence = {
        "repo_meta": {},
        "classification": {},
    }
    try:
        validate_evidence_top_level(evidence)
    except ValueError as exc:
        assert "Missing required evidence keys" in str(exc)
    else:
        raise AssertionError("Expected validation failure")


def test_validate_evidence_full_passes_on_pipeline_output(tmp_path: Path) -> None:
    from sdlc_assessor.classifier.engine import classify_repo
    from sdlc_assessor.collector.engine import collect_evidence
    from sdlc_assessor.core.io import write_json
    from sdlc_assessor.scorer.engine import score_evidence

    payload = classify_repo("tests/fixtures/fixture_python_basic")
    classification_path = tmp_path / "classification.json"
    write_json(classification_path, payload)
    evidence = collect_evidence("tests/fixtures/fixture_python_basic", str(classification_path))
    scored = score_evidence(evidence, "engineering_triage", "prototype", "cli")
    errors = validate_evidence_full(scored)
    assert errors == [], f"unexpected validation errors: {errors}"


def test_validate_evidence_full_returns_errors_on_invalid_payload() -> None:
    invalid = {
        "repo_meta": {},  # missing required name/default_branch/analysis_timestamp
        "classification": {},
        "inventory": {},
        "findings": "not-a-list",
        "scoring": {},
        "hard_blockers": [],
    }
    errors = validate_evidence_full(invalid)
    assert errors, "expected at least one schema error"
    joined = "\n".join(errors)
    assert "findings" in joined or "scoring" in joined or "repo_meta" in joined


def test_package_local_schema_load_succeeds_when_docs_unavailable(tmp_path: Path, monkeypatch) -> None:
    """SDLC-012: package-local schema is preferred over docs/."""
    import sdlc_assessor.core.schema as schema_mod

    monkeypatch.setattr(schema_mod, "_docs_schema_path", lambda: None)
    schema = load_evidence_schema()
    assert schema["title"] == "SDLC Framework v2 Evidence Schema"
