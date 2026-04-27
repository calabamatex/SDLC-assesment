"""Tests for the persona-contextual translation of RSF top-5 findings.

Asserts:
- Each persona's report contains persona-distinct translation prose for
  each top-5 finding (different framing per persona for the same RSF
  criterion).
- The translation map covers the criteria most likely to fire (D2.2,
  D2.3, D3.1, D3.2, D3.4, D5.4, D6.1–D6.4, D7.1, D7.2, D7.4).
- The fallback for uncovered criteria is invoked when no entry exists
  in the map.
- Every translation carries a published-framework reference (no
  invented content).
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

import pytest

from sdlc_assessor.renderer.deliverables._persona_translations import (
    PersonaTranslation,
    covered_criteria,
    translation_for,
)


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Translation map integrity
# ---------------------------------------------------------------------------


def test_covered_criteria_includes_high_frequency_set() -> None:
    """The translation map must cover the criteria that fire most often."""
    expected_minimum = {
        "D2.2", "D2.3", "D3.1", "D3.2", "D3.4",
        "D5.4", "D6.1", "D6.2", "D6.3", "D6.4",
        "D7.1", "D7.2", "D7.4",
    }
    missing = expected_minimum - covered_criteria()
    assert not missing, f"translation map missing high-frequency criteria: {sorted(missing)}"


@pytest.mark.parametrize(
    "use_case",
    ["acquisition_diligence", "vc_diligence", "engineering_triage", "remediation_agent"],
)
def test_every_covered_criterion_has_all_four_personas(use_case: str) -> None:
    """Every covered criterion must have an entry for every persona."""
    for crit_id in covered_criteria():
        entry = translation_for(crit_id, use_case)
        assert entry is not None, f"{crit_id}/{use_case} missing translation"
        assert isinstance(entry, PersonaTranslation)
        assert entry.consequence
        assert entry.action
        assert entry.framework_ref


def test_every_translation_carries_a_published_framework_ref() -> None:
    """The framework_ref field is the audit trail — never empty."""
    from sdlc_assessor.renderer.deliverables._persona_translations import _TRANSLATIONS

    for crit_id, persona_map in _TRANSLATIONS.items():
        for persona, translation in persona_map.items():
            assert translation.framework_ref, (
                f"{crit_id}/{persona} has empty framework_ref — "
                "every translation must cite a published reference"
            )
            # Cheap sanity-check that it cites real frameworks.
            text = translation.framework_ref
            recognized = any(
                anchor in text
                for anchor in (
                    "OWASP", "NIST", "DORA", "CWE", "CVSS", "SLSA",
                    "Sigstore", "CycloneDX", "SPDX", "OpenSSF", "ISO",
                    "AICPA", "CSA", "Rekor", "CodeScene", "CNCF",
                    "OpenChain", "Apache",
                )
            )
            assert recognized, (
                f"{crit_id}/{persona} framework_ref doesn't cite a recognized "
                f"published framework: {text!r}"
            )


def test_translations_are_persona_distinct() -> None:
    """For each criterion, the four personas' consequence text must differ."""
    from sdlc_assessor.renderer.deliverables._persona_translations import _TRANSLATIONS

    for crit_id, persona_map in _TRANSLATIONS.items():
        consequences = {
            persona: t.consequence for persona, t in persona_map.items()
        }
        # All four consequences must be unique strings.
        unique_consequences = set(consequences.values())
        assert len(unique_consequences) == len(consequences), (
            f"{crit_id} has duplicate consequence prose across personas: "
            f"{[k for k, v in consequences.items() if list(consequences.values()).count(v) > 1]}"
        )


def test_translation_for_unknown_criterion_returns_none() -> None:
    """The lookup helper returns None for criteria not in the map."""
    assert translation_for("D99.99", "vc_diligence") is None


def test_translation_for_unknown_persona_returns_none() -> None:
    """The lookup helper returns None for personas not in the map."""
    assert translation_for("D2.2", "unknown_persona") is None


# ---------------------------------------------------------------------------
# Integration: rendered reports actually carry persona-distinct text
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def rendered_reports(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    """Render all four persona reports against fixture_committed_credential."""
    fixture = REPO_ROOT / "tests" / "fixtures" / "fixture_committed_credential"
    out_root = tmp_path_factory.mktemp("persona_translation")

    rendered: dict[str, str] = {}
    for use_case in (
        "acquisition_diligence", "vc_diligence",
        "engineering_triage", "remediation_agent",
    ):
        out_dir = out_root / use_case
        cmd = [
            sys.executable,
            "-m", "sdlc_assessor.cli",
            "run",
            str(fixture),
            "--use-case", use_case,
            "--format", "html",
            "--out-dir", str(out_dir),
        ]
        subprocess.run(cmd, check=True, capture_output=True, cwd=str(REPO_ROOT))
        rendered[use_case] = (out_dir / "report.html").read_text(encoding="utf-8")
    return rendered


def test_persona_translation_section_present(rendered_reports: dict[str, str]) -> None:
    for use_case, html in rendered_reports.items():
        assert 'class="persona-translation"' in html, (
            f"{use_case} missing persona-translation section"
        )
        # Each report should have at least one card.
        assert html.count('class="pt-card"') >= 1, (
            f"{use_case} has no persona-translation cards"
        )


def test_persona_translation_carries_framework_refs(rendered_reports: dict[str, str]) -> None:
    """Every report's translation cards must cite published frameworks."""
    for use_case, html in rendered_reports.items():
        # Extract framework_ref text from rendered cards.
        refs = re.findall(r'class="pt-framework-ref">.*?<code>([^<]+)</code>', html)
        assert refs, f"{use_case} has no framework references in translation cards"
        # At least one ref must mention a recognized framework.
        recognized = ("NIST", "OWASP", "DORA", "CWE", "CVSS", "SLSA", "OpenSSF", "ISO", "Sigstore", "CycloneDX", "SPDX")
        has_recognized = any(any(anchor in r for anchor in recognized) for r in refs)
        assert has_recognized, (
            f"{use_case} translation cards don't cite any recognized framework"
        )


def test_persona_translation_consequence_differs_across_personas(
    rendered_reports: dict[str, str],
) -> None:
    """For shared criteria, consequence text must differ across the four reports."""
    consequences_by_persona: dict[str, set[str]] = {}
    for use_case, html in rendered_reports.items():
        # Match the consequence text in each card.
        matches = re.findall(
            r'<strong>What this means here:</strong>\s*([^<]+)',
            html,
        )
        # Strip whitespace + lowercase for comparison.
        consequences_by_persona[use_case] = {m.strip().lower() for m in matches}

    # No persona should have zero consequences (means the section is empty).
    for use_case, consequences in consequences_by_persona.items():
        assert consequences, f"{use_case} has zero persona-translation consequences"

    # Look at the union: each pair of personas should share <50% of consequences
    # (some criteria may have similar generic-fallback prose, but custom-mapped
    # criteria — the high-frequency ones — produce distinct text).
    personas = list(consequences_by_persona.keys())
    for i, persona_a in enumerate(personas):
        for persona_b in personas[i + 1:]:
            a = consequences_by_persona[persona_a]
            b = consequences_by_persona[persona_b]
            shared = a & b
            total = a | b
            if total:
                shared_ratio = len(shared) / len(total)
                assert shared_ratio < 0.5, (
                    f"{persona_a} and {persona_b} share {shared_ratio:.0%} of "
                    f"consequence prose ({len(shared)}/{len(total)}); "
                    "translation isn't persona-distinct enough"
                )


def test_persona_translation_includes_score_and_anchor(
    rendered_reports: dict[str, str],
) -> None:
    """Each card shows the RSF score badge + the level-anchor text."""
    for use_case, html in rendered_reports.items():
        # Score badges (e.g., '0/5', '1/5').
        scores = re.findall(r'class="pt-score[^"]*">(\d/5)<', html)
        assert scores, f"{use_case} translation cards have no score badges"
        # Level-anchor rationale should appear.
        assert "RSF level anchor matched:" in html, (
            f"{use_case} cards missing RSF level-anchor text"
        )
