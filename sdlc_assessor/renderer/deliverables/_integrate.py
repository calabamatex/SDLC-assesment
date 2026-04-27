"""Glue between the RSF-grounded report layer and the persona builders.

Each persona builder (``acquisition.py`` / ``vc.py`` / ``engineering.py``
/ ``remediation.py``) calls :func:`apply_depth_pass` once after
constructing its base :class:`Deliverable`. The function attaches the
:class:`MethodologyNote`, glossary slice, citation list, and the
executive-summary paragraphs.

Post-RSF: the legacy ``ScoreDecomposition`` and ``GapAnalysis`` were
removed because they used the made-up 0–100 rubric that RSF supersedes.
Per-dimension scoring lives in ``scored["rsf"]["dimensions"]`` (real
0–5 anchors); persona-weighted totals live in ``scored["rsf"]["personas"]``;
the executive summary cites those instead of the legacy thresholds.
"""

from __future__ import annotations

from sdlc_assessor.renderer.deliverables._citations import CitationRegistry
from sdlc_assessor.renderer.deliverables._exec_summary import build_executive_summary
from sdlc_assessor.renderer.deliverables._methodology import (
    glossary_for,
    methodology_for,
)
from sdlc_assessor.renderer.deliverables._persona_translations import (
    PersonaTranslation,
    translation_for,
)
from sdlc_assessor.renderer.deliverables.base import Deliverable, Section


def apply_depth_pass(
    deliverable: Deliverable,
    *,
    scored: dict,
    use_case_profile: dict,
) -> Deliverable:
    """Attach the RSF-grounded report fields to ``deliverable`` in place.

    Returns the same Deliverable for chaining. Idempotent — re-running
    rebuilds the fields from ``scored`` + the profile and overwrites
    whatever was attached previously.
    """
    use_case = deliverable.use_case
    citations = CitationRegistry()

    methodology = methodology_for(scored, use_case)
    glossary = glossary_for(use_case)

    executive_summary = build_executive_summary(
        use_case=use_case,
        scored=scored,
        deliverable=deliverable,
        verdict=deliverable.cover.recommendation,
        citations=citations,
    )

    # Legacy fields kept on the dataclass for back-compat but no longer
    # populated — anything that reads them now sees None and falls back
    # cleanly. The HTML renderer no longer renders them.
    deliverable.score_decomposition = None
    deliverable.gap = None
    deliverable.methodology = methodology
    deliverable.glossary = list(glossary)
    deliverable.executive_summary = executive_summary
    deliverable.citations = citations.as_list()

    # Persona-contextual translation of RSF top-5 findings: insert as a body
    # section so the persona's reader sees the lowest-scored RSF anchors
    # translated into their own frame (investment / liability / sprint /
    # imperative). This is the user's explicit "thin → contextualized" ask.
    translation_section = _build_persona_translation_section(
        scored=scored, use_case=use_case
    )
    if translation_section is not None:
        # Insert near the front of body sections so it dominates the body
        # narrative (after cover + RSF block + exec summary, which the HTML
        # renderer places before sections).
        deliverable.sections.insert(0, translation_section)

    return deliverable


def _build_persona_translation_section(
    *, scored: dict, use_case: str
) -> Section | None:
    """Build a `kind="persona_translation"` Section for the top-5 RSF findings.

    Reads the RSF assessment from ``scored["rsf"]``; sorts sub-criteria by
    score (lowest first, real-anchor only — `?` and `N/A` excluded); takes
    the first 5; resolves persona-specific consequence + action text per
    criterion via the translation map. Falls back to generic translation
    built from the RSF level-anchor text when no custom translation is
    registered.

    Returns None when the RSF block isn't attached or no real-anchor
    sub-criteria scored.
    """
    rsf = (scored.get("rsf") or {})
    dimensions = rsf.get("dimensions") or []
    real_scored: list[dict] = []
    for d in dimensions:
        for c in d.get("criteria") or []:
            v = c.get("value")
            if isinstance(v, int) and 0 <= v <= 5:
                real_scored.append({**c, "_dimension_title": d.get("title", "")})
    if not real_scored:
        return None

    real_scored.sort(key=lambda c: (c["value"], c["criterion_id"]))
    top_five = real_scored[:5]

    items: list[dict] = []
    for c in top_five:
        crit_id = c["criterion_id"]
        translation = translation_for(crit_id, use_case)
        if translation is None:
            translation = _generic_translation(c, use_case)
        items.append(
            {
                "criterion_id": crit_id,
                "score": c["value"],
                "dimension_title": c["_dimension_title"],
                "level_anchor_rationale": c.get("rationale", ""),
                "evidence": list(c.get("evidence", []))[:3],
                "consequence": translation.consequence,
                "action": translation.action,
                "framework_ref": translation.framework_ref,
            }
        )

    return Section(
        title="Top RSF findings — translated for this report's reader",
        kind="persona_translation",
        summary=(
            "The five lowest-scored RSF sub-criteria, translated into "
            "the consequence and action framing this persona's reader "
            "actually decides on. Same evidence, different lens. Every "
            "framework reference is a citation to the published spec — "
            "not invented."
        ),
        data={"items": items, "use_case": use_case},
    )


def _generic_translation(
    criterion: dict, use_case: str
) -> PersonaTranslation:
    """Fallback translation built from the RSF rationale + persona lens.

    Used when no persona-specific entry exists in the translation map.
    Keeps the criterion's own level-anchor text; wraps it with a generic
    persona-framed consequence + action statement.
    """
    rationale = criterion.get("rationale", "")
    score = criterion.get("value", 0)
    crit_id = criterion.get("criterion_id", "?")

    if use_case == "vc_diligence":
        consequence = (
            f"At {score}/5 on {crit_id}, this is a thesis-credibility gap "
            "the founder should be prepared to discuss before term-sheet."
        )
        action = (
            "Surface in the founder Q&A; tie remediation to a fundable "
            "milestone."
        )
    elif use_case == "acquisition_diligence":
        consequence = (
            f"At {score}/5 on {crit_id}, this is an inheritable cost on close "
            "and a candidate for escrow conditions or seller-funded remediation."
        )
        action = (
            "Pre-close: name the closure path. Day-30: integrate the fix into "
            "the acquirer's standard pipeline."
        )
    elif use_case == "engineering_triage":
        consequence = (
            f"At {score}/5 on {crit_id}, this is a sprint candidate. The "
            "RSF level-anchor describes the gap; the next level up describes "
            "the lift."
        )
        action = (
            "Plan into the next sprint or two; close-out tracked as a "
            "team metric."
        )
    elif use_case == "remediation_agent":
        consequence = (
            f"Score {score}/5 on {crit_id} — RSF anchor: {rationale}"
        )
        action = (
            "Open a remediation task targeting the next level up; "
            "verification command per the criterion's framework reference."
        )
    else:
        consequence = (
            f"Score {score}/5 on {crit_id}. See the RSF level-anchor in the "
            "report for the gap definition."
        )
        action = "Plan remediation per the criterion's framework reference."

    return PersonaTranslation(
        consequence=consequence,
        action=action,
        framework_ref=f"RSF {crit_id} level anchor (see docs/frameworks/rsf_v1.0.md §2)",
    )


__all__ = ["apply_depth_pass"]
