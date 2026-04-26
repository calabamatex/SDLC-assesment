"""HTML renderer tests (SDLC-064)."""

from __future__ import annotations

import re
from pathlib import Path

from sdlc_assessor.cli import main as cli_main
from sdlc_assessor.renderer.html import render_html_report

_SCORED = {
    "repo_meta": {"name": "demo", "default_branch": "main", "analysis_timestamp": "2026-04-26T00:00:00+00:00"},
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
            "statement": "Probable hardcoded secret <script>",  # XSS canary
            "evidence": [{"path": "src/app.py", "line_start": 12}],
            "score_impact": {"direction": "negative", "magnitude": 7},
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
                "category": "reproducibility_research_rigor",
                "applicable": False,
                "score": 0,
                "max_score": 0,
                "summary": "Not applicable.",
                "key_findings": [],
            },
        ],
        "effective_profile": {"use_case": "engineering_triage", "maturity": "production", "repo_type": "service"},
    },
    "hard_blockers": [
        {"severity": "critical", "title": "Secret leak.", "reason": "credential exposure", "closure_requirements": ["Rotate."]}
    ],
}


def test_html_report_renders_well_formed_document() -> None:
    html = render_html_report(_SCORED)
    assert html.startswith("<!DOCTYPE html>")
    assert "</html>" in html
    # Title reflects the repo name.
    assert "<title>SDLC Assessment — demo</title>" in html


def test_html_report_contains_all_required_sections() -> None:
    html = render_html_report(_SCORED)
    for header in (
        "2. Executive Summary",
        "4. Repo Classification",
        "5. Quantitative Inventory",
        "6. Top Strengths",
        "7. Top Risks",
        "8. Hard Blockers",
        "9. Category Scoring Matrix",
        "10. Detailed Findings",
        "11. Evidence Appendix",
    ):
        assert header in html, f"missing section: {header}"


def test_html_report_escapes_script_tags_in_finding_statement() -> None:
    """XSS canary: <script> in a finding statement must end up escaped."""
    html = render_html_report(_SCORED)
    assert "<script>Probable" not in html
    assert "&lt;script&gt;" in html
    # The trailing legitimate <script> tag (the sort logic) is allowed —
    # only one script tag should appear in the document.
    script_tags = re.findall(r"<script>", html)
    assert len(script_tags) == 1


def test_html_report_marks_severity_classes_on_finding_rows() -> None:
    html = render_html_report(_SCORED)
    assert 'class="sev-high"' in html
    # Critical blocker present → critical class somewhere.
    assert 'class="sev-critical"' in html


def test_html_report_no_findings_section_message() -> None:
    payload = {**_SCORED, "findings": [], "hard_blockers": []}
    html = render_html_report(payload)
    assert "No hard blockers were triggered." in html
    assert "No findings to display." in html


def test_html_report_legacy_dict_category_scores_back_compat() -> None:
    """Older artifacts use a dict for category_scores; we should still render."""
    legacy = {
        **_SCORED,
        "scoring": {
            **_SCORED["scoring"],
            "category_scores": {
                "security_posture": {
                    "applicability": "applicable",
                    "score": 2,
                    "max": 20,
                    "summary": "x",
                }
            },
        },
    }
    import warnings

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        html = render_html_report(legacy)
    assert "9. Category Scoring Matrix" in html
    assert any(issubclass(w.category, DeprecationWarning) for w in captured)


def test_html_report_full_points_strengths_listed() -> None:
    payload = {
        **_SCORED,
        "scoring": {
            **_SCORED["scoring"],
            "category_scores": [
                {
                    "category": "documentation_truthfulness",
                    "applicable": True,
                    "score": 12,
                    "max_score": 12,
                    "summary": "all docs",
                    "key_findings": [],
                },
            ],
        },
    }
    html = render_html_report(payload)
    assert "documentation_truthfulness" in html
    assert "retained full points" in html


# ---------------------------------------------------------------------------
# CLI integration: --format html / both
# ---------------------------------------------------------------------------


def test_cli_run_emits_html_when_format_html(tmp_path: Path) -> None:
    rc = cli_main(
        [
            "run",
            "tests/fixtures/fixture_python_basic",
            "--use-case",
            "engineering_triage",
            "--out-dir",
            str(tmp_path),
            "--format",
            "html",
        ]
    )
    assert rc == 0
    assert (tmp_path / "report.html").exists()
    assert not (tmp_path / "report.md").exists()
    text = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in text


def test_cli_run_emits_both_when_format_both(tmp_path: Path) -> None:
    rc = cli_main(
        [
            "run",
            "tests/fixtures/fixture_python_basic",
            "--use-case",
            "engineering_triage",
            "--out-dir",
            str(tmp_path),
            "--format",
            "both",
        ]
    )
    assert rc == 0
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "report.html").exists()


def test_cli_render_subcommand_writes_html(tmp_path: Path) -> None:
    """Run the pipeline once, then call `render` separately with --format html."""
    out_md = tmp_path / "report.md"
    out_html = tmp_path / "report.html"

    rc = cli_main(
        [
            "run",
            "tests/fixtures/fixture_python_basic",
            "--use-case",
            "engineering_triage",
            "--out-dir",
            str(tmp_path),
            "--format",
            "markdown",
        ]
    )
    assert rc == 0
    assert out_md.exists()
    assert not out_html.exists()

    # Now invoke render separately on the produced scored.json.
    rc = cli_main(
        [
            "render",
            str(tmp_path / "scored.json"),
            "--format",
            "html",
            "--out",
            str(out_html),
        ]
    )
    assert rc == 0
    assert out_html.exists()
