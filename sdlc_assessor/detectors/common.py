"""Common cross-language detectors for Phase 3."""

from __future__ import annotations

import re
from pathlib import Path


def _all_files(repo_path: Path):
    for p in repo_path.rglob("*"):
        if p.is_file() and ".git" not in p.parts:
            yield p


def run_common_detectors(repo_path: Path) -> list[dict]:
    findings: list[dict] = []

    # probable secrets
    secret_pattern = re.compile(r"(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE)
    for p in _all_files(repo_path):
        text = p.read_text(encoding="utf-8", errors="ignore")
        if secret_pattern.search(text):
            findings.append(
                {
                    "category": "security_posture",
                    "subcategory": "probable_secrets",
                    "severity": "high",
                    "statement": "Probable hardcoded secret detected.",
                    "evidence": [{"path": str(p)}],
                    "confidence": "medium",
                    "applicability": "applicable",
                    "score_impact": {"magnitude_modifier": 1.0},
                    "detector_source": "common.probable_secrets",
                }
            )

    # large files
    for p in _all_files(repo_path):
        if p.stat().st_size > 100_000:
            findings.append(
                {
                    "category": "maintainability_operability",
                    "subcategory": "large_files",
                    "severity": "low",
                    "statement": "Large file detected in repository.",
                    "evidence": [{"path": str(p), "bytes": p.stat().st_size}],
                    "confidence": "high",
                    "applicability": "applicable",
                    "score_impact": {"magnitude_modifier": 0.5},
                    "detector_source": "common.large_files",
                }
            )

    # committed artifacts
    artifact_ext = {".zip", ".jar", ".exe", ".dll", ".tar", ".gz"}
    for p in _all_files(repo_path):
        if p.suffix.lower() in artifact_ext:
            findings.append(
                {
                    "category": "dependency_release_hygiene",
                    "subcategory": "committed_artifacts",
                    "severity": "medium",
                    "statement": "Committed binary/archive artifact detected.",
                    "evidence": [{"path": str(p)}],
                    "confidence": "high",
                    "applicability": "applicable",
                    "score_impact": {"magnitude_modifier": 0.8},
                    "detector_source": "common.committed_artifacts",
                }
            )

    # missing CI
    if not (repo_path / ".github" / "workflows").exists():
        findings.append(
            {
                "category": "testing_quality_gates",
                "subcategory": "missing_ci",
                "severity": "medium",
                "statement": "No CI workflows detected.",
                "evidence": [{"path": ".github/workflows"}],
                "confidence": "high",
                "applicability": "applicable",
                "score_impact": {"magnitude_modifier": 1.0},
                "detector_source": "common.missing_ci",
            }
        )

    # missing README
    if not (repo_path / "README.md").exists() and not (repo_path / "readme.md").exists():
        findings.append(
            {
                "category": "documentation_truthfulness",
                "subcategory": "missing_readme",
                "severity": "medium",
                "statement": "README file is missing.",
                "evidence": [{"path": "README.md"}],
                "confidence": "high",
                "applicability": "applicable",
                "score_impact": {"magnitude_modifier": 0.9},
                "detector_source": "common.missing_readme",
            }
        )

    # missing SECURITY.md
    if not (repo_path / "SECURITY.md").exists():
        findings.append(
            {
                "category": "security_posture",
                "subcategory": "missing_security_md",
                "severity": "low",
                "statement": "SECURITY.md file is missing.",
                "evidence": [{"path": "SECURITY.md"}],
                "confidence": "high",
                "applicability": "applicable",
                "score_impact": {"magnitude_modifier": 0.5},
                "detector_source": "common.missing_security_md",
            }
        )

    return findings
