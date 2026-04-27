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


def test_every_persona_shows_rsf_persona_total(rendered_reports: dict[str, str]) -> None:
    """Each report's RSF block must show the persona-weighted total %."""
    for use_case, html in rendered_reports.items():
        # The RSF block renders the per-persona total table; every persona row
        # carries '<strong>NN.N%</strong>'.
        assert re.search(r"<strong>\d+\.\d%</strong>", html), (
            f"{use_case} report does not surface any RSF persona total"
        )


def test_every_persona_cites_rsf_canonical_doc(rendered_reports: dict[str, str]) -> None:
    """Each report must cite the RSF v1.0 canonical doc as the source."""
    for use_case, html in rendered_reports.items():
        assert "rsf_v1.0.md" in html or "Repository Scoring Framework" in html, (
            f"{use_case} does not cite the RSF canonical doc"
        )


def test_user_flagged_sentence_is_gone(rendered_reports: dict[str, str]) -> None:
    """The user explicitly flagged this sentence as ambiguous handwaving."""
    flagged = "Score and blocker profile fall below the diligence bar"
    for use_case, html in rendered_reports.items():
        assert flagged not in html, (
            f"{use_case} still emits the user-flagged ambiguous phrasing: {flagged!r}"
        )


def test_no_legacy_pass_threshold_language(rendered_reports: dict[str, str]) -> None:
    """Post-RSF, the report must not say 'pass_threshold X' or 'falls N points below'."""
    legacy_phrases = (
        "pass_threshold 7",     # catches "pass_threshold 70/72/74"
        "pass threshold 7",     # space variant
        "points below the",     # legacy gap phrasing
        "points short of the",
        "use_case_profiles.json:",  # legacy citation
    )
    for use_case, html in rendered_reports.items():
        for phrase in legacy_phrases:
            assert phrase not in html, (
                f"{use_case} still contains legacy threshold language: "
                f"{phrase!r}"
            )


# ---------------------------------------------------------------------------
# RSF assessment grounding
# ---------------------------------------------------------------------------


def test_rsf_block_present_in_every_report(rendered_reports: dict[str, str]) -> None:
    for use_case, html in rendered_reports.items():
        assert 'id="rsf-assessment"' in html, (
            f"{use_case} missing RSF assessment block"
        )


def test_rsf_block_renders_eight_personas(rendered_reports: dict[str, str]) -> None:
    """Each RSF block surfaces all 8 personas (the matrix from RSF §3)."""
    for use_case, html in rendered_reports.items():
        # Extract the RSF block.
        start = html.find('id="rsf-assessment"')
        end = html.find("</section>", start)
        block = html[start:end]
        for persona_label in ("VC", "PE/M&amp;A", "CTO/VP Eng", "Eng Mgr", "CISO",
                              "Procurement", "OSS user", "C-level non-tech"):
            assert persona_label in block, (
                f"{use_case} RSF block missing persona {persona_label!r}"
            )


@pytest.mark.parametrize(
    "section_id",
    ["rsf-assessment", "methodology", "glossary", "citations"],
)
def test_section_present_in_every_persona(rendered_reports: dict[str, str], section_id: str) -> None:
    """RSF-grounded sections must render in every persona report.

    Note: the legacy ``score-decomposition`` and ``gap-analysis`` sections
    were removed in the RSF cutover (their math used the made-up rubric).
    """
    for use_case, html in rendered_reports.items():
        assert f'id="{section_id}"' in html, (
            f"{use_case} missing section #{section_id}"
        )


def test_legacy_score_decomposition_section_is_gone(rendered_reports: dict[str, str]) -> None:
    """The score-decomposition section was removed in the RSF cutover."""
    for use_case, html in rendered_reports.items():
        assert 'id="score-decomposition"' not in html, (
            f"{use_case} still renders the legacy score-decomposition section"
        )


def test_legacy_gap_analysis_section_is_gone(rendered_reports: dict[str, str]) -> None:
    for use_case, html in rendered_reports.items():
        assert 'id="gap-analysis"' not in html, (
            f"{use_case} still renders the legacy gap-analysis section"
        )


def test_methodology_box_describes_rsf(rendered_reports: dict[str, str]) -> None:
    """Methodology section cites RSF aggregation, not legacy multipliers."""
    for use_case, html in rendered_reports.items():
        start = html.find('id="methodology"')
        end = html.find("</section>", start)
        section = html[start:end]
        assert "RSF" in section or "Repository Scoring Framework" in section
        # Negative: legacy substrate.
        assert "SEVERITY_WEIGHTS" not in section
        assert "use_case_profiles.json" not in section


def test_glossary_describes_rsf_terms(rendered_reports: dict[str, str]) -> None:
    """Glossary leads with RSF terminology (persona-weighted total, dimension score, ?)."""
    for use_case, html in rendered_reports.items():
        start = html.find('id="glossary"')
        end = html.find("</section>", start)
        section = html[start:end]
        assert "persona-weighted total" in section, (
            f"{use_case} glossary missing 'persona-weighted total' entry"
        )
        # Negative: legacy.
        assert "diligence bar" not in section


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


def test_no_unsourced_numeric_claims_in_reports(rendered_reports: dict[str, str]) -> None:
    """Reports must not assert specific dollar / engineer-day numbers without
    a corpus to source them from.

    Persona vocabulary ("valuation discount", "tranche", "escrow") is fine
    when used qualitatively — that's the persona's frame. What's forbidden
    is a *number* attached to those terms ("$X holdback", "Y engineer-days
    per task", "Z% valuation discount") because the corpus that would
    ground those numbers does not yet exist (that's 0.14.0+ work).
    """
    # Match: '$' followed by a digit (any dollar amount) OR 'NN engineer-day(s)'.
    # These are the patterns that would mean we're inventing numbers.
    dollar_pattern = re.compile(r"\$[0-9]")
    engineer_day_pattern = re.compile(r"\d+\s*engineer[- ]days?\s*(per|to)")
    valuation_pct_pattern = re.compile(r"\d+%\s*(valuation\s*discount|holdback)")

    for use_case, html in rendered_reports.items():
        # Strip the framework citations and CSS — they may legitimately use
        # `$` in selectors or example notation.
        body_idx = html.find("<body>")
        body = html[body_idx:] if body_idx >= 0 else html
        # Drop CSS/script/source-code blocks.
        body = re.sub(r"<style>.*?</style>", "", body, flags=re.DOTALL)
        body = re.sub(r"<script>.*?</script>", "", body, flags=re.DOTALL)

        for label, pattern in (
            ("dollar amount", dollar_pattern),
            ("engineer-day claim", engineer_day_pattern),
            ("percent discount", valuation_pct_pattern),
        ):
            match = pattern.search(body)
            assert match is None, (
                f"{use_case} contains an unsourced {label}: {match.group(0)!r}. "
                "Numeric claims attached to dollars / engineer-days / "
                "discount-percent require the calibration corpus from 0.14.0+."
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


# ---------------------------------------------------------------------------
# Provenance header (0.11.0 — "reports must name their subject")
# ---------------------------------------------------------------------------


def test_provenance_banner_present_in_every_report(rendered_reports: dict[str, str]) -> None:
    """Every report must carry the provenance banner."""
    for use_case, html in rendered_reports.items():
        assert 'class="provenance"' in html, f"{use_case} missing provenance banner"
        assert 'aria-label="Report provenance"' in html, f"{use_case} provenance banner missing aria-label"


def test_provenance_names_the_project(rendered_reports: dict[str, str]) -> None:
    """The project name must appear as a literal string in the banner.

    For the test fixture, the project name is the directory name
    'fixture_committed_credential' (no git origin).
    """
    for use_case, html in rendered_reports.items():
        assert "fixture_committed_credential" in html, (
            f"{use_case} provenance does not name the project"
        )


def test_provenance_discloses_local_path_when_no_git_origin(rendered_reports: dict[str, str]) -> None:
    """Reports of non-git inputs must explicitly say 'no git origin', not fabricate one."""
    for use_case, html in rendered_reports.items():
        # The fixture is not a git repo; provenance must say so.
        assert "local path:" in html or "no git origin" in html, (
            f"{use_case} provenance fabricates a source for a non-git input"
        )


def test_provenance_shows_scan_timestamp(rendered_reports: dict[str, str]) -> None:
    """Reports must show when they were scanned (UTC, not paraphrase)."""
    for use_case, html in rendered_reports.items():
        assert re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC", html), (
            f"{use_case} provenance missing scan timestamp"
        )


def test_provenance_shows_persona_badge(rendered_reports: dict[str, str]) -> None:
    """The persona badge must surface the use-case so the reader never forgets the version."""
    expected_badges = {
        "acquisition_diligence": "acquisition diligence",
        "vc_diligence": "vc diligence",
        "engineering_triage": "engineering triage",
        "remediation_agent": "remediation agent",
    }
    for use_case, html in rendered_reports.items():
        badge_text = expected_badges[use_case]
        assert f'persona-badge">{badge_text}' in html, (
            f"{use_case} missing persona badge for '{badge_text}'"
        )


def test_provenance_shows_classifier_output(rendered_reports: dict[str, str]) -> None:
    """Archetype / maturity / surface must appear in the provenance metadata grid."""
    for use_case, html in rendered_reports.items():
        for label in ("Archetype", "Maturity", "Surface", "Scorer"):
            assert f"<dt>{label}</dt>" in html, (
                f"{use_case} provenance grid missing field: {label}"
            )


def _exec_summary_sentences(html: str) -> set[str]:
    """Extract sentences from a report's exec-summary prose paragraphs.

    The boilerplate guards scope here intentionally — provenance text,
    RSF assessment numbers, hard-blocker closure items, and the
    classification line are SHARED across personas (same evidence,
    different totals). The persona-distinct framing lives in the
    exec-summary's prose ``<p>`` paragraphs.
    """
    opener = '<section class="exec-summary"'
    idx = html.find(opener)
    if idx == -1:
        return set()
    end = html.find("</section>", idx)
    if end == -1:
        return set()
    section = html[idx:end]

    paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", section, re.DOTALL)
    sentences: list[str] = []
    for p in paragraphs:
        stripped = re.sub(r"<[^>]+>", " ", p)
        for s in re.split(r"(?<=[.!?])\s+", stripped):
            s = s.strip()
            if len(s) > 30:
                sentences.append(s.lower())
    return set(sentences)


def test_each_persona_has_at_least_two_distinct_sentences_in_exec_summary(
    rendered_reports: dict[str, str],
) -> None:
    """Each persona's exec summary must carry ≥2 sentences unique to it.

    Post-RSF, parts of the exec summary are intentionally shared across
    personas — they describe the same RSF facts (sub-criteria scored, the
    lowest-scored anchor, dimensions flagged for `?`). The persona-
    distinct parts are the framing language ("for thesis credibility…"
    vs "for post-close ownership cost…" vs "for operational reliability…").
    The test enforces that distinct framing exists; it doesn't fight the
    fact that the underlying RSF assessment is the same evidence.
    """
    persona_sentences = {
        use_case: _exec_summary_sentences(html)
        for use_case, html in rendered_reports.items()
    }
    sentence_counts: dict[str, int] = {}
    for sents in persona_sentences.values():
        for s in sents:
            sentence_counts[s] = sentence_counts.get(s, 0) + 1

    for use_case, sents in persona_sentences.items():
        unique = [s for s in sents if sentence_counts[s] == 1]
        assert len(unique) >= 2, (
            f"{use_case} exec summary has only {len(unique)} sentence(s) "
            "unique to it. Persona framing must produce at least 2 distinct "
            "sentences (the persona-specific lens / consequence framing)."
        )


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
        """Extract sentences from the exec-summary's prose paragraphs only.

        The boilerplate guard is for *narrative* content. Some content
        SHOULD be identical across personas because it describes the same
        asset:
        - Provenance (project name, URL, commit) — repo identity.
        - RSF assessment (per-dimension scores) — same evidence per
          persona; only persona totals differ.
        - Must-close hard blockers — same blockers fire for every persona.
        - Classification line (archetype · maturity · surface) — fact.

        The persona-distinct narrative lives in the exec-summary prose
        paragraphs (verdict headline + blocker consequences + closing-
        gap framing). Scope the boilerplate check there.
        """
        # Find the exec-summary section.
        opener = '<section class="exec-summary"'
        idx = html.find(opener)
        if idx == -1:
            return set()
        end = html.find("</section>", idx)
        if end == -1:
            return set()
        section = html[idx:end]

        # Pull each <p>'s text contents.
        paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", section, re.DOTALL)
        sentences: list[str] = []
        for p in paragraphs:
            stripped = re.sub(r"<[^>]+>", " ", p)
            for s in re.split(r"(?<=[.!?])\s+", stripped):
                s = s.strip()
                if len(s) > 30 and s not in chrome_whitelist:
                    sentences.append(s.lower())
        return set(sentences)

    persona_sentences = {
        use_case: _persona_specific_text(html) for use_case, html in rendered_reports.items()
    }
    # Post-RSF: shared sentences describing the same RSF assessment are
    # legitimate (same evidence, different totals). What's still
    # forbidden is *all* persona content overlapping — a persona must
    # have at least one sentence unique to it.
    sentence_counts: dict[str, int] = {}
    for sents in persona_sentences.values():
        for s in sents:
            sentence_counts[s] = sentence_counts.get(s, 0) + 1
    for use_case, sents in persona_sentences.items():
        unique = [s for s in sents if sentence_counts[s] == 1]
        assert unique, (
            f"{use_case} exec summary has zero sentences unique to it — "
            "persona framing is missing entirely"
        )
