"""Schema loading and full-payload validation for evidence/scored artifacts.

Resolution order for the evidence schema (SDLC-012):

1. ``importlib.resources`` package-local copy under ``sdlc_assessor/core/evidence_schema.json``
   — preferred so wheels and installed packages always have a schema available.
2. ``docs/evidence_schema.json`` at the repo root, used when running from the
   source tree where the package-local copy may be stale relative to docs.

A pre-commit / CI byte-equality check (``scripts/check_schema_sync.py``) keeps
the two copies in sync so the resolution order does not silently diverge.
"""

from __future__ import annotations

import warnings
from importlib import resources
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


def _package_schema_path() -> Path | None:
    """Return the package-local evidence_schema.json path if present."""
    try:
        ref = resources.files("sdlc_assessor.core").joinpath("evidence_schema.json")
    except (ModuleNotFoundError, FileNotFoundError):
        return None
    try:
        path = Path(str(ref))
    except (TypeError, ValueError):
        return None
    return path if path.exists() else None


def _docs_schema_path() -> Path | None:
    candidate = Path(__file__).resolve().parents[2] / "docs" / "evidence_schema.json"
    return candidate if candidate.exists() else None


def _default_schema_path() -> Path:
    """Resolve a default schema path with package-local preference (SDLC-012)."""
    pkg = _package_schema_path()
    if pkg is not None:
        return pkg
    docs = _docs_schema_path()
    if docs is not None:
        return docs
    raise FileNotFoundError(
        "evidence_schema.json not found in package-local or docs/ locations"
    )


def load_evidence_schema(schema_path: str | Path | None = None) -> dict:
    if schema_path is None:
        path: Path = _default_schema_path()
    else:
        path = Path(schema_path)
        if not path.is_absolute() and not path.exists():
            candidate = Path(__file__).resolve().parents[2] / path
            if candidate.exists():
                path = candidate
    return read_json(path)


def validate_evidence_top_level(evidence: dict) -> None:
    missing = REQUIRED_TOP_LEVEL_KEYS - set(evidence.keys())
    if missing:
        raise ValueError(f"Missing required evidence keys: {sorted(missing)}")


def validate_evidence_full(payload: dict, schema_path: str | Path | None = None) -> list[str]:
    """Validate ``payload`` against the evidence schema, return human-readable errors.

    Returns an empty list when the payload validates. When ``jsonschema`` is not
    installed, falls back to ``validate_evidence_top_level`` and emits a warning.

    SDLC-011: this function is what ``SDLC_STRICT=1`` calls at the end of
    ``score_evidence`` to fail loudly on schema-non-conformant output.
    """
    try:
        import jsonschema
    except ImportError:
        warnings.warn(
            "jsonschema not installed; falling back to top-level key check. "
            "Install the [dev] extra for full validation.",
            stacklevel=2,
        )
        try:
            validate_evidence_top_level(payload)
            return []
        except ValueError as exc:
            return [str(exc)]

    schema = load_evidence_schema(schema_path)
    validator = jsonschema.Draft202012Validator(schema)
    errors: list[str] = []
    for err in sorted(validator.iter_errors(payload), key=lambda e: e.absolute_path):
        path = "/".join(str(p) for p in err.absolute_path) or "<root>"
        errors.append(f"{path}: {err.message} [validator={err.validator}]")
    return errors
