"""Integration tests for the 0.11.0 depth pass.

Renders all four persona deliverables against a single scored fixture
and asserts the user's specific complaints are addressed:

- Every threshold mention is grounded (cites use_case_profiles.json).
- Every recommendation shows the rule that produced it.
- Every inline citation marker has a matching footnote.
- Methodology + glossary present in every report.
- Score decomposition + gap analysis sections present.
- The user-flagged sentence "Score and blocker profile fall below the
  diligence bar" no longer appears as-is.
- No editorial speculation language (holdback / tranche / etc.) leaks
  into the rendered output for 0.11.0.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


PERSONAS = ["acquisition_diligence", "vc_diligence", "engineering_triage", "remediation_agent"]


@pytest.fixture(scope="module")
def rendered_reports(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    """Render all four persona reports against fixture_committed_credential.

    Generates the full pipeline (classify → collect → score → render)
    once per module so tests share the output.
    """
    repo_root = Path(__file__).resolve().parents[2]
    fixture = repo_root / "tests" / "fixtures" / "fixture_committed_credential"
    out_root = tmp_path_factory.mktemp("v0_11_render")

    rendered: dict[str, str] = {}
    for use_case in PERSONAS:
        out_dir = out_root / use_case
        cmd = [
            sys.executable,
            "-m",
            "sdlc_assessor.cli",
            "run",
            str(fixture),
            "--use-case",
            use_case,
            "--format",
            "html",
            "--out-dir",
            str(out_dir),
        ]
        subprocess.run(cmd, check=True, capture_output=True, cwd=str(repo_root))
        rendered[use_case] = (out_dir / "report.html").read_text(encoding="utf-8")
    return rendered


# ---------------------------------------------------------------------------
# Threshold grounding
# ---------------------------------------------------------------------------


def test_every_persona_shows_its_pass_threshold_with_number(rendered_reports: dict[str, str]) -> None:
    """The pass threshold must appear as a literal number in each report.

    The user explicitly asked: 'What is the diligence bar exactly?' —
    the answer must be a visible numeric token, not a paraphrase.
    """
    expected = {
        "acquisition_diligence": 74,
        "vc_diligence": 72,
        "engineering_triage": 70,
        "remediation_agent": 70,
    }
    for use_case, threshold in expected.items():
        html = rendered_reports[use_case]
        assert (
            f"<strong>{threshold}</strong>" in html
            or f"pass_threshold {threshold}" in html
            or f"pass threshold {threshold}" in html
        ), f"{use_case} did not surface pass threshold {threshold} in numeric form"


def test_every_persona_cites_use_case_profiles_json(rendered_reports: dict[str, str]) -> None:
    """Each report must cite the profile path where its threshold lives."""
    for use_case, html in rendered_reports.items():
        assert "use_case_profiles.json" in html, (
            f"{use_case} did not cite use_case_profiles.json — threshold is ungrounded"
        )


def test_user_flagged_sentence_is_gone(rendered_reports: dict[str, str]) -> None:
    """The user explicitly flagged this sentence as ambiguous handwaving."""
    flagged = "Score and blocker profile fall below the diligence bar"
    for use_case, html in rendered_reports.items():
        assert flagged not in html, (
            f"{use_case} still emits the user-flagged ambiguous phrasing: {flagged!r}"
        )


# ---------------------------------------------------------------------------
# Recommendation grounding
# ---------------------------------------------------------------------------


def test_every_persona_names_the_verdict_rule(rendered_reports: dict[str, str]) -> None:
    """The exec summary must spell out which rule branch fired."""
    for use_case, html in rendered_reports.items():
        # The exec summary uses 'Rule:' to introduce the branch text.
        assert "Rule: " in html, f"{use_case} exec summary did not name a verdict rule"


def test_recommendation_rationale_names_pass_threshold(rendered_reports: dict[str, str]) -> None:
    """Cover-page rationale must name the threshold + gap, not handwave."""
    expected_threshold = {
        "acquisition_diligence": 74,
        "vc_diligence": 72,
        "engineering_triage": 70,
        "remediation_agent": 70,
    }
    for use_case, html in rendered_reports.items():
        # The rationale lives in the .recommendation .rationale div.
        m = re.search(r'class="rationale"[^>]*>([^<]+)', html)
        assert m, f"{use_case} has no .rationale div"
        rationale = m.group(1)
        threshold = expected_threshold[use_case]
        # We accept any phrasing that includes the threshold number near the word
        # 'threshold' or 'pass' — the test is for grounding, not exact wording.
        assert re.search(rf"\b{threshold}\b", rationale), (
            f"{use_case} rationale does not name threshold {threshold}: {rationale!r}"
        )


# ---------------------------------------------------------------------------
# Section presence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "section_id",
    ["methodology", "score-decomposition", "gap-analysis", "glossary", "citations"],
)
def test_section_present_in_every_persona(rendered_reports: dict[str, str], section_id: str) -> None:
    """Each new depth-pass section must render in every persona report."""
    for use_case, html in rendered_reports.items():
        assert f'id="{section_id}"' in html, (
            f"{use_case} missing section #{section_id}"
        )


def test_methodology_box_names_formula_and_threshold(rendered_reports: dict[str, str]) -> None:
    for use_case, html in rendered_reports.items():
        # Extract just the methodology section.
        start = html.find('id="methodology"')
        end = html.find("</section>", start)
        section = html[start:end]
        assert "SEVERITY_WEIGHTS" in section, f"{use_case} methodology missing severity-weight reference"
        assert "use_case_profiles.json" in section, f"{use_case} methodology not citing profile path"


def test_glossary_includes_diligence_bar_for_acquisition(rendered_reports: dict[str, str]) -> None:
    """The user explicitly asked what 'the diligence bar' is — the glossary defines it."""
    html = rendered_reports["acquisition_diligence"]
    start = html.find('id="glossary"')
    end = html.find("</section>", start)
    section = html[start:end]
    assert "diligence bar" in section


# ---------------------------------------------------------------------------
# Citation resolution
# ---------------------------------------------------------------------------


def test_every_inline_citation_has_a_matching_footnote(rendered_reports: dict[str, str]) -> None:
    """No stranded [N] markers — every inline ref resolves."""
    for use_case, html in rendered_reports.items():
        markers = set(re.findall(r'href="#cite-(\d+)"', html))
        footnotes = set(re.findall(r'id="cite-(\d+)"', html))
        stranded = markers - footnotes
        assert not stranded, (
            f"{use_case} has inline markers without footnotes: {sorted(stranded)}"
        )


def test_at_least_three_citations_per_persona(rendered_reports: dict[str, str]) -> None:
    """The exec summary alone references threshold + score + verdict-rule sources."""
    for use_case, html in rendered_reports.items():
        footnotes = re.findall(r'id="cite-(\d+)"', html)
        assert len(footnotes) >= 3, (
            f"{use_case} has only {len(footnotes)} citations; exec summary needs ≥3"
        )


# ---------------------------------------------------------------------------
# Editorial-speculation guard (0.11.0 cut)
# ---------------------------------------------------------------------------


def test_no_editorial_speculation_terms_leak_into_reports(rendered_reports: dict[str, str]) -> None:
    """0.11.0 ships only math-polish. Holdback / tranche / etc. wait for 0.14.0+."""
    forbidden = ("holdback amount", "tranche plan", "valuation discount", "engineer-day rate")
    # Note: bare 'holdback' / 'tranche' may appear as glossary terms — we exclude those
    # from 0.11.0 (test_no_editorial_holdback_or_tranche_terms_in_glossary in test_methodology.py
    # enforces that). Here we guard against the *prose claim* surfacing.
    for use_case, html in rendered_reports.items():
        for token in forbidden:
            assert token not in html, (
                f"{use_case} renders editorial token {token!r} — drop until 0.14.0+ corpus exists"
            )


def test_projection_disclosure_present_when_phases_have_lifts(rendered_reports: dict[str, str]) -> None:
    """Phase-lift numbers must be disclosed as projections, not historical outcomes."""
    for use_case, html in rendered_reports.items():
        if "projected_lift" in html or "projected lift" in html.lower():
            assert "projection" in html.lower() and (
                "0.14.0" in html or "historical outcome" in html.lower()
            ), f"{use_case} renders phase lifts without projection disclosure"


# ---------------------------------------------------------------------------
# No-boilerplate (sentence-overlap across personas)
# ---------------------------------------------------------------------------


def test_no_full_paragraph_appears_identically_across_personas(
    rendered_reports: dict[str, str],
) -> None:
    """A sentence that appears in 3+ persona reports is boilerplate.

    Whitelist short page chrome and shared-methodology phrasing — we
    accept that the methodology box is shared across personas. The test
    targets persona-specific prose.
    """
    chrome_whitelist = {
        # Methodology box content is the same per spec — that's not boilerplate,
        # it's a shared explanation. We exclude #methodology content from the
        # check by stripping it before tokenizing.
    }

    def _persona_specific_text(html: str) -> set[str]:
        """Extract sentences from the exec-summary + cover only."""
        chunks: list[str] = []
        for tag in ('class="exec-summary"', 'class="recommendation"', 'class="cover"'):
            idx = html.find(tag)
            if idx == -1:
                continue
            end = html.find("</section>", idx)
            if end == -1:
                end = html.find("</aside>", idx)
            if end == -1:
                end = idx + 4000
            chunks.append(html[idx:end])
        text = " ".join(chunks)
        # Strip HTML tags.
        text = re.sub(r"<[^>]+>", " ", text)
        # Tokenize sentences.
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return {s.strip().lower() for s in sentences if len(s.strip()) > 30 and s not in chrome_whitelist}

    persona_sentences = {
        use_case: _persona_specific_text(html) for use_case, html in rendered_reports.items()
    }
    # Any sentence that appears in 3+ personas' exec summaries is boilerplate.
    sentence_counts: dict[str, int] = {}
    for sents in persona_sentences.values():
        for s in sents:
            sentence_counts[s] = sentence_counts.get(s, 0) + 1
    overshare = {s: n for s, n in sentence_counts.items() if n >= 3}
    assert not overshare, (
        f"sentences appear in ≥3 personas' exec summaries (boilerplate): "
        f"{list(overshare.items())[:3]}"
    )
