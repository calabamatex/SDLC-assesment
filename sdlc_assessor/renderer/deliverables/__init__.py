"""Persona-distinct deliverable builders (SDLC-073..077).

Importing this package registers all four shipped builders with the
dispatcher in :mod:`sdlc_assessor.renderer.deliverables.base`.
"""

from __future__ import annotations

from sdlc_assessor.renderer.deliverables import (  # noqa: F401  — registers builders
    acquisition,
    engineering,
    remediation,
    vc,
)
from sdlc_assessor.renderer.deliverables.base import (
    CategoryArithmetic,
    Citation,
    CostFrame,
    CoverPage,
    Deliverable,
    EngineeringAppendix,
    GapAnalysis,
    GlossaryEntry,
    MethodologyNote,
    ProvenanceHeader,
    Recommendation,
    RecommendationOption,
    RecommendationVerdict,
    ScoreDecomposition,
    Section,
    SectionFact,
    build_deliverable,
    deliverable_to_dict,
    register_deliverable_builder,
    registered_deliverables,
)

__all__ = [
    "CategoryArithmetic",
    "Citation",
    "CostFrame",
    "CoverPage",
    "Deliverable",
    "EngineeringAppendix",
    "GapAnalysis",
    "GlossaryEntry",
    "MethodologyNote",
    "ProvenanceHeader",
    "Recommendation",
    "RecommendationOption",
    "RecommendationVerdict",
    "ScoreDecomposition",
    "Section",
    "SectionFact",
    "build_deliverable",
    "deliverable_to_dict",
    "register_deliverable_builder",
    "registered_deliverables",
]
