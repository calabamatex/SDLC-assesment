"""Golden tests for the Markdown renderer.

Covers the SDLC-015 / SDLC-023 list-of-dicts shape, the legacy dict back-compat
branch, and the dynamic §2 / §6 / §7 / §10 sections.
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
    report = render_markdown_report(SCORED_LIST_SHAPE)
    for section in (
        "## 1. Header",
        "## 2. Executive Summary",
        "## 3. Overall Score and Verdict",
        "## 4. Repo Classification Box",
        "## 5. Quantitative Inventory",
        "## 6. Top Strengths",
        "## 7. Top Risks",
        "## 8. Hard Blockers",
        "## 9. Category Scoring Matrix",
        "## 10. Detailed Findings by Category",
        "## 11. Evidence Appendix",
    ):
        assert section in report, f"missing {section}"


def test_report_top_strengths_does_not_invent_praise() -> None:
    report = render_markdown_report(SCORED_LIST_SHAPE)
    # Neither category is at full points → renderer must say so.
    assert "No category earned full points" in report


def test_report_top_strengths_lists_full_point_category_when_present() -> None:
    payload = {
        **SCORED_LIST_SHAPE,
        "scoring": {
            **SCORED_LIST_SHAPE["scoring"],
            "category_scores": [
                {
                    "category": "documentation_truthfulness",
                    "applicable": True,
                    "score": 12,
                    "max_score": 12,
                    "summary": "All documentation present.",
                    "key_findings": [],
                },
            ],
        },
    }
    report = render_markdown_report(payload)
    assert "documentation_truthfulness" in report
    assert "retained full points" in report


def test_report_top_risks_caps_at_five() -> None:
    findings = [
        {
            "id": f"F-{i:04d}",
            "category": "code_quality_contracts",
            "subcategory": "print_usage",
            "severity": "high",
            "confidence": "high",
            "statement": f"finding {i}",
            "evidence": [{"path": "x.py"}],
            "score_impact": {"direction": "negative", "magnitude": 7},
        }
        for i in range(10)
    ]
    payload = {**SCORED_LIST_SHAPE, "findings": findings}
    report = render_markdown_report(payload)
    risks_block = report.split("## 7. Top Risks", 1)[1].split("## 8.", 1)[0]
    bullet_count = sum(1 for line in risks_block.splitlines() if line.startswith("- **"))
    assert bullet_count <= 5


def test_report_findings_are_grouped_by_category(scored_with_two_categories=None) -> None:
    report = render_markdown_report(SCORED_LIST_SHAPE)
    section = report.split("## 10. Detailed Findings by Category", 1)[1]
    assert "### security_posture" in section
    assert "### code_quality_contracts" in section


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
    assert "## 9. Category Scoring Matrix" in report
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
