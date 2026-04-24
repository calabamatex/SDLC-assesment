"""Normalize raw detector findings into evidence finding records."""

from __future__ import annotations


def normalize_findings(raw_findings: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for idx, f in enumerate(raw_findings, start=1):
        out = dict(f)
        out["id"] = f"F-{idx:04d}"
        normalized.append(out)
    return normalized
