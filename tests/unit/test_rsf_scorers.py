"""Tests for RSF v1.0 per-criterion scorers.

These verify the discipline rule: score 0 only when absence is observable;
score `?` when evidence the criterion needs is not collected; never invent
a score from incomplete evidence.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sdlc_assessor.rsf.aggregate import NOT_APPLICABLE, UNVERIFIED
from sdlc_assessor.rsf.scorers import (
    score_all,
    score_d1_1,
    score_d1_2,
    score_d2_1,
    score_d2_2,
    score_d2_3,
    score_d3_1,
    score_d3_2,
    score_d3_4,
    score_d5_4,
    score_d6_1,
    score_d6_2,
    score_d6_3,
    score_d6_4,
    score_d7_1,
)


@pytest.fixture
def empty_scored() -> dict:
    return {
        "inventory": {},
        "findings": [],
        "classification": {},
        "repo_meta": {"git_summary": {}},
    }


def _write(repo: Path, rel: str, content: str = "x") -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


# ---------------------------------------------------------------------------
# D1
# ---------------------------------------------------------------------------


def test_d1_1_no_tests_scores_zero(tmp_path: Path, empty_scored: dict) -> None:
    empty_scored["inventory"] = {"test_files": 0, "workflow_files": 0}
    result = score_d1_1(empty_scored, tmp_path)
    assert result.value == 0
    assert "No automated tests" in result.rationale


def test_d1_1_tests_no_ci_scores_one(tmp_path: Path, empty_scored: dict) -> None:
    empty_scored["inventory"] = {"test_files": 5, "workflow_files": 0}
    result = score_d1_1(empty_scored, tmp_path)
    assert result.value == 1
    assert "not run in CI" in result.rationale


def test_d1_1_tests_with_ci_unverified(tmp_path: Path, empty_scored: dict) -> None:
    """Coverage % is unobservable; level 2+ requires it; ?."""
    empty_scored["inventory"] = {"test_files": 5, "workflow_files": 1}
    result = score_d1_1(empty_scored, tmp_path)
    assert result.value == UNVERIFIED


def test_d1_2_no_workflows_scores_zero(tmp_path: Path, empty_scored: dict) -> None:
    result = score_d1_2(empty_scored, tmp_path)
    assert result.value == 0


def test_d1_2_workflows_with_sast_unverified(tmp_path: Path, empty_scored: dict) -> None:
    _write(tmp_path, ".github/workflows/ci.yml", "uses: actions/setup-python@v5\nrun: ruff check .")
    result = score_d1_2(empty_scored, tmp_path)
    assert result.value == UNVERIFIED
    assert "ci.yml" in str(result.evidence)


# ---------------------------------------------------------------------------
# D2
# ---------------------------------------------------------------------------


def test_d2_1_no_dependabot_unverified_not_zero(tmp_path: Path, empty_scored: dict) -> None:
    """RSF level 0 requires affirmative CVE evidence; we don't run a scan, so ?."""
    result = score_d2_1(empty_scored, tmp_path)
    assert result.value == UNVERIFIED
    assert "unverified" in result.rationale.lower()


def test_d2_1_dependabot_present_unverified(tmp_path: Path, empty_scored: dict) -> None:
    _write(tmp_path, ".github/dependabot.yml", "version: 2")
    result = score_d2_1(empty_scored, tmp_path)
    assert result.value == UNVERIFIED
    assert any("dependabot" in e for e in result.evidence)


def test_d2_2_secrets_no_scanning_scores_zero(tmp_path: Path, empty_scored: dict) -> None:
    empty_scored["findings"] = [
        {"id": "F-1", "subcategory": "probable_secrets", "severity": "high"}
    ]
    result = score_d2_2(empty_scored, tmp_path)
    assert result.value == 0


def test_d2_2_secrets_with_scanning_scores_one(tmp_path: Path, empty_scored: dict) -> None:
    empty_scored["findings"] = [{"id": "F-1", "subcategory": "probable_secrets"}]
    _write(tmp_path, ".gitleaks.toml", "[allowlist]")
    result = score_d2_2(empty_scored, tmp_path)
    assert result.value == 1


def test_d2_2_no_secrets_no_scanning_unverified(tmp_path: Path, empty_scored: dict) -> None:
    result = score_d2_2(empty_scored, tmp_path)
    assert result.value == UNVERIFIED


def test_d2_3_top_ten_patterns_score_zero(tmp_path: Path, empty_scored: dict) -> None:
    empty_scored["findings"] = [
        {"id": "F-1", "subcategory": "probable_secrets", "severity": "high"},
        {"id": "F-2", "subcategory": "subprocess_shell_true", "severity": "high"},
    ]
    result = score_d2_3(empty_scored, tmp_path)
    assert result.value == 0
    assert "Top 10" in result.rationale


def test_d2_3_no_top_ten_findings_unverified(tmp_path: Path, empty_scored: dict) -> None:
    result = score_d2_3(empty_scored, tmp_path)
    assert result.value == UNVERIFIED


# ---------------------------------------------------------------------------
# D3
# ---------------------------------------------------------------------------


def test_d3_1_no_sbom_scores_zero(tmp_path: Path, empty_scored: dict) -> None:
    result = score_d3_1(empty_scored, tmp_path)
    assert result.value == 0


def test_d3_1_sbom_file_unverified(tmp_path: Path, empty_scored: dict) -> None:
    _write(tmp_path, "sbom.json", "{}")
    result = score_d3_1(empty_scored, tmp_path)
    assert result.value == UNVERIFIED


def test_d3_1_sbom_workflow_unverified(tmp_path: Path, empty_scored: dict) -> None:
    _write(tmp_path, ".github/workflows/sbom.yml", "uses: anchore/sbom-action@v1")
    result = score_d3_1(empty_scored, tmp_path)
    assert result.value == UNVERIFIED


def test_d3_2_no_signing_scores_zero(tmp_path: Path, empty_scored: dict) -> None:
    result = score_d3_2(empty_scored, tmp_path)
    assert result.value == 0


def test_d3_2_cosign_workflow_unverified(tmp_path: Path, empty_scored: dict) -> None:
    _write(tmp_path, ".github/workflows/release.yml", "uses: sigstore/cosign-installer@v3")
    result = score_d3_2(empty_scored, tmp_path)
    assert result.value == UNVERIFIED


def test_d3_4_no_dependency_automation_scores_zero(tmp_path: Path, empty_scored: dict) -> None:
    result = score_d3_4(empty_scored, tmp_path)
    assert result.value == 0


def test_d3_4_dependabot_scores_two(tmp_path: Path, empty_scored: dict) -> None:
    _write(tmp_path, ".github/dependabot.yml", "version: 2")
    result = score_d3_4(empty_scored, tmp_path)
    assert result.value == 2


# ---------------------------------------------------------------------------
# D5.4
# ---------------------------------------------------------------------------


def test_d5_4_no_tags_scores_zero(tmp_path: Path, empty_scored: dict) -> None:
    empty_scored["repo_meta"]["git_summary"] = {"tag_count": 0}
    result = score_d5_4(empty_scored, tmp_path)
    assert result.value == 0


def test_d5_4_tags_present_unverified(tmp_path: Path, empty_scored: dict) -> None:
    empty_scored["repo_meta"]["git_summary"] = {"tag_count": 5}
    result = score_d5_4(empty_scored, tmp_path)
    assert result.value == UNVERIFIED


# ---------------------------------------------------------------------------
# D6
# ---------------------------------------------------------------------------


def test_d6_1_no_readme_scores_zero(tmp_path: Path, empty_scored: dict) -> None:
    result = score_d6_1(empty_scored, tmp_path)
    assert result.value == 0


def test_d6_1_stub_readme_scores_zero(tmp_path: Path, empty_scored: dict) -> None:
    _write(tmp_path, "README.md", "# Foo")
    result = score_d6_1(empty_scored, tmp_path)
    assert result.value == 0


def test_d6_1_real_readme_unverified(tmp_path: Path, empty_scored: dict) -> None:
    _write(tmp_path, "README.md", "\n".join([f"line {i}" for i in range(20)]))
    result = score_d6_1(empty_scored, tmp_path)
    assert result.value == UNVERIFIED


def test_d6_2_no_license_scores_zero(tmp_path: Path, empty_scored: dict) -> None:
    result = score_d6_2(empty_scored, tmp_path)
    assert result.value == 0


def test_d6_2_license_with_spdx_hint_scores_two(tmp_path: Path, empty_scored: dict) -> None:
    _write(tmp_path, "LICENSE", "MIT License\n\nCopyright (c) 2026 calabamatex")
    result = score_d6_2(empty_scored, tmp_path)
    assert result.value == 2


def test_d6_3_no_security_md_scores_zero(tmp_path: Path, empty_scored: dict) -> None:
    result = score_d6_3(empty_scored, tmp_path)
    assert result.value == 0


def test_d6_3_security_md_with_contact_scores_two(tmp_path: Path, empty_scored: dict) -> None:
    _write(
        tmp_path,
        "SECURITY.md",
        "# Security Policy\n\n"
        "## Supported Versions\n\n"
        "Only the latest minor version receives security fixes.\n\n"
        "## Reporting a Vulnerability\n\n"
        "Report vulnerabilities to security@example.com.\n"
        "We will respond within 7 days.\n"
        "See our disclosure process below.\n"
        "Coordinated disclosure with CVE assignment is supported.\n",
    )
    result = score_d6_3(empty_scored, tmp_path)
    assert result.value == 2


def test_d6_4_no_contributing_scores_zero(tmp_path: Path, empty_scored: dict) -> None:
    result = score_d6_4(empty_scored, tmp_path)
    assert result.value == 0


def test_d6_4_contributing_only_scores_one(tmp_path: Path, empty_scored: dict) -> None:
    _write(tmp_path, "CONTRIBUTING.md", "How to contribute")
    result = score_d6_4(empty_scored, tmp_path)
    assert result.value == 1


def test_d6_4_contributing_plus_coc_scores_two(tmp_path: Path, empty_scored: dict) -> None:
    _write(tmp_path, "CONTRIBUTING.md", "How to contribute")
    _write(tmp_path, "CODE_OF_CONDUCT.md", "Be excellent to each other")
    result = score_d6_4(empty_scored, tmp_path)
    assert result.value == 2


def test_d6_4_with_governance_scores_three(tmp_path: Path, empty_scored: dict) -> None:
    _write(tmp_path, "CONTRIBUTING.md", "x")
    _write(tmp_path, "CODE_OF_CONDUCT.md", "x")
    _write(tmp_path, "GOVERNANCE.md", "Maintainers, decision process")
    result = score_d6_4(empty_scored, tmp_path)
    assert result.value == 3


# ---------------------------------------------------------------------------
# D7.1
# ---------------------------------------------------------------------------


def test_d7_1_bus_factor_one_scores_zero(tmp_path: Path, empty_scored: dict) -> None:
    empty_scored["repo_meta"]["git_summary"] = {"estimated_bus_factor": 1, "contributor_count": 1}
    result = score_d7_1(empty_scored, tmp_path)
    assert result.value == 0


def test_d7_1_bus_factor_two_scores_one(tmp_path: Path, empty_scored: dict) -> None:
    empty_scored["repo_meta"]["git_summary"] = {"estimated_bus_factor": 2, "contributor_count": 3}
    result = score_d7_1(empty_scored, tmp_path)
    assert result.value == 1


def test_d7_1_bus_factor_three_scores_two(tmp_path: Path, empty_scored: dict) -> None:
    empty_scored["repo_meta"]["git_summary"] = {"estimated_bus_factor": 3, "contributor_count": 5}
    result = score_d7_1(empty_scored, tmp_path)
    assert result.value == 2


def test_d7_1_high_bus_with_codeowners_scores_three(tmp_path: Path, empty_scored: dict) -> None:
    empty_scored["repo_meta"]["git_summary"] = {"estimated_bus_factor": 6, "contributor_count": 10}
    _write(tmp_path, ".github/CODEOWNERS", "* @user1 @user2")
    result = score_d7_1(empty_scored, tmp_path)
    assert result.value == 3


def test_d7_1_no_bus_factor_data_unverified(tmp_path: Path, empty_scored: dict) -> None:
    result = score_d7_1(empty_scored, tmp_path)
    assert result.value == UNVERIFIED


# ---------------------------------------------------------------------------
# Top-level score_all
# ---------------------------------------------------------------------------


def test_score_all_emits_31_scores(tmp_path: Path, empty_scored: dict) -> None:
    scores = score_all(empty_scored, tmp_path)
    assert len(scores) == 31
    ids = {s.criterion_id for s in scores}
    expected = {f"D1.{i}" for i in range(1, 4)}  # D1 has 3 sub-criteria.
    for d in range(2, 9):
        expected |= {f"D{d}.{i}" for i in range(1, 5)}  # D2..D8 have 4 each.
    assert ids == expected


def test_score_all_d8_not_applicable_marks_d8(tmp_path: Path, empty_scored: dict) -> None:
    scores = score_all(empty_scored, tmp_path, d8_not_applicable=True)
    d8_scores = [s for s in scores if s.criterion_id.startswith("D8.")]
    assert len(d8_scores) == 4
    for s in d8_scores:
        assert s.value == NOT_APPLICABLE


def test_d4_dora_metrics_all_unverified(tmp_path: Path, empty_scored: dict) -> None:
    """No DORA metric is computable from the current detector surface."""
    scores = score_all(empty_scored, tmp_path)
    d4_scores = [s for s in scores if s.criterion_id.startswith("D4.")]
    assert len(d4_scores) == 4
    assert all(s.value == UNVERIFIED for s in d4_scores)


def test_d8_compliance_all_unverified_when_not_overridden(tmp_path: Path, empty_scored: dict) -> None:
    """D8 is org-scoped; without --d8-not-applicable, all 4 are ?."""
    scores = score_all(empty_scored, tmp_path)
    d8_scores = [s for s in scores if s.criterion_id.startswith("D8.")]
    assert all(s.value == UNVERIFIED for s in d8_scores)
