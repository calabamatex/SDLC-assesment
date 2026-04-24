"""TypeScript/JavaScript-specific detectors for Phase 3."""

from __future__ import annotations

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
            ("as any", "as_any", "medium", "`as any` detected."),
            ("console.", "console_usage", "low", "console.* usage detected."),
            ("catch {}", "empty_catch", "medium", "Empty catch block detected."),
            ("JSON.parse(", "json_parse", "medium", "JSON.parse usage detected."),
            ("exec(", "exec_usage", "high", "exec usage detected."),
            ("execSync(", "exec_sync_usage", "high", "execSync usage detected."),
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
                        "detector_source": "tsjs_pack",
                    }
                )

    tsconfig = repo_path / "tsconfig.json"
    if tsconfig.exists():
        content = tsconfig.read_text(encoding="utf-8", errors="ignore")
        if '"strict": true' not in content:
            findings.append(
                {
                    "category": "code_quality_contracts",
                    "subcategory": "missing_strict_mode",
                    "severity": "medium",
                    "statement": "TypeScript strict mode not enabled.",
                    "evidence": [{"path": str(tsconfig)}],
                    "confidence": "high",
                    "applicability": "applicable",
                    "score_impact": {"magnitude_modifier": 0.9},
                    "detector_source": "tsjs_pack",
                }
            )

    return findings
