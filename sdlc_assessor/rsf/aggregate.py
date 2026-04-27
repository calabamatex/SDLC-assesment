"""RSF v1.0 aggregation: per-dimension means + persona-weighted totals.

Implements RSF §4 verbatim:

    D_i = (Σ_j s_ij) / (n_i · 5) × 5      # mean of sub-criterion scores, on the 0–5 scale
    T   = Σ_i D_i · w_i                    # 0–500 scale
    T_% = T / 500 × 100                    # 0–100% executive view

`?` is treated as 0 for scoring but flagged separately. `N/A` is excluded
from the dimension's denominator. Confidence flag fires per RSF §4 when
≥1 sub-criterion is `?` in a dimension; the report-level "limited
confidence" warning fires when >25% of total weight maps to flagged
dimensions.
"""

from __future__ import annotations

from dataclasses import dataclass

from sdlc_assessor.rsf.criteria import RSF_DIMENSIONS, RSF_VERSION
from sdlc_assessor.rsf.personas import (
    RSF_PERSONAS,
    Persona,
    persona_weights_redistributed,
)

# Sentinels for special values. Using strings rather than None so the
# JSON output is unambiguous.
NOT_APPLICABLE = "N/A"
UNVERIFIED = "?"


@dataclass(slots=True)
class CriterionScore:
    """Per-criterion result.

    ``value`` is one of:
    - integer 0..5 — a real assessment against the rubric
    - "N/A" — the criterion does not apply to this asset
    - "?" — evidence could not be collected
    """

    criterion_id: str  # "D1.1", "D2.3", etc.
    value: int | str
    evidence: list[str]  # path / URL / log excerpt the score was based on
    rationale: str  # one-sentence rationale (which level anchor matched)


@dataclass(slots=True)
class DimensionScore:
    """Per-dimension aggregated score (0–5)."""

    dimension_id: str  # "D1"..."D8"
    title: str
    mean: float | None  # 0.0..5.0; None if every sub-criterion is N/A
    n_scored: int  # count of sub-criteria included (excludes N/A)
    n_unverified: int  # count of `?` sub-criteria (treated as 0)
    n_total: int  # total sub-criteria for this dimension (always 3 or 4)
    confidence_flagged: bool  # true if ≥1 sub-criterion is `?`
    criteria: list[CriterionScore]


@dataclass(slots=True)
class PersonaTotal:
    """Per-persona weighted total."""

    persona_id: str
    persona_label: str
    weights_used: dict[str, int]  # actual weights after N/A redistribution
    total: float  # 0..500
    total_pct: float  # 0..100
    confidence_flagged: bool  # true if ≥1 dimension contributing weight is flagged
    limited_confidence_warning: bool  # true if >25% of weight maps to flagged dims


@dataclass(slots=True)
class RSFAssessment:
    """Top-level RSF assessment for a repository."""

    framework_version: str  # "v1.0"
    dimensions: list[DimensionScore]
    personas: list[PersonaTotal]
    na_dimensions: list[str]  # dimensions where every sub-criterion is N/A
    flagged_dimensions: list[str]  # dimensions with ≥1 `?`


def _numeric(value: int | str) -> int:
    """Convert RSF score values to a number for aggregation.

    Per RSF §1: ``?`` is treated as 0 for scoring (and flagged). ``N/A``
    is excluded by the caller (this function should not be called with
    N/A inputs).
    """
    if isinstance(value, str):
        if value == UNVERIFIED:
            return 0
        raise ValueError(f"unexpected RSF score value: {value!r}")
    if not 0 <= value <= 5:
        raise ValueError(f"RSF score out of range: {value!r}")
    return value


def _aggregate_dimension(
    dimension_id: str,
    title: str,
    criterion_scores: list[CriterionScore],
) -> DimensionScore:
    n_total = len(criterion_scores)
    scored: list[int] = []
    n_unverified = 0
    for cs in criterion_scores:
        if cs.value == NOT_APPLICABLE:
            continue
        if cs.value == UNVERIFIED:
            n_unverified += 1
        scored.append(_numeric(cs.value))
    if not scored:
        return DimensionScore(
            dimension_id=dimension_id,
            title=title,
            mean=None,
            n_scored=0,
            n_unverified=n_unverified,
            n_total=n_total,
            confidence_flagged=n_unverified > 0,
            criteria=criterion_scores,
        )
    # RSF §4: D_i = (Σ s_ij) / (n_i · 5) × 5 — which simplifies to the mean.
    mean = sum(scored) / len(scored)
    return DimensionScore(
        dimension_id=dimension_id,
        title=title,
        mean=mean,
        n_scored=len(scored),
        n_unverified=n_unverified,
        n_total=n_total,
        confidence_flagged=n_unverified > 0,
        criteria=criterion_scores,
    )


def _persona_total(
    persona: Persona,
    dimensions: list[DimensionScore],
    na_dimension_ids: set[str],
) -> PersonaTotal:
    weights = persona_weights_redistributed(persona, na_dimensions=na_dimension_ids)

    total = 0.0
    flagged_weight = 0
    confidence_flagged = False
    for dim in dimensions:
        if dim.dimension_id not in weights:
            continue
        if dim.mean is None:
            # Defensive — should not happen since N/A dims are redistributed.
            continue
        weight = weights[dim.dimension_id]
        total += dim.mean * weight
        if dim.confidence_flagged:
            confidence_flagged = True
            flagged_weight += weight

    total_pct = (total / 500.0) * 100.0
    limited_warning = flagged_weight > 25  # RSF §4: >25% of weight flagged

    return PersonaTotal(
        persona_id=persona.id,
        persona_label=persona.label,
        weights_used=weights,
        total=total,
        total_pct=total_pct,
        confidence_flagged=confidence_flagged,
        limited_confidence_warning=limited_warning,
    )


def aggregate(
    criterion_scores: list[CriterionScore],
) -> RSFAssessment:
    """Aggregate a flat list of CriterionScore into a full RSFAssessment.

    Per RSF §4. The list need not be in any order; criteria are bucketed
    by their ``dimension_id`` (the prefix before the dot in the
    criterion_id, e.g., ``D2.3`` → dimension ``D2``).
    """
    by_dimension: dict[str, list[CriterionScore]] = {}
    for cs in criterion_scores:
        dim_id = cs.criterion_id.split(".", 1)[0]
        by_dimension.setdefault(dim_id, []).append(cs)

    dimensions: list[DimensionScore] = []
    for dim in RSF_DIMENSIONS:
        scores = by_dimension.get(dim.id, [])
        dimensions.append(_aggregate_dimension(dim.id, dim.title, scores))

    na_dimension_ids = {d.dimension_id for d in dimensions if d.mean is None}
    flagged_dimension_ids = [d.dimension_id for d in dimensions if d.confidence_flagged]

    personas = [_persona_total(p, dimensions, na_dimension_ids) for p in RSF_PERSONAS]

    return RSFAssessment(
        framework_version=RSF_VERSION,
        dimensions=dimensions,
        personas=personas,
        na_dimensions=sorted(na_dimension_ids),
        flagged_dimensions=flagged_dimension_ids,
    )


def assessment_to_dict(assessment: RSFAssessment) -> dict:
    """JSON-friendly serialization of an RSFAssessment.

    Used by the CLI to attach the RSF result to ``scored.json`` and by
    tests / consumers that need a plain-Python view.
    """
    return {
        "framework_version": assessment.framework_version,
        "dimensions": [
            {
                "dimension_id": d.dimension_id,
                "title": d.title,
                "mean": d.mean,
                "n_scored": d.n_scored,
                "n_unverified": d.n_unverified,
                "n_total": d.n_total,
                "confidence_flagged": d.confidence_flagged,
                "criteria": [
                    {
                        "criterion_id": c.criterion_id,
                        "value": c.value,
                        "evidence": list(c.evidence),
                        "rationale": c.rationale,
                    }
                    for c in d.criteria
                ],
            }
            for d in assessment.dimensions
        ],
        "personas": [
            {
                "persona_id": p.persona_id,
                "persona_label": p.persona_label,
                "weights_used": dict(p.weights_used),
                "total": p.total,
                "total_pct": p.total_pct,
                "confidence_flagged": p.confidence_flagged,
                "limited_confidence_warning": p.limited_confidence_warning,
            }
            for p in assessment.personas
        ],
        "na_dimensions": list(assessment.na_dimensions),
        "flagged_dimensions": list(assessment.flagged_dimensions),
    }


__all__ = [
    "CriterionScore",
    "DimensionScore",
    "NOT_APPLICABLE",
    "PersonaTotal",
    "RSFAssessment",
    "UNVERIFIED",
    "aggregate",
    "assessment_to_dict",
]
