"""Python-specific detectors."""

from __future__ import annotations

import re
from pathlib import Path


def run_python_detectors(repo_path: Path) -> list[dict]:
    findings: list[dict] = []

    for p in repo_path.rglob("*.py"):
        text = p.read_text(encoding="utf-8", errors="ignore")

        checks = [
            (r"\bAny\b", "any_usage", "low", "`Any` type usage detected."),
            (r"type:\s*ignore", "type_ignore", "medium", "`type: ignore` usage detected."),
            (r"except\s*:\s*", "bare_except", "high", "Bare except detected."),
            (r"except\s+Exception", "broad_except_exception", "medium", "Broad `except Exception` detected."),
            (r"\bprint\(", "print_usage", "low", "`print` usage detected."),
            (r"subprocess\.[\w_]+\([^\)]*shell\s*=\s*True", "subprocess_shell_true", "high", "subprocess with shell=True detected."),
        ]

        for pattern, subcat, severity, statement in checks:
            if re.search(pattern, text):
                findings.append(
                    {
                        "category": "code_quality_contracts",
                        "subcategory": subcat,
                        "severity": severity,
                        "statement": statement,
                        "evidence": [{"path": str(p)}],
                        "confidence": "medium",
                        "applicability": "applicable",
                        "score_impact": {"direction": "negative", "magnitude": 3},
                        "detector_source": "python_pack",
                    }
                )

    return findings
