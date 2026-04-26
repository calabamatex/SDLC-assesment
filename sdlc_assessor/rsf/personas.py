"""RSF v1.0 persona weight matrix.

Reproduced verbatim from ``docs/frameworks/rsf_v1.0.md`` §3. Each row
sums to 100. ``N/A`` dimensions redistribute proportionally across the
remaining dimensions per the framework's aggregation rule.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Persona:
    """One of the 8 RSF consumer personas, with per-dimension weights."""

    id: str  # snake_case canonical id used in code / CLI flags
    label: str  # display label as shown in the RSF doc header row
    rationale: str  # one-line rationale from RSF v1.0 §3 "Rationale anchors"
    weights: dict[str, int]  # {"D1": 15, "D2": 20, ...} — must sum to 100


# Persona weights from the RSF v1.0 §3 matrix. Verbatim.

RSF_PERSONAS: tuple[Persona, ...] = (
    Persona(
        id="vc",
        label="VC",
        rationale=(
            "VC weights security, code quality, and discipline highest because "
            "cost-to-cure dominates valuation impact; compliance is light because "
            "most VC targets are pre-regulatory."
        ),
        weights={
            "D1": 15, "D2": 20, "D3": 10, "D4": 15,
            "D5": 15, "D6": 10, "D7": 10, "D8": 5,
        },
    ),
    Persona(
        id="pe_ma",
        label="PE/M&A",
        rationale=(
            "PE/M&A shifts weight from raw delivery to compliance and supply "
            "chain: the buyer inherits regulatory risk."
        ),
        weights={
            "D1": 15, "D2": 20, "D3": 15, "D4": 10,
            "D5": 10, "D6": 5, "D7": 5, "D8": 20,
        },
    ),
    Persona(
        id="cto_vp_eng",
        label="CTO/VP Eng",
        rationale=(
            "CTO/VP Eng weights delivery and discipline highest; this is the "
            "operational lens."
        ),
        weights={
            "D1": 10, "D2": 15, "D3": 10, "D4": 25,
            "D5": 20, "D6": 5, "D7": 5, "D8": 10,
        },
    ),
    Persona(
        id="eng_mgr",
        label="Eng Mgr",
        rationale=(
            "Eng Mgr concentrates on D4/D5/D1 (the daily flow); compliance is "
            "org's problem."
        ),
        weights={
            "D1": 15, "D2": 10, "D3": 5, "D4": 25,
            "D5": 25, "D6": 10, "D7": 10, "D8": 0,
        },
    ),
    Persona(
        id="ciso",
        label="CISO",
        rationale="CISO weights security, supply chain, and compliance highest.",
        weights={
            "D1": 5, "D2": 30, "D3": 20, "D4": 5,
            "D5": 10, "D6": 5, "D7": 5, "D8": 20,
        },
    ),
    Persona(
        id="procurement",
        label="Procurement",
        rationale=(
            "Procurement mirrors CISO but with stronger compliance emphasis "
            "(vendor onboarding gating)."
        ),
        weights={
            "D1": 5, "D2": 25, "D3": 20, "D4": 5,
            "D5": 10, "D6": 10, "D7": 5, "D8": 20,
        },
    ),
    Persona(
        id="oss_user",
        label="OSS user",
        rationale=(
            "OSS user weights supply chain, sustainability, and documentation; "
            "this consumer cannot influence delivery cadence and rarely has "
            "compliance interest."
        ),
        weights={
            "D1": 10, "D2": 15, "D3": 25, "D4": 5,
            "D5": 15, "D6": 15, "D7": 15, "D8": 0,
        },
    ),
    Persona(
        id="c_level_non_tech",
        label="C-level non-tech",
        rationale=(
            "C-level non-tech weights compliance highest because liability and "
            "audit posture dominate their lens; balanced across delivery and "
            "security as risk inputs."
        ),
        weights={
            "D1": 5, "D2": 15, "D3": 5, "D4": 15,
            "D5": 10, "D6": 5, "D7": 10, "D8": 35,
        },
    ),
)


def persona_by_id(persona_id: str) -> Persona:
    """Look up a persona by its snake_case id."""
    for p in RSF_PERSONAS:
        if p.id == persona_id:
            return p
    raise KeyError(f"unknown RSF persona: {persona_id!r}")


def persona_weights_redistributed(
    persona: Persona, *, na_dimensions: set[str]
) -> dict[str, int]:
    """Redistribute weight from ``N/A`` dimensions across the remaining ones.

    Per RSF v1.0 §3: *"`N/A` dimensions (typically D8 for many internal
    contexts) redistribute proportionally across remaining weights."*

    The redistribution preserves the relative weighting of the remaining
    dimensions so the total sums to 100.
    """
    if not na_dimensions:
        return dict(persona.weights)

    remaining_total = sum(
        w for dim_id, w in persona.weights.items() if dim_id not in na_dimensions
    )
    if remaining_total == 0:
        # Defensive: persona had all weight on N/A dimensions. Distribute
        # equally across whatever dimensions remain in the matrix.
        remaining = [d for d in persona.weights if d not in na_dimensions]
        if not remaining:
            return {}
        share = 100 // len(remaining)
        out = {d: share for d in remaining}
        # Make it sum to exactly 100 by topping up the first.
        if remaining:
            out[remaining[0]] += 100 - share * len(remaining)
        return out

    # Scale each remaining dimension proportionally.
    redistributed: dict[str, int] = {}
    running_total = 0
    remaining_dims = [d for d in persona.weights if d not in na_dimensions]
    for dim_id in remaining_dims[:-1]:
        share = round(persona.weights[dim_id] * 100 / remaining_total)
        redistributed[dim_id] = share
        running_total += share
    # Last dim absorbs the rounding remainder so the total is exactly 100.
    if remaining_dims:
        redistributed[remaining_dims[-1]] = 100 - running_total
    return redistributed


__all__ = [
    "Persona",
    "RSF_PERSONAS",
    "persona_by_id",
    "persona_weights_redistributed",
]
