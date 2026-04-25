"""Validate full pipeline outputs against docs/evidence_schema.json.

This test was added in SDLC-007. It is expected to FAIL initially against the
v0.1 implementation (16 schema violations per ANALYSIS.md §4.1). Tasks
SDLC-008..012 turn it green.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sdlc_assessor.classifier.engine import classify_repo
from sdlc_assessor.collector.engine import collect_evidence
from sdlc_assessor.core.io import write_json
from sdlc_assessor.core.schema import load_evidence_schema
from sdlc_assessor.scorer.engine import score_evidence

FIXTURES = [
    "fixture_empty_repo",
    "fixture_python_basic",
    "fixture_probable_secret",
    "fixture_typescript_basic",
]


def _format_errors(errors: list) -> str:
    lines = []
    for err in errors:
        path = "/".join(str(p) for p in err.absolute_path) or "<root>"
        lines.append(f"  - {path}: {err.message} [validator={err.validator}]")
    return "\n".join(lines) if lines else "<none>"


def _run_pipeline(fixture: str, tmp_path: Path) -> tuple[dict, dict]:
    """Run classify → collect → score against a fixture, return (evidence, scored)."""
    repo_path = Path("tests/fixtures") / fixture
    classification = classify_repo(str(repo_path))
    classification_path = tmp_path / "classification.json"
    write_json(classification_path, classification)

    evidence = collect_evidence(str(repo_path), str(classification_path))
    write_json(tmp_path / "evidence.json", evidence)

    scored = score_evidence(evidence, "engineering_triage", "prototype", "cli")
    write_json(tmp_path / "scored.json", scored)
    return evidence, scored


@pytest.mark.parametrize("fixture", FIXTURES)
def test_scored_json_is_schema_conformant(fixture: str, tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = load_evidence_schema()
    _evidence, scored = _run_pipeline(fixture, tmp_path)
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(scored), key=lambda e: e.absolute_path)
    assert errors == [], (
        f"scored.json for {fixture} failed schema validation:\n{_format_errors(errors)}"
    )


@pytest.mark.parametrize("fixture", FIXTURES)
def test_findings_have_direction_and_magnitude(fixture: str, tmp_path: Path) -> None:
    """Every finding's score_impact must include direction and magnitude per schema."""
    evidence, _scored = _run_pipeline(fixture, tmp_path)
    for f in evidence.get("findings", []):
        si = f.get("score_impact", {})
        assert "direction" in si, f"finding {f.get('id')} missing score_impact.direction"
        assert "magnitude" in si, f"finding {f.get('id')} missing score_impact.magnitude"
        assert si["direction"] in {"positive", "negative", "neutral"}
        assert isinstance(si["magnitude"], int)
        assert 0 <= si["magnitude"] <= 10


@pytest.mark.parametrize("fixture", FIXTURES)
def test_scoring_block_has_required_keys(fixture: str, tmp_path: Path) -> None:
    _evidence, scored = _run_pipeline(fixture, tmp_path)
    scoring = scored.get("scoring", {})
    for required_key in ("base_weights", "applied_weights", "category_scores", "overall_score", "verdict"):
        assert required_key in scoring, f"scoring missing required key '{required_key}'"
    assert isinstance(scoring["category_scores"], list), (
        "scoring.category_scores must be a list per schema"
    )
    assert isinstance(scoring["overall_score"], int), (
        "scoring.overall_score must be an integer per schema"
    )


@pytest.mark.parametrize("fixture", FIXTURES)
def test_each_category_score_has_required_keys(fixture: str, tmp_path: Path) -> None:
    _evidence, scored = _run_pipeline(fixture, tmp_path)
    for entry in scored.get("scoring", {}).get("category_scores", []):
        for required_key in ("category", "applicable", "score", "max_score", "summary"):
            assert required_key in entry, (
                f"category_scores entry missing '{required_key}': {entry}"
            )
        assert isinstance(entry["applicable"], bool)
        assert isinstance(entry["score"], int)
        assert isinstance(entry["max_score"], int)
        assert isinstance(entry["summary"], str)
        assert entry["summary"], "summary must be non-empty"


def test_schema_loads_from_default_path() -> None:
    schema = load_evidence_schema()
    assert isinstance(schema, dict)
    assert schema.get("title") == "SDLC Framework v2 Evidence Schema"
