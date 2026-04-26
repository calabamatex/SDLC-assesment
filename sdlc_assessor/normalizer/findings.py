"""Normalize raw detector findings into evidence finding records."""

from __future__ import annotations

SEVERITY_TO_MAGNITUDE = {
    "info": 1,
    "low": 2,
    "medium": 4,
    "high": 7,
    "critical": 10,
}

# Path-class tagging (SDLC-067): findings whose evidence path falls under one
# of these directory roots are tagged so reports can segregate them from
# production-source findings. Tag value lands on ``finding["tags"]`` as
# ``"source:<class>"``.
_PATH_CLASSES: tuple[tuple[str, str], ...] = (
    ("tests/fixtures/", "test_fixture"),
    ("tests/fixture/", "test_fixture"),
    ("fixtures/", "test_fixture"),
    ("test_fixtures/", "test_fixture"),
    ("examples/", "example"),
    ("example/", "example"),
    ("samples/", "example"),
    ("demos/", "example"),
    ("benchmark/", "benchmark"),
    ("benchmarks/", "benchmark"),
    ("vendor/", "vendor"),
    ("third_party/", "vendor"),
    ("third-party/", "vendor"),
    ("docs/", "docs"),
    ("doc/", "docs"),
)


def classify_path(path: str | None) -> str | None:
    """Return the path-class for ``path`` or ``None`` if it's production source.

    The match is greedy: any path component matching one of the
    ``_PATH_CLASSES`` prefixes wins. Comparison is case-sensitive on
    POSIX-normalized paths (forward slashes).
    """
    if not path:
        return None
    normalized = path.replace("\\", "/").lstrip("./")
    for prefix, label in _PATH_CLASSES:
        if normalized.startswith(prefix) or f"/{prefix}" in f"/{normalized}":
            return label
    return None


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

    SDLC-067 (v0.9.0): also classifies the finding's primary evidence path
    and adds a ``source:<class>`` tag (e.g. ``source:test_fixture``,
    ``source:vendor``) when the path matches a non-production root. Findings
    in production source remain untagged so consumers can default to
    "production-only" views without explicit filtering.
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

        # SDLC-067: path-class tag on the primary evidence path.
        evidence = out.get("evidence") or [{}]
        primary_path = evidence[0].get("path") if evidence else None
        path_class = classify_path(primary_path)
        if path_class:
            tags = list(out.get("tags") or [])
            tag = f"source:{path_class}"
            if tag not in tags:
                tags.append(tag)
            out["tags"] = tags

        normalized.append(out)
    return normalized


def is_fixture_finding(finding: dict) -> bool:
    """Return True when ``finding`` was tagged as fixture/example/benchmark/vendor source."""
    tags = finding.get("tags") or []
    return any(
        isinstance(t, str)
        and t.startswith("source:")
        and t.split(":", 1)[1] in {"test_fixture", "example", "benchmark", "vendor"}
        for t in tags
    )


def production_findings(findings: list[dict]) -> list[dict]:
    """Return only findings that aren't fixture/example/benchmark/vendor-derived."""
    return [f for f in findings if not is_fixture_finding(f)]


def fixture_findings(findings: list[dict]) -> list[dict]:
    """Return only findings tagged as fixture/example/benchmark/vendor-derived."""
    return [f for f in findings if is_fixture_finding(f)]


__all__ = [
    "SEVERITY_TO_MAGNITUDE",
    "build_score_impact",
    "classify_path",
    "fixture_findings",
    "is_fixture_finding",
    "normalize_findings",
    "production_findings",
    "severity_to_magnitude",
]
