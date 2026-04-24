from sdlc_assessor.renderer.markdown import render_markdown_report


def test_report_contains_required_sections() -> None:
    scored = {
        "repo_meta": {"name": "demo", "default_branch": "main"},
        "classification": {"repo_archetype": "service", "maturity_profile": "production", "deployment_surface": "networked"},
        "inventory": {"source_files": 1, "source_loc": 10, "test_files": 1, "workflow_files": 0},
        "findings": [{"category": "security_posture", "severity": "high", "statement": "Probable hardcoded secret detected."}],
        "scoring": {
            "overall_score": 55.0,
            "verdict": "fail",
            "score_confidence": "medium",
            "category_scores": {"security_posture": {"applicability": "applicable", "score": 2.0, "max": 20.0}},
        },
        "hard_blockers": [{"severity": "high", "reason": "Probable hardcoded secret detected."}],
    }

    report = render_markdown_report(scored)
    assert "## 1. Header" in report
    assert "## 3. Overall Score and Verdict" in report
    assert "## 8. Hard Blockers" in report
    assert "## 11. Evidence Appendix" in report


def test_report_mentions_hard_blocker_or_none() -> None:
    report_with_none = render_markdown_report(
        {
            "repo_meta": {},
            "classification": {},
            "inventory": {},
            "findings": [],
            "scoring": {"category_scores": {}},
            "hard_blockers": [],
        }
    )
    assert "No hard blockers were triggered." in report_with_none
