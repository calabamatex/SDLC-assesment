"""Hard blocker detection for phase 4."""

from __future__ import annotations


def detect_hard_blockers(findings: list[dict]) -> list[dict]:
    blockers: list[dict] = []
    for f in findings:
        subcat = f.get("subcategory", "")
        severity = f.get("severity", "")
        if subcat == "probable_secrets" or severity == "critical":
            blockers.append(
                {
                    "title": "Potential hard blocker",
                    "reason": f.get("statement", ""),
                    "finding_id": f.get("id", "unknown"),
                    "severity": severity or "high",
                }
            )
    return blockers
