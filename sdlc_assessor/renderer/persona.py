"""Persona-aware narrative dispatch (SDLC-068).

Each use-case profile in ``profiles/data/use_case_profiles.json`` declares a
``narrative_emphasis`` list — the report subjects this persona cares about.
For ``acquisition_diligence`` that means *integration risk*, *maintenance
burden*, *release hygiene*, *dependency concentration*, *knowledge-transfer
risk*. For ``vc_diligence`` it's *credibility*, *technical moat support*,
*execution maturity*, *risk concentration*, *overclaim detection*. Etc.

This module turns those terms into structured narrative blocks pulled from
the scored payload. Renderers (Markdown, HTML, JSON) consume the blocks;
none of them invent prose.

The four use-case profiles span 18 distinct emphasis terms; each has a
dedicated builder in :mod:`sdlc_assessor.renderer.narrative_blocks`.
Unknown terms degrade to a generic block built from the strongest findings,
so an organisation can ship a custom profile with new emphasis keys without
breaking the renderer.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field

from sdlc_assessor.normalizer.findings import is_fixture_finding


@dataclass(slots=True)
class NarrativeFact:
    """A quantitative fact pulled from the scored payload (rendered as a bullet)."""

    label: str
    value: str
    severity: str | None = None  # "info" | "low" | "medium" | "high" | "critical" | None


@dataclass(slots=True)
class NarrativeCallout:
    """A call-to-attention box (sometimes a "key risk" line in reports)."""

    severity: str  # critical | high | medium | low | info
    message: str


@dataclass(slots=True)
class NarrativeBlock:
    """One emphasis-driven section in a persona-aware report.

    Each block is a small unit a renderer can drop into a section: a title,
    1–3 sentences of summary prose, a list of quantitative facts, and zero
    or more callouts that warrant attention before proceeding.
    """

    key: str  # the narrative_emphasis term that produced this block
    title: str
    summary: str
    facts: list[NarrativeFact] = field(default_factory=list)
    callouts: list[NarrativeCallout] = field(default_factory=list)


def block_to_dict(block: NarrativeBlock) -> dict:
    """JSON-serialisable form for inclusion in ``scored.json``."""
    return asdict(block)


# Builder dispatch — populated by ``narrative_blocks`` import.
_BUILDERS: dict[str, Callable[[dict, dict], NarrativeBlock]] = {}


def register_builder(key: str, fn: Callable[[dict, dict], NarrativeBlock]) -> None:
    """Bind ``key`` to a narrative-block builder (used by narrative_blocks.py)."""
    _BUILDERS[key] = fn


def registered_keys() -> list[str]:
    return sorted(_BUILDERS)


def narrate_for_persona(scored: dict, use_case_profile: dict) -> list[NarrativeBlock]:
    """Produce one :class:`NarrativeBlock` per ``narrative_emphasis`` term.

    Unknown terms fall through to :func:`_generic_block`. Every block is
    grounded in the scored payload — no LLM, no invented content.
    """
    # Force registration if a renderer imported persona before narrative_blocks.
    from sdlc_assessor.renderer import narrative_blocks  # noqa: F401

    emphasis: Iterable[str] = use_case_profile.get("narrative_emphasis") or ()
    blocks: list[NarrativeBlock] = []
    for key in emphasis:
        builder = _BUILDERS.get(_normalize_key(key))
        if builder is None:
            blocks.append(_generic_block(key, scored))
        else:
            blocks.append(builder(scored, use_case_profile))
    return blocks


def _normalize_key(key: str) -> str:
    """Normalize an emphasis term to a builder lookup key.

    Profile JSONs may use space-separated phrases ("integration risk") or
    snake_case keys; both should resolve. We canonicalise to snake_case.
    """
    return key.strip().lower().replace(" ", "_").replace("-", "_")


# ---------------------------------------------------------------------------
# Helpers shared across builders
# ---------------------------------------------------------------------------

_SEVERITY_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def production_findings(scored: dict) -> list[dict]:
    """All findings minus fixture/example/vendor-tagged ones."""
    return [f for f in (scored.get("findings") or []) if not is_fixture_finding(f)]


def critical_blockers(scored: dict) -> list[dict]:
    return [b for b in (scored.get("hard_blockers") or []) if b.get("severity") == "critical"]


def high_blockers(scored: dict) -> list[dict]:
    return [b for b in (scored.get("hard_blockers") or []) if b.get("severity") == "high"]


def category_score(scored: dict, category: str) -> dict | None:
    for entry in (scored.get("scoring") or {}).get("category_scores", []) or []:
        if isinstance(entry, dict) and entry.get("category") == category:
            return entry
    return None


def top_findings(scored: dict, *, n: int, only_subcategories: set[str] | None = None) -> list[dict]:
    findings = production_findings(scored)
    if only_subcategories:
        findings = [f for f in findings if f.get("subcategory") in only_subcategories]

    def _rank(f: dict) -> tuple:
        sev = _SEVERITY_RANK.get(f.get("severity", "info"), 0)
        conf = {"high": 1.0, "medium": 0.9, "low": 0.7}.get(f.get("confidence", "medium"), 0.0)
        mag = float(f.get("score_impact", {}).get("magnitude", 0)) / 10.0
        return (-(sev * conf * mag), f.get("category", ""), f.get("subcategory", ""))

    return sorted(findings, key=_rank)[:n]


def count_by_subcategory(scored: dict, subcategories: set[str]) -> int:
    return sum(1 for f in production_findings(scored) if f.get("subcategory") in subcategories)


def find_one(scored: dict, subcategory: str) -> dict | None:
    for f in production_findings(scored):
        if f.get("subcategory") == subcategory:
            return f
    return None


# ---------------------------------------------------------------------------
# Generic fallback (used when a profile ships an unknown emphasis term)
# ---------------------------------------------------------------------------


def _generic_block(key: str, scored: dict) -> NarrativeBlock:
    title = key.replace("_", " ").replace("-", " ").strip().title() or "Risk Surface"
    top = top_findings(scored, n=3)
    facts = [
        NarrativeFact(
            label=(f.get("subcategory") or "").replace("_", " ").title() or "Finding",
            value=(f.get("statement") or "").rstrip("."),
            severity=f.get("severity"),
        )
        for f in top
    ]
    if facts:
        summary = (
            f"No persona-specific narrative for emphasis term “{key}”; "
            f"falling back to the {len(facts)} highest-impact production findings."
        )
    else:
        summary = (
            f"No persona-specific narrative for emphasis term “{key}”, "
            "and no production findings to surface."
        )
    return NarrativeBlock(key=key, title=title, summary=summary, facts=facts)


__all__ = [
    "NarrativeBlock",
    "NarrativeCallout",
    "NarrativeFact",
    "block_to_dict",
    "category_score",
    "count_by_subcategory",
    "critical_blockers",
    "find_one",
    "high_blockers",
    "narrate_for_persona",
    "production_findings",
    "register_builder",
    "registered_keys",
    "top_findings",
]
