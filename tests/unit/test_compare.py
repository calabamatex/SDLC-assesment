"""Comparison engine + CLI integration tests (SDLC-061, SDLC-063)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sdlc_assessor.cli import main as cli_main
from sdlc_assessor.compare.engine import (
    build_comparison,
    comparison_to_dict,
)
from sdlc_assessor.compare.markdown import render_comparison_markdown


def _fake_scored(
    *,
    overall: int,
    verdict: str,
    cat_scores: list[tuple[str, int, int]],
    findings: list[dict],
    blockers: list[dict] | None = None,
    classification: dict | None = None,
) -> dict:
    return {
        "repo_meta": {"name": "demo", "default_branch": "main", "analysis_timestamp": "2026-04-26T00:00:00+00:00"},
        "classification": classification or {
            "repo_archetype": "library",
            "maturity_profile": "prototype",
            "deployment_surface": "package_only",
            "classification_confidence": 0.9,
            "language_pack_selection": ["common", "python"],
            "network_exposure": False,
            "release_surface": "internal_only",
        },
        "inventory": {
            "source_files": 1,
            "source_loc": 10,
            "test_files": 1,
            "workflow_files": 1,
            "runtime_dependencies": 0,
            "dev_dependencies": 0,
        },
        "findings": findings,
        "scoring": {
            "base_weights": {},
            "applied_weights": {},
            "category_scores": [
                {
                    "category": cat,
                    "applicable": True,
                    "score": s,
                    "max_score": m,
                    "summary": f"Category {cat} summary.",
                    "key_findings": [],
                }
                for cat, s, m in cat_scores
            ],
            "overall_score": overall,
            "verdict": verdict,
        },
        "hard_blockers": blockers or [],
    }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


def test_build_comparison_overall_delta_and_verdict_change() -> None:
    a = _fake_scored(overall=85, verdict="pass", cat_scores=[("security_posture", 18, 20)], findings=[])
    b = _fake_scored(overall=72, verdict="conditional_pass", cat_scores=[("security_posture", 12, 20)], findings=[])
    c = build_comparison(a, b, label_a="path/a", label_b="path/b")
    assert c.overall_score_a == 85
    assert c.overall_score_b == 72
    assert c.overall_score_delta == -13
    assert c.verdict_change == "pass → conditional_pass"


def test_build_comparison_unchanged_verdict() -> None:
    a = _fake_scored(overall=85, verdict="pass", cat_scores=[], findings=[])
    b = _fake_scored(overall=87, verdict="pass", cat_scores=[], findings=[])
    c = build_comparison(a, b, label_a="a", label_b="b")
    assert c.verdict_change == "unchanged"


def test_build_comparison_category_deltas_signed() -> None:
    a = _fake_scored(
        overall=85,
        verdict="pass",
        cat_scores=[("security_posture", 18, 20), ("code_quality_contracts", 15, 16)],
        findings=[],
    )
    b = _fake_scored(
        overall=80,
        verdict="pass",
        cat_scores=[("security_posture", 12, 20), ("code_quality_contracts", 15, 16)],
        findings=[],
    )
    c = build_comparison(a, b, label_a="a", label_b="b")
    deltas_by_cat = {d.category: d.delta for d in c.category_deltas}
    assert deltas_by_cat["security_posture"] == -6
    assert deltas_by_cat["code_quality_contracts"] == 0


def test_build_comparison_finding_deltas_classify_only_in_each_side() -> None:
    a = _fake_scored(
        overall=85,
        verdict="pass",
        cat_scores=[],
        findings=[
            {"id": "F-1", "category": "security_posture", "subcategory": "eval_or_exec",
             "severity": "critical", "statement": "eval"},
            {"id": "F-2", "category": "security_posture", "subcategory": "shared",
             "severity": "high", "statement": "shared"},
        ],
    )
    b = _fake_scored(
        overall=80,
        verdict="pass",
        cat_scores=[],
        findings=[
            {"id": "F-3", "category": "security_posture", "subcategory": "shared",
             "severity": "high", "statement": "shared"},
            {"id": "F-4", "category": "security_posture", "subcategory": "shared",
             "severity": "high", "statement": "shared"},
            {"id": "F-5", "category": "code_quality_contracts", "subcategory": "new_thing",
             "severity": "medium", "statement": "new"},
        ],
    )
    c = build_comparison(a, b, label_a="a", label_b="b")
    by_subcat = {(d.category, d.subcategory): d for d in c.finding_deltas}
    eval_d = by_subcat[("security_posture", "eval_or_exec")]
    new_d = by_subcat[("code_quality_contracts", "new_thing")]
    shared = by_subcat[("security_posture", "shared")]
    assert eval_d.only_in == "a"
    assert eval_d.count_a == 1 and eval_d.count_b == 0 and eval_d.delta == -1
    assert new_d.only_in == "b"
    assert new_d.count_a == 0 and new_d.count_b == 1 and new_d.delta == 1
    assert shared.only_in == "both"
    assert shared.count_a == 1 and shared.count_b == 2 and shared.delta == 1


def test_build_comparison_blocker_delta_split_by_severity() -> None:
    a = _fake_scored(
        overall=70, verdict="conditional_pass", cat_scores=[], findings=[],
        blockers=[{"title": "x", "reason": "x", "severity": "critical"}],
    )
    b = _fake_scored(
        overall=60, verdict="conditional_pass", cat_scores=[], findings=[],
        blockers=[
            {"title": "x", "reason": "x", "severity": "critical"},
            {"title": "y", "reason": "y", "severity": "critical"},
            {"title": "z", "reason": "z", "severity": "high"},
        ],
    )
    c = build_comparison(a, b, label_a="a", label_b="b")
    assert c.blocker_delta_critical == 1
    assert c.blocker_delta_high == 1


def test_comparison_to_dict_is_json_serialisable() -> None:
    a = _fake_scored(overall=85, verdict="pass", cat_scores=[("x", 10, 12)], findings=[])
    b = _fake_scored(overall=80, verdict="pass", cat_scores=[("x", 10, 12)], findings=[])
    c = build_comparison(a, b, label_a="a", label_b="b")
    payload = comparison_to_dict(c)
    json.dumps(payload)  # raises if not serialisable
    assert payload["overall_score_a"] == 85
    assert payload["overall_score_b"] == 80
    assert isinstance(payload["category_deltas"], list)


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


def test_render_comparison_markdown_required_sections() -> None:
    a = _fake_scored(
        overall=85, verdict="pass",
        cat_scores=[("security_posture", 18, 20)],
        findings=[
            {"id": "F-1", "category": "security_posture", "subcategory": "eval_or_exec",
             "severity": "critical", "statement": "eval call"},
        ],
    )
    b = _fake_scored(
        overall=72, verdict="conditional_pass",
        cat_scores=[("security_posture", 12, 20)],
        findings=[
            {"id": "F-2", "category": "code_quality_contracts", "subcategory": "new_thing",
             "severity": "medium", "statement": "new finding"},
        ],
        blockers=[{"title": "x", "reason": "x", "severity": "critical"}],
    )
    md = render_comparison_markdown(build_comparison(a, b, label_a="path/a", label_b="path/b"))
    for header in (
        "# SDLC Comparison Report",
        "## 1. Overall Score and Verdict",
        "## 2. Per-category Score Deltas",
        "## 3. Hard-blocker Delta",
        "## 4. Finding-set Diff",
        "## 5. Classification Delta",
    ):
        assert header in md, f"missing section: {header}"
    assert "▼" in md  # negative delta marker present
    assert "eval_or_exec" in md
    assert "new_thing" in md


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def test_cli_compare_subcommand_writes_artifacts(tmp_path: Path) -> None:
    """End-to-end: `sdlc compare a b ...` writes scored dirs + comparison artifacts."""
    rc = cli_main(
        [
            "compare",
            "tests/fixtures/fixture_python_basic",
            "tests/fixtures/fixture_probable_secret",
            "--use-case",
            "engineering_triage",
            "--out-dir",
            str(tmp_path),
        ]
    )
    assert rc == 0
    assert (tmp_path / "repo_a" / "scored.json").exists()
    assert (tmp_path / "repo_b" / "scored.json").exists()
    assert (tmp_path / "comparison.md").exists()
    assert (tmp_path / "comparison.json").exists()

    # The Markdown report should mention both fixture paths.
    md = (tmp_path / "comparison.md").read_text(encoding="utf-8")
    assert "fixture_python_basic" in md
    assert "fixture_probable_secret" in md

    # JSON shape sanity.
    payload = json.loads((tmp_path / "comparison.json").read_text(encoding="utf-8"))
    assert "overall_score_a" in payload
    assert "overall_score_b" in payload
    assert "finding_deltas" in payload
    # The probable-secret fixture should score lower than python_basic.
    assert payload["overall_score_a"] > payload["overall_score_b"]


def test_cli_compare_with_explicit_profiles(tmp_path: Path) -> None:
    rc = cli_main(
        [
            "compare",
            "tests/fixtures/fixture_go_basic",
            "tests/fixtures/fixture_go_panics",
            "--use-case",
            "engineering_triage",
            "--maturity",
            "production",
            "--repo-type",
            "service",
            "--out-dir",
            str(tmp_path),
        ]
    )
    assert rc == 0
    payload = json.loads((tmp_path / "comparison.json").read_text(encoding="utf-8"))
    # Both repos scored under the same explicit profile; the "panics" fixture
    # should land below the basic one.
    assert payload["overall_score_a"] > payload["overall_score_b"]


@pytest.mark.parametrize(
    ("repo_a", "repo_b"),
    [
        ("tests/fixtures/fixture_kotlin_basic", "tests/fixtures/fixture_kotlin_unsafe"),
        ("tests/fixtures/fixture_java_basic", "tests/fixtures/fixture_java_unsafe"),
        ("tests/fixtures/fixture_csharp_basic", "tests/fixtures/fixture_csharp_unsafe"),
    ],
)
def test_cli_compare_lang_clean_vs_dirty(repo_a: str, repo_b: str, tmp_path: Path) -> None:
    rc = cli_main(
        [
            "compare",
            repo_a,
            repo_b,
            "--use-case",
            "engineering_triage",
            "--out-dir",
            str(tmp_path),
        ]
    )
    assert rc == 0
    payload = json.loads((tmp_path / "comparison.json").read_text(encoding="utf-8"))
    # The "unsafe"/"panics" fixture must score worse than the clean one.
    assert payload["overall_score_a"] >= payload["overall_score_b"]
    # And there should be at least one finding-only-in-B.
    assert any(d["only_in"] == "b" for d in payload["finding_deltas"])
