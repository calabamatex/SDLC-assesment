"""Semgrep SAST adapter (SDLC-054).

Multi-language pattern matcher. We invoke ``semgrep --json --config=auto
--metrics=off``. ``--config=auto`` pulls Semgrep's curated registry rule
sets matching the repo's languages; ``--metrics=off`` keeps the run
offline-stable (no network telemetry).

Each result row in semgrep's output has its own severity (INFO / WARNING /
ERROR) plus a rule ID. The adapter maps these to our schema.
"""

from __future__ import annotations

import json
from pathlib import Path

from sdlc_assessor.detectors.sast.framework import (
    SASTAdapter,
    SASTResult,
    register_adapter,
)

_SEMGREP_SEVERITY = {
    "ERROR": "high",
    "WARNING": "medium",
    "INFO": "low",
}


class SemgrepAdapter(SASTAdapter):
    tool_name = "semgrep"
    ecosystems = ("python", "javascript", "typescript", "go", "rust", "java", "csharp")
    detector_source = "sast.semgrep"
    timeout_seconds = 180  # semgrep is the slowest of the four; allow more

    def build_command(self, repo_path: Path) -> list[str]:
        return [
            self.tool_name,
            "scan",
            "--json",
            "--config=auto",
            "--metrics=off",
            "--quiet",
            "--exclude=tests/fixtures",
            "--exclude=node_modules",
            "--exclude=.venv",
            str(repo_path),
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
            extra = entry.get("extra") or {}
            severity_raw = extra.get("severity", "INFO")
            severity = _SEMGREP_SEVERITY.get(severity_raw, "low")
            rule_id = entry.get("check_id") or "semgrep_rule"
            metadata = extra.get("metadata") or {}
            category = "security_posture" if "security" in metadata.get("category", "").lower() else "code_quality_contracts"
            start = entry.get("start") or {}
            end = entry.get("end") or {}
            short_id = rule_id.split(".")[-1] if "." in rule_id else rule_id
            out.append(
                SASTResult(
                    subcategory=f"semgrep_{short_id[:60]}",
                    severity=severity,
                    category=category,
                    statement=extra.get("message", "Semgrep finding."),
                    path=str(entry.get("path", "unknown")),
                    line_start=start.get("line") if isinstance(start.get("line"), int) else None,
                    line_end=end.get("line") if isinstance(end.get("line"), int) else None,
                    snippet=extra.get("lines"),
                    rationale=extra.get("message"),
                    confidence="high",
                    rule_id=rule_id,
                    tags=[f"semgrep:{rule_id}"],
                )
            )
        return out


register_adapter(SemgrepAdapter())


__all__ = ["SemgrepAdapter"]
