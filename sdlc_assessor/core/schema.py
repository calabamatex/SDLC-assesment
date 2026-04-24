"""Evidence schema loading and validation."""

from __future__ import annotations

from pathlib import Path

from sdlc_assessor.core.io import read_json

try:
    from jsonschema import Draft202012Validator  # type: ignore
except Exception:  # pragma: no cover
    Draft202012Validator = None


REQUIRED_TOP = {"repo_meta", "classification", "inventory", "findings", "scoring", "hard_blockers"}
REQUIRED_SCORING = {"base_weights", "applied_weights", "category_scores", "overall_score", "verdict"}


def load_evidence_schema(schema_path: str | Path = "docs/evidence_schema.json") -> dict:
    return read_json(schema_path)


def _fallback_validate(evidence: dict) -> None:
    missing = REQUIRED_TOP - set(evidence.keys())
    if missing:
        raise ValueError(f"Schema validation failed at <root>: missing keys {sorted(missing)}")

    scoring = evidence.get("scoring", {})
    if not isinstance(scoring, dict):
        raise ValueError("Schema validation failed at scoring: must be object")
    missing_scoring = REQUIRED_SCORING - set(scoring.keys())
    if missing_scoring:
        raise ValueError(f"Schema validation failed at scoring: missing keys {sorted(missing_scoring)}")


def validate_evidence_top_level(evidence: dict, schema_path: str | Path = "docs/evidence_schema.json") -> None:
    if Draft202012Validator is None:
        _fallback_validate(evidence)
        return

    schema = load_evidence_schema(schema_path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(evidence), key=lambda e: e.path)
    if errors:
        first = errors[0]
        path = ".".join(str(x) for x in first.path)
        where = path or "<root>"
        raise ValueError(f"Schema validation failed at {where}: {first.message}")
