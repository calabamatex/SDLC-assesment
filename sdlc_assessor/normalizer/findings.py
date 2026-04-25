"""Normalize raw detector findings into evidence finding records."""

from __future__ import annotations

SEVERITY_TO_MAGNITUDE = {
    "info": 1,
    "low": 2,
    "medium": 4,
    "high": 7,
    "critical": 10,
}


def severity_to_magnitude(severity: str) -> int:
    """Map a severity tier to an integer magnitude (0-10) per the schema."""
    return SEVERITY_TO_MAGNITUDE.get(severity, 4)


def build_score_impact(
    severity: str,
    *,
    direction: str = "negative",
    rationale: str | None = None,
) -> dict:
    """Construct a schema-conformant score_impact block from a severity.

    Returns ``{"direction", "magnitude", "rationale"}`` per
    ``docs/evidence_schema.json`` ``findings[].score_impact``.
    """
    impact: dict = {
        "direction": direction,
        "magnitude": severity_to_magnitude(severity),
    }
    if rationale:
        impact["rationale"] = rationale
    return impact


def normalize_findings(raw_findings: list[dict]) -> list[dict]:
    """Assign stable IDs and ensure every finding has a schema-conformant score_impact.

    Raw detector outputs can omit ``score_impact`` or supply only the legacy
    ``magnitude_modifier``; this function fills in the schema-required
    ``direction`` + integer ``magnitude`` from the finding's severity, while
    preserving any explicit ``rationale`` the detector supplied.
    """
    normalized: list[dict] = []
    for idx, f in enumerate(raw_findings, start=1):
        out = dict(f)
        out["id"] = f"F-{idx:04d}"

        existing = dict(out.get("score_impact", {}) or {})
        if "direction" not in existing or "magnitude" not in existing:
            severity = out.get("severity", "low")
            magnitude = existing.get("magnitude")
            if not isinstance(magnitude, int):
                magnitude = severity_to_magnitude(severity)
            existing["direction"] = existing.get("direction", "negative")
            existing["magnitude"] = magnitude
        # Drop the legacy magnitude_modifier — scorer reads magnitude/10.0 now.
        existing.pop("magnitude_modifier", None)
        out["score_impact"] = existing

        # Schema requires applicability on every finding; default to "applicable".
        out.setdefault("applicability", "applicable")
        normalized.append(out)
    return normalized
