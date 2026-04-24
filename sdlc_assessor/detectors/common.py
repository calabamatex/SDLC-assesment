"""Common cross-language detectors."""

from __future__ import annotations

import re
from pathlib import Path


def _all_files(repo_path: Path):
    for p in repo_path.rglob("*"):
        if p.is_file() and ".git" not in p.parts:
            yield p


def run_common_detectors(repo_path: Path) -> list[dict]:
    findings: list[dict] = []

    secret_pattern = re.compile(
        r"(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{8,}['\"]",
        re.IGNORECASE,
    )
    for p in _all_files(repo_path):
        text = p.read_text(encoding="utf-8", errors="ignore")
        if secret_pattern.search(text):
            findings.append(_finding("security_posture", "probable_secrets", "high", "Probable hardcoded secret detected.", p))

    for p in _all_files(repo_path):
        if p.stat().st_size > 100_000:
            findings.append(_finding("maintainability_operability", "large_files", "low", "Large file detected in repository.", p))

    artifact_ext = {".zip", ".jar", ".exe", ".dll", ".tar", ".gz", ".whl"}
    for p in _all_files(repo_path):
        if p.suffix.lower() in artifact_ext:
            findings.append(_finding("dependency_release_hygiene", "committed_artifacts", "medium", "Committed artifact detected.", p))

    if not (repo_path / ".github" / "workflows").exists():
        findings.append(_finding("testing_quality_gates", "missing_ci", "medium", "No CI workflows detected.", Path(".github/workflows")))

    if not (repo_path / "README.md").exists() and not (repo_path / "readme.md").exists():
        findings.append(_finding("documentation_truthfulness", "missing_readme", "medium", "README file is missing.", Path("README.md")))

    if not (repo_path / "SECURITY.md").exists():
        findings.append(_finding("security_posture", "missing_security_md", "low", "SECURITY.md file is missing.", Path("SECURITY.md")))

    return findings


def _finding(category: str, subcategory: str, severity: str, statement: str, path: Path) -> dict:
    return {
        "category": category,
        "subcategory": subcategory,
        "severity": severity,
        "statement": statement,
        "evidence": [{"path": str(path)}],
        "confidence": "medium",
        "applicability": "applicable",
        "score_impact": {"direction": "negative", "magnitude": 3},
        "detector_source": "common",
    }
