"""Git-history detector tests (SDLC-037).

These tests construct a tiny throw-away git repo per case via subprocess so
the detector exercises the real `git log` path. If `git` is missing on the
runner the tests are skipped — the detector itself returns an empty list in
that case.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from sdlc_assessor.detectors.git_history import (
    BUS_FACTOR_AUTHOR_SHARE_THRESHOLD,
    SIGNING_LOW_COVERAGE_THRESHOLD,
    collect_git_summary,
    run_git_history_detectors,
)

_GIT = shutil.which("git")
pytestmark = pytest.mark.skipif(_GIT is None, reason="git not on PATH")


def _git(repo: Path, *args: str) -> None:
    subprocess.run([_GIT, "-C", str(repo), *args], check=True, capture_output=True)


def _init_repo(repo: Path, *, commits: int = 1, author: str = "Alice <alice@example>") -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.name", author.split(" <")[0])
    _git(repo, "config", "user.email", author.split("<")[1].rstrip(">"))
    _git(repo, "config", "commit.gpgsign", "false")
    for i in range(commits):
        (repo / f"file{i}.txt").write_text(f"hello {i}", encoding="utf-8")
        _git(repo, "add", f"file{i}.txt")
        _git(repo, "commit", "-q", "-m", f"commit {i}", "--allow-empty")


def test_no_findings_outside_git_repo(tmp_path: Path) -> None:
    assert run_git_history_detectors(tmp_path) == []
    assert collect_git_summary(tmp_path) is None


def test_git_summary_populated_for_real_repo(tmp_path: Path) -> None:
    repo = tmp_path / "demo"
    _init_repo(repo, commits=3)
    summary = collect_git_summary(repo)
    assert summary is not None
    assert summary["commits_analyzed"] == 3
    assert 0.0 <= summary["signing_coverage"] <= 1.0
    assert summary["bus_factor"] >= 1
    assert summary["codeowners_present"] is False


def test_unsigned_commits_finding_fires_at_low_coverage(tmp_path: Path) -> None:
    repo = tmp_path / "demo"
    _init_repo(repo, commits=10)
    findings = run_git_history_detectors(repo)
    subcats = {f["subcategory"] for f in findings}
    # All commits unsigned → coverage is 0.0, well below the threshold.
    assert "unsigned_commits" in subcats
    finding = next(f for f in findings if f["subcategory"] == "unsigned_commits")
    assert finding["severity"] == "medium"
    assert "0%" in finding["statement"] or "0.0%" in finding["statement"]


def test_unsigned_finding_silenced_below_minimum_commit_threshold(tmp_path: Path) -> None:
    repo = tmp_path / "demo"
    _init_repo(repo, commits=2)
    findings = run_git_history_detectors(repo)
    assert "unsigned_commits" not in {f["subcategory"] for f in findings}


def test_bus_factor_low_high_severity_when_one_author(tmp_path: Path) -> None:
    repo = tmp_path / "demo"
    _init_repo(repo, commits=20)
    findings = run_git_history_detectors(repo)
    bus = [f for f in findings if f["subcategory"] == "bus_factor_low"]
    assert bus
    assert bus[0]["severity"] == "high"


def test_missing_codeowners_finding(tmp_path: Path) -> None:
    repo = tmp_path / "demo"
    _init_repo(repo, commits=3)
    findings = run_git_history_detectors(repo)
    assert "missing_codeowners" in {f["subcategory"] for f in findings}


def test_codeowners_present_silences_finding(tmp_path: Path) -> None:
    repo = tmp_path / "demo"
    _init_repo(repo, commits=3)
    (repo / ".github").mkdir()
    (repo / ".github" / "CODEOWNERS").write_text("* @alice\n", encoding="utf-8")
    findings = run_git_history_detectors(repo)
    assert "missing_codeowners" not in {f["subcategory"] for f in findings}


def test_thresholds_module_constants_are_in_expected_range() -> None:
    assert 0.0 < SIGNING_LOW_COVERAGE_THRESHOLD < 1.0
    assert 0.0 < BUS_FACTOR_AUTHOR_SHARE_THRESHOLD < 1.0
