"""ESLint SAST adapter (SDLC-053).

Wraps ``eslint . --format=json`` for JS/TS/JSX/TSX repos. ESLint emits an
array of file objects, each with a ``messages`` list. Each message becomes
a :class:`SASTResult`.

ESLint requires its own config in the target repo (``eslint.config.js``,
``.eslintrc*``, or ``"eslintConfig"`` in package.json). When no config is
present ESLint exits with code 2 and an error message; the adapter
gracefully returns no findings rather than treating that as a real failure.
"""

from __future__ import annotations

import json
from pathlib import Path

from sdlc_assessor.detectors.sast.framework import (
    SASTAdapter,
    SASTResult,
    register_adapter,
)

# ESLint severities: 0 off, 1 warn, 2 error.
_ESLINT_SEVERITY = {
    0: "info",
    1: "low",
    2: "medium",
}

ESLINT_CONFIG_FILES = (
    "eslint.config.js",
    "eslint.config.mjs",
    "eslint.config.cjs",
    ".eslintrc",
    ".eslintrc.js",
    ".eslintrc.cjs",
    ".eslintrc.json",
    ".eslintrc.yml",
    ".eslintrc.yaml",
)


class ESLintAdapter(SASTAdapter):
    tool_name = "eslint"
    ecosystems = ("javascript", "typescript")
    detector_source = "sast.eslint"

    def should_run(self, repo_path: Path) -> bool:
        if not super().should_run(repo_path):
            return False
        # Only run when the repo has an ESLint config — otherwise eslint
        # emits "no config" errors, not findings.
        if any((repo_path / candidate).exists() for candidate in ESLINT_CONFIG_FILES):
            return True
        package_json = repo_path / "package.json"
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return False
            return "eslintConfig" in data
        return False

    def build_command(self, repo_path: Path) -> list[str]:
        return [
            self.tool_name,
            ".",
            "--format=json",
            "--no-error-on-unmatched-pattern",
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
        for file_entry in data:
            file_path = file_entry.get("filePath", "unknown")
            for msg in file_entry.get("messages", []) or []:
                rule_id = msg.get("ruleId") or "EX000"
                severity = _ESLINT_SEVERITY.get(msg.get("severity"), "low")
                category = (
                    "security_posture"
                    if any(token in rule_id for token in ("security", "no-eval", "no-implied-eval", "no-new-func"))
                    else "code_quality_contracts"
                )
                out.append(
                    SASTResult(
                        subcategory=f"eslint_{rule_id.replace('/', '_')}",
                        severity=severity,
                        category=category,
                        statement=msg.get("message", "ESLint diagnostic."),
                        path=str(file_path),
                        line_start=msg.get("line"),
                        line_end=msg.get("endLine") or msg.get("line"),
                        rationale=msg.get("message"),
                        confidence="high",
                        rule_id=rule_id,
                        tags=[f"eslint:{rule_id}"],
                    )
                )
        return out


register_adapter(ESLintAdapter())


__all__ = ["ESLintAdapter", "ESLINT_CONFIG_FILES"]
