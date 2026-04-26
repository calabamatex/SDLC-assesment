"""Bandit SAST adapter (SDLC-051).

Wraps `bandit -r <repo> -f json` and turns each ``results[]`` entry into a
:class:`SASTResult`. Bandit is a Python security linter — its output is
already organised by severity and confidence, so the mapping is direct.
"""

from __future__ import annotations

import json
from pathlib import Path

from sdlc_assessor.detectors.sast.framework import (
    SASTAdapter,
    SASTResult,
    register_adapter,
)

# Bandit severity tiers → our schema severity. Bandit ranks are HIGH/MEDIUM/LOW.
_BANDIT_SEVERITY = {
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
    "UNDEFINED": "info",
}

_BANDIT_CONFIDENCE = {
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
    "UNDEFINED": "low",
}


class BanditAdapter(SASTAdapter):
    tool_name = "bandit"
    ecosystems = ("python",)
    detector_source = "sast.bandit"

    def build_command(self, repo_path: Path) -> list[str]:
        return [
            self.tool_name,
            "-r",
            str(repo_path),
            "-f",
            "json",
            "--quiet",
            "--exclude",
            ",".join(
                [
                    ".venv",
                    "venv",
                    "node_modules",
                    "__pycache__",
                    "build",
                    "dist",
                    ".eggs",
                    "tests/fixtures",
                ]
            ),
        ]

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> list[SASTResult]:
        if not stdout.strip():
            return []
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return []
        results = data.get("results") or []
        out: list[SASTResult] = []
        for entry in results:
            severity = _BANDIT_SEVERITY.get(entry.get("issue_severity", "UNDEFINED"), "low")
            confidence = _BANDIT_CONFIDENCE.get(entry.get("issue_confidence", "UNDEFINED"), "medium")
            test_id = entry.get("test_id") or entry.get("test_name") or "BX000"
            out.append(
                SASTResult(
                    subcategory=f"bandit_{test_id}",
                    severity=severity,
                    category="security_posture",
                    statement=entry.get("issue_text", "Bandit issue."),
                    path=str(entry.get("filename", "unknown")),
                    line_start=entry.get("line_number"),
                    line_end=entry.get("line_range", [entry.get("line_number")])[-1] if entry.get("line_range") else entry.get("line_number"),
                    snippet=entry.get("code"),
                    rationale=entry.get("issue_text"),
                    confidence=confidence,
                    rule_id=entry.get("test_id"),
                    tags=[f"cwe:{entry.get('issue_cwe', {}).get('id', '?')}"] if entry.get("issue_cwe") else [],
                )
            )
        return out


register_adapter(BanditAdapter())


__all__ = ["BanditAdapter"]
