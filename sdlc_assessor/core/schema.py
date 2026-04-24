"""Schema loading and lightweight evidence validation for phase 0."""

from __future__ import annotations

from pathlib import Path

from sdlc_assessor.core.io import read_json

REQUIRED_TOP_LEVEL_KEYS = {
    "repo_meta",
    "classification",
    "inventory",
    "findings",
    "scoring",
    "hard_blockers",
}


def load_evidence_schema(schema_path: str | Path = "docs/evidence_schema.json") -> dict:
    return read_json(schema_path)


def validate_evidence_top_level(evidence: dict) -> None:
    missing = REQUIRED_TOP_LEVEL_KEYS - set(evidence.keys())
    if missing:
        raise ValueError(f"Missing required evidence keys: {sorted(missing)}")
