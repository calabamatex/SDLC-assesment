"""Ruff SAST adapter (SDLC-052).

Ruff is primarily a fast Python linter, but its rule set covers a number of
SAST-grade categories: ``S`` (flake8-bandit), ``B`` (flake8-bugbear), ``E``
plus security-relevant subsets. We invoke ``ruff check . --output-format=json``
and map each diagnostic into a :class:`SASTResult`.

The ruff CLI exits non-zero when it finds issues — that's the expected
"signal present" outcome, not a failure. The framework tolerates that.
"""

from __future__ import annotations

import json
from pathlib import Path

from sdlc_assessor.detectors.sast.framework import (
    SASTAdapter,
    SASTResult,
    register_adapter,
)

# Ruff doesn't report severity per diagnostic; we infer severity from rule
# *prefix*. ``S`` (flake8-bandit) is security; ``B`` (bugbear) is real bugs;
# ``E`` is style. Anything else falls back to ``info``.
_RULE_PREFIX_SEVERITY = {
    "S": ("high", "security_posture"),
    "B": ("medium", "code_quality_contracts"),
    "E": ("low", "code_quality_contracts"),
    "F": ("medium", "code_quality_contracts"),  # pyflakes — undefined-name etc
    "UP": ("info", "code_quality_contracts"),
    "I": ("info", "code_quality_contracts"),
    "SIM": ("info", "code_quality_contracts"),
}


def _classify(code: str) -> tuple[str, str]:
    # Codes look like "S101", "B007", "E501". Prefix is the alphabetic head.
    prefix = ""
    for ch in code:
        if ch.isalpha():
            prefix += ch
        else:
            break
    return _RULE_PREFIX_SEVERITY.get(prefix, ("info", "code_quality_contracts"))


class RuffAdapter(SASTAdapter):
    tool_name = "ruff"
    ecosystems = ("python",)
    detector_source = "sast.ruff"

    def build_command(self, repo_path: Path) -> list[str]:
        return [
            self.tool_name,
            "check",
            str(repo_path),
            "--output-format=json",
            "--exit-zero",  # never raise on findings; we only care about JSON
            "--no-cache",   # avoid cross-run cache surprises in CI
            "--exclude",
            "tests/fixtures",
        ]

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> list[SASTResult]:
        if not stdout.strip():
            return []
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list):
            return []
        out: list[SASTResult] = []
        for entry in data:
            code = entry.get("code") or "X000"
            severity, category = _classify(code)
            location = entry.get("location") or {}
            end_location = entry.get("end_location") or {}
            line = location.get("row") if isinstance(location.get("row"), int) else None
            line_end = end_location.get("row") if isinstance(end_location.get("row"), int) else line
            out.append(
                SASTResult(
                    subcategory=f"ruff_{code}",
                    severity=severity,
                    category=category,
                    statement=entry.get("message", "Ruff diagnostic."),
                    path=str(entry.get("filename", "unknown")),
                    line_start=line,
                    line_end=line_end,
                    rationale=entry.get("message"),
                    confidence="high",
                    rule_id=code,
                    tags=[f"ruff:{code}"],
                )
            )
        return out


register_adapter(RuffAdapter())


__all__ = ["RuffAdapter"]
