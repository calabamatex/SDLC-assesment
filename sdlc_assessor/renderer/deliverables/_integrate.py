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
from sdlc_assessor.renderer.deliverables.base import Deliverable


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

    return deliverable


__all__ = ["apply_depth_pass"]
