"""Top-level RSF entry point: ``assess_repository``.

Implementation note: this module is in active development. The
per-criterion scorers (mapping detector signals → 0..5 anchors per RSF
sub-criterion) are added in the next commit. For now, this module exposes
the entry point and a placeholder that returns an all-`?` assessment so
the rest of the system can be wired up.
"""

from __future__ import annotations

from sdlc_assessor.rsf.aggregate import (
    UNVERIFIED,
    CriterionScore,
    RSFAssessment,
    aggregate,
)
from sdlc_assessor.rsf.criteria import RSF_CRITERIA


def assess_repository(scored: dict, *, repo_path: str | None = None) -> RSFAssessment:
    """Run the RSF v1.0 assessment against a scored payload.

    The current implementation is a placeholder — every criterion is
    returned as ``?`` (unverified) until the per-criterion scorers are
    wired in. This keeps the framework callable end-to-end while the
    scorers are built.

    The placeholder honours the framework: ``?`` flags every dimension
    for confidence and triggers the "limited confidence" warning on
    every persona. That is the *correct* output for an unanchored
    assessor — the report shows it has no evidence rather than
    inventing a number.
    """
    criterion_scores: list[CriterionScore] = []
    for c in RSF_CRITERIA:
        criterion_scores.append(
            CriterionScore(
                criterion_id=c.id,
                value=UNVERIFIED,
                evidence=[],
                rationale=(
                    "Per-criterion scorer not yet implemented. "
                    "See sdlc_assessor/rsf/score.py — RSF anchoring in progress."
                ),
            )
        )
    return aggregate(criterion_scores)


__all__ = ["assess_repository"]
