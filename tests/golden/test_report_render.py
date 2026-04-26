"""Golden tests for the Markdown renderer.

The v0.9.0 renderer (SDLC-070) is persona-aware: section structure mirrors
the HTML renderer's executive callout + scorecard + per-emphasis narrative
blocks + production/fixture-segregated findings. These tests assert the
v0.9.0 layout, not the v0.8.0 numbered-section template.
"""

from __future__ import annotations

from sdlc_assessor.renderer.markdown import render_markdown_report

SCORED_LIST_SHAPE = {
    "repo_meta": {"name": "demo", "default_branch": "main"},
    "classification": {
        "repo_archetype": "service",
        "maturity_profile": "production",
        "deployment_surface": "networked",
        "network_exposure": True,
        "release_surface": "deployable_service",
        "classification_confidence": 0.9,
    },
    "inventory": {
        "source_files": 1,
        "source_loc": 10,
        "test_files": 1,
        "workflow_files": 1,
        "runtime_dependencies": 2,
        "dev_dependencies": 4,
    },
    "findings": [
        {
            "id": "F-0001",
            "category": "security_posture",
            "subcategory": "probable_secrets",
            "severity": "high",
            "confidence": "medium",
            "statement": "Probable hardcoded secret detected.",
            "evidence": [{"path": "src/app.py", "line_start": 12, "match_type": "pattern"}],
            "score_impact": {"direction": "negative", "magnitude": 7},
        },
        {
            "id": "F-0002",
            "category": "code_quality_contracts",
            "subcategory": "print_usage",
            "severity": "low",
            "confidence": "high",
            "statement": "print() call in module-level code.",
            "evidence": [{"path": "src/app.py", "line_start": 22}],
            "score_impact": {"direction": "negative", "magnitude": 2},
        },
    ],
    "scoring": {
        "overall_score": 55,
        "verdict": "fail",
        "score_confidence": "medium",
        "category_scores": [
            {
                "category": "security_posture",
                "applicable": True,
                "score": 2,
                "max_score": 20,
                "summary": "Strongest issue: secret leak.",
                "key_findings": ["F-0001"],
            },
            {
                "category": "code_quality_contracts",
                "applicable": True,
                "score": 12,
                "max_score": 15,
                "summary": "Minor stdout chatter.",
                "key_findings": ["F-0002"],
            },
            {
                "category": "reproducibility_research_rigor",
                "applicable": False,
                "score": 0,
                "max_score": 0,
                "summary": "Not applicable for a service archetype.",
                "key_findings": [],
            },
        ],
        "effective_profile": {"use_case": "engineering_triage", "maturity": "production", "repo_type": "service"},
    },
    "hard_blockers": [
        {"severity": "critical", "title": "Probable hardcoded secret.", "reason": "credential exposure", "closure_requirements": ["Rotate."]}
    ],
}


def test_report_contains_required_sections() -> None:
    """v0.9.0: persona-aware sections + scorecard + segregated findings."""
    report = render_markdown_report(SCORED_LIST_SHAPE)
    for marker in (
        "# SDLC Assessment Report — demo",
        "## Executive Summary",
        "## Scorecard",
        "## Persona-aware narrative",
        "## Hard Blockers",
        "## Quantitative Inventory",
        "## Category Scoring Matrix",
        "## Detailed Findings",
        "## Evidence Appendix",
    ):
        assert marker in report, f"missing marker: {marker}"


def test_report_renders_persona_narrative_blocks_for_engineering_triage() -> None:
    """Engineering-triage profile has 4 narrative_emphasis terms; each becomes an h3."""
    report = render_markdown_report(SCORED_LIST_SHAPE)
    persona_section = report.split("## Persona-aware narrative", 1)[1].split("## Hard Blockers", 1)[0]
    # engineering_triage emphasis: technical_debt, failure_modes, code_level_evidence, implementation_priority
    for title in ("Technical debt", "Failure modes", "Code-level evidence", "Implementation priority"):
        assert title in persona_section, f"missing narrative block: {title}"


def test_report_executive_summary_pulls_persona_callouts() -> None:
    """Executive summary lists strongest callouts with severity tags."""
    report = render_markdown_report(SCORED_LIST_SHAPE)
    exec_section = report.split("## Executive Summary", 1)[1].split("## Scorecard", 1)[0]
    # Critical blocker should appear in the headline.
    assert "**1**" in exec_section or "1 critical" in exec_section.lower() or "critical blocker" in exec_section.lower()


def test_report_scorecard_contains_overall_and_verdict() -> None:
    report = render_markdown_report(SCORED_LIST_SHAPE)
    scorecard = report.split("## Scorecard", 1)[1].split("## Persona-aware", 1)[0]
    assert "| Overall | 55 |" in scorecard
    assert "`fail`" in scorecard


def test_report_findings_segregated_into_production_only_when_no_fixtures() -> None:
    """No fixture-tagged findings → no fixture subsection rendered."""
    report = render_markdown_report(SCORED_LIST_SHAPE)
    assert "Fixture / non-production findings" not in report


def test_report_fixture_findings_segregated_when_tagged() -> None:
    payload = {
        **SCORED_LIST_SHAPE,
        "findings": [
            *SCORED_LIST_SHAPE["findings"],
            {
                "id": "F-fix",
                "category": "code_quality_contracts",
                "subcategory": "print_usage",
                "severity": "low",
                "confidence": "high",
                "statement": "fixture print",
                "evidence": [{"path": "tests/fixtures/x/main.py", "line_start": 1}],
                "score_impact": {"direction": "negative", "magnitude": 2},
                "tags": ["source:test_fixture"],
            },
        ],
    }
    report = render_markdown_report(payload)
    assert "Fixture / non-production findings" in report
    fixture_section = report.split("Fixture / non-production findings", 1)[1]
    assert "tests/fixtures/x/main.py" in fixture_section
    # Production findings table must NOT contain the fixture finding's path.
    prod_section = report.split("### Production findings", 1)[1].split("### Production findings by category", 1)[0]
    assert "tests/fixtures/x/main.py" not in prod_section


def test_report_legacy_dict_shape_back_compat() -> None:
    """SDLC-015: dict shape must still render with a deprecation warning."""
    import warnings

    legacy = {
        **SCORED_LIST_SHAPE,
        "scoring": {
            **SCORED_LIST_SHAPE["scoring"],
            "category_scores": {
                "security_posture": {"applicability": "applicable", "score": 2, "max": 20, "summary": "x"},
            },
        },
    }
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        report = render_markdown_report(legacy)
    assert "## Category Scoring Matrix" in report
    assert any(issubclass(w.category, DeprecationWarning) for w in captured)


def test_report_mentions_hard_blocker_or_none() -> None:
    payload = {
        "repo_meta": {},
        "classification": {},
        "inventory": {},
        "findings": [],
        "scoring": {"category_scores": []},
        "hard_blockers": [],
    }
    report = render_markdown_report(payload)
    assert "No hard blockers were triggered." in report
