"""Repository Scoring Framework (RSF) v1.0 implementation.

Source of truth: ``docs/frameworks/rsf_v1.0.md`` (provided by the user as
the canonical scoring framework). Every value in this package — criterion
anchors, persona weights, dimension definitions — is reproduced verbatim
from that document. No values come from training-data memory.

Public API:

- :func:`assess_repository` — top-level entry. Takes a repo path + the
  collected evidence (scored.json + classification + remediation_plan)
  and returns a :class:`RSFAssessment` with per-criterion scores,
  per-dimension means, per-persona weighted totals, and confidence flag.
- :data:`RSF_CRITERIA` — the 31 sub-criteria with their level anchors.
- :data:`RSF_PERSONAS` — the 8 personas with their weight matrix.
- :data:`RSF_VERSION` — the framework version string.
"""

from __future__ import annotations

from sdlc_assessor.rsf.aggregate import (
    DimensionScore,
    PersonaTotal,
    RSFAssessment,
    aggregate,
)
from sdlc_assessor.rsf.criteria import (
    RSF_CRITERIA,
    RSF_DIMENSIONS,
    RSF_VERSION,
    Criterion,
    CriterionLevel,
    Dimension,
)
from sdlc_assessor.rsf.personas import (
    RSF_PERSONAS,
    Persona,
    persona_weights_redistributed,
)
from sdlc_assessor.rsf.score import assess_repository

__all__ = [
    "Criterion",
    "CriterionLevel",
    "Dimension",
    "DimensionScore",
    "Persona",
    "PersonaTotal",
    "RSFAssessment",
    "RSF_CRITERIA",
    "RSF_DIMENSIONS",
    "RSF_PERSONAS",
    "RSF_VERSION",
    "aggregate",
    "assess_repository",
    "persona_weights_redistributed",
]
