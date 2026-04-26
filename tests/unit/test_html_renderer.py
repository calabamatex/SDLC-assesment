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
    """v0.9.0 layout: executive callout + scorecard + persona narrative + sections."""
    html = render_html_report(_SCORED)
    for marker in (
        "Executive summary",                      # callout heading
        '<div class="scorecard">',                # scorecard region
        "Quantitative inventory",                 # inventory section
        "Hard blockers",                          # blockers section
        "Category scoring matrix",                # scoring matrix
        "Detailed findings",                      # detailed findings
        "Evidence appendix",                      # evidence appendix
    ):
        assert marker in html, f"missing marker: {marker}"


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
    # Findings table marks severity rows.
    assert 'class="sev-high"' in html
    # Hard-blocker callout uses the critical pill / class.
    assert "verdict-critical" in html or "callout-critical" in html or 'class="sev-critical"' in html


def test_html_report_no_findings_section_message() -> None:
    payload = {**_SCORED, "findings": [], "hard_blockers": []}
    html = render_html_report(payload)
    assert "No hard blockers were triggered." in html
    # v0.9.0 splits findings into production + fixture; "No findings" message
    # appears for the production half when the input has zero findings.
    assert "No production findings to display." in html or "No findings to display." in html


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
    assert "Category scoring matrix" in html
    assert any(issubclass(w.category, DeprecationWarning) for w in captured)


def test_html_report_renders_executive_callout_with_persona_summary() -> None:
    """v0.9.0: the executive callout pulls the first narrative block's summary."""
    html = render_html_report(_SCORED)
    # Callout container is present.
    assert '<aside class="exec-callout"' in html
    assert '<p class="headline">' in html


def test_html_report_renders_scorecard_with_six_cards() -> None:
    """v0.9.0: scorecard surfaces overall, verdict, blockers, findings, archetype, confidence."""
    html = render_html_report(_SCORED)
    assert '<div class="scorecard">' in html
    # Six labels in the scorecard.
    for label in ("Overall", "Verdict", "Hard blockers", "Production findings", "Archetype", "Classification confidence"):
        assert f">{label}<" in html, f"missing scorecard label: {label}"


def test_html_report_segregates_fixture_findings_under_collapsible() -> None:
    """v0.9.0: fixture-derived findings live in a <details> block, not the main table."""
    payload = {
        **_SCORED,
        "findings": [
            {
                "id": "F-prod",
                "category": "code_quality_contracts",
                "subcategory": "print_usage",
                "severity": "low",
                "confidence": "high",
                "statement": "production print",
                "evidence": [{"path": "sdlc_assessor/cli.py", "line_start": 5}],
                "score_impact": {"direction": "negative", "magnitude": 2},
                "tags": [],
            },
            {
                "id": "F-fix",
                "category": "code_quality_contracts",
                "subcategory": "print_usage",
                "severity": "low",
                "confidence": "high",
                "statement": "fixture print",
                "evidence": [{"path": "tests/fixtures/fixture_python_basic/main.py", "line_start": 1}],
                "score_impact": {"direction": "negative", "magnitude": 2},
                "tags": ["source:test_fixture"],
            },
        ],
    }
    html = render_html_report(payload)
    assert '<details class="fixture-section">' in html
    # Fixture finding is inside the details block, not the production table.
    prod_table_start = html.find('id="prod-findings"')
    fixture_details_start = html.find('class="fixture-section"')
    assert prod_table_start < fixture_details_start
    # The fixture finding's path appears in the document.
    assert "tests/fixtures/fixture_python_basic/main.py" in html


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
