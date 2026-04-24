"""TypeScript/JavaScript-specific detectors."""

from __future__ import annotations

import re
from pathlib import Path


TSJS_GLOBS = ["*.ts", "*.tsx", "*.js", "*.jsx"]


def _iter_tsjs(repo_path: Path):
    for pattern in TSJS_GLOBS:
        for p in repo_path.rglob(pattern):
            yield p


def run_tsjs_detectors(repo_path: Path) -> list[dict]:
    findings: list[dict] = []

    for p in _iter_tsjs(repo_path):
        text = p.read_text(encoding="utf-8", errors="ignore")

        checks = [
            (r"as\s+any", "as_any", "medium", "`as any` detected."),
            (r"console\.[a-zA-Z_]+\(", "console_usage", "low", "console.* usage detected."),
            (r"catch\s*\(?.*?\)?\s*\{\s*\}", "empty_catch", "medium", "Empty catch block detected."),
            (r"JSON\.parse\(", "json_parse", "medium", "JSON.parse usage detected."),
            (r"\bexec\(", "exec_usage", "high", "exec usage detected."),
            (r"\bexecSync\(", "exec_sync_usage", "high", "execSync usage detected."),
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
                        "detector_source": "tsjs_pack",
                    }
                )

    tsconfig = repo_path / "tsconfig.json"
    if not tsconfig.exists() or '"strict": true' not in tsconfig.read_text(encoding="utf-8", errors="ignore"):
        findings.append(
            {
                "category": "code_quality_contracts",
                "subcategory": "missing_strict_mode",
                "severity": "medium",
                "statement": "TypeScript strict mode not enabled.",
                "evidence": [{"path": str(tsconfig if tsconfig.exists() else Path('tsconfig.json'))}],
                "confidence": "high",
                "applicability": "applicable",
                "score_impact": {"direction": "negative", "magnitude": 3},
                "detector_source": "tsjs_pack",
            }
        )

    return findings
