"""Python-specific detectors for Phase 3."""

from __future__ import annotations

from pathlib import Path


def run_python_detectors(repo_path: Path) -> list[dict]:
    findings: list[dict] = []

    for p in repo_path.rglob("*.py"):
        text = p.read_text(encoding="utf-8", errors="ignore")
        checks = [
            ("Any", "any_usage", "low", "`Any` type usage detected."),
            ("type: ignore", "type_ignore", "medium", "`type: ignore` usage detected."),
            ("except:\n", "bare_except", "high", "Bare except detected."),
            ("except Exception", "broad_except_exception", "medium", "Broad `except Exception` detected."),
            ("print(", "print_usage", "low", "`print` usage detected."),
            ("shell=True", "subprocess_shell_true", "high", "subprocess with shell=True detected."),
        ]
        for pattern, subcat, severity, statement in checks:
            if pattern in text:
                findings.append(
                    {
                        "category": "code_quality_contracts",
                        "subcategory": subcat,
                        "severity": severity,
                        "statement": statement,
                        "evidence": [{"path": str(p)}],
                        "confidence": "medium",
                        "applicability": "applicable",
                        "score_impact": {"magnitude_modifier": 0.8},
                        "detector_source": "python_pack",
                    }
                )

    return findings
