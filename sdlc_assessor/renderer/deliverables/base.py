"""Persona-deliverable framework (SDLC-073).

The v0.9.0 renderer was persona-aware at the *narrative-block* level — it
pulled different facts into a single fixed page layout. The user's
feedback was correct: that's not a deliverable, it's a flexible bug list.

A deliverable is a *document shape*. An acquisition memo and a VC thesis
evaluation answer different questions in different orders for different
readers, even when they cite the same evidence. This module models that.

Shape
-----

Each persona produces a :class:`Deliverable` consisting of:

- :class:`CoverPage` — recommendation pill, headline metric (the score
  gauge SVG), the 3–5 facts the reader needs before turning the page.
- A list of :class:`Section` objects — ordered, persona-specific body
  sections. Each section can contain:
    * prose paragraphs (str, already escaped where needed),
    * narrative facts (small tables or callout strips),
    * an SVG chart,
    * a structured ``data`` payload (e.g., a SWOT or a Day-30/60/90 plan
      that the renderer formats),
    * a list of :class:`Recommendation` rows.
- :class:`Recommendation` rows — what to do, with an option ladder
  (``Proceed`` / ``Proceed with conditions`` / ``Defer`` /
  ``Decline``), each option qualified by what would have to be true.
- :class:`EngineeringAppendix` — a pointer/handle to the deep finding
  list and category scoring matrix; renderers compose this from the
  scored payload directly so deliverables stay small.

Builders
--------

The four shipped builders live in:
:mod:`sdlc_assessor.renderer.deliverables.acquisition` (memo),
:mod:`...vc` (thesis evaluation),
:mod:`...engineering` (health report),
:mod:`...remediation` (action plan).

Unknown ``use_case`` values fall back to a generic deliverable derived
from the persona-narrative blocks alone, so a custom profile shipped by
an organisation degrades gracefully instead of crashing.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Literal

from sdlc_assessor.renderer.persona import NarrativeBlock

RecommendationVerdict = Literal[
    "proceed",
    "proceed_with_conditions",
    "defer",
    "decline",
]


@dataclass(slots=True)
class CoverPage:
    """The page-1 callout — what the reader needs before turning the page."""

    title: str
    subtitle: str
    recommendation: RecommendationVerdict
    recommendation_rationale: str  # 1–2 sentences. Plain English.
    score: int
    score_band: str  # "fail" | "conditional" | "pass" | "distinction"
    headline_facts: list[tuple[str, str]] = field(default_factory=list)
    score_gauge_svg: str = ""
    classification_line: str = ""  # "Service · production maturity · networked"


# ---------------------------------------------------------------------------
# 0.11.0 depth-pass dataclasses (SDLC-081..087)
#
# These types support the depth pass that addresses the user's feedback that
# the v0.10.0 reports talk *around* numbers without showing them. Each new
# section of the report (executive summary prose, methodology box, score
# decomposition table, gap analysis, cost frame, glossary, citations) maps
# to one of the dataclasses below.
#
# Plan reference: /Users/ethanallen/.claude/plans/users-ethanallen-...md,
# Phase 0 (0.11.0 depth pass), Section A.
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Citation:
    """A claim → evidence pointer for the in-prose superscript footnotes.

    ``claim_id`` is a stable string (e.g. ``"score_below_bar"``) so
    builders can cite the same claim in the executive summary and the
    methodology box and have the renderer resolve them to the same
    footnote number.
    """

    claim_id: str
    text: str
    evidence_refs: list[str] = field(default_factory=list)  # ["scoring.overall_score=59", ...]
    source_files: list[tuple[str, int | None]] = field(default_factory=list)


@dataclass(slots=True)
class CategoryArithmetic:
    """One row in the score-decomposition table.

    Reconstructs ``earned = base_max × multiplier × applicability − Σ deductions``
    so the reader can audit how the 12/20 (etc.) actually got there.
    """

    category: str
    label: str  # persona-relabelled (from PersonaVocab.category_labels)
    base_max: int  # from BASE_WEIGHTS in scorer.engine
    multiplier: float  # use-case category_multiplier
    applicability: str  # "applicable" | "partial" | "not_applicable"
    earned: float
    deductions: list[dict] = field(default_factory=list)  # [{finding_id, severity_w, conf_mult, magnitude, deduction}, ...]
    normalized_weight: int = 0  # rounded post-multiplier weight out of the persona's total weighted_max


@dataclass(slots=True)
class ScoreDecomposition:
    """Full score arithmetic surfaced to the reader.

    Carries every multiplier and weight the scoring engine applied so
    nothing in the report has to handwave at "the diligence bar."
    """

    overall: int
    pass_threshold: int
    distinction_threshold: int
    threshold_source: str  # "use_case_profiles.json:acquisition_diligence.pass_threshold"
    flat_penalties: list[tuple[str, int]] = field(default_factory=list)  # [("missing_tests", 15), ...]
    confidence_multiplier_table: dict[str, float] = field(default_factory=dict)
    severity_weight_table: dict[str, int] = field(default_factory=dict)
    maturity_factor: float = 1.0
    categories: list[CategoryArithmetic] = field(default_factory=list)
    score_confidence: str | None = None  # the scoring.score_confidence value ("low"|"medium"|"high")
    score_confidence_rationale: str = ""


@dataclass(slots=True)
class GapAnalysis:
    """Numeric distance to pass + concrete phases that close it."""

    gap_to_pass: int  # max(0, pass_threshold - overall)
    gap_to_distinction: int  # max(0, distinction_threshold - overall)
    closing_phases: list[dict] = field(default_factory=list)
    # ↑ [{phase: "phase_1_security", task_count: 6, projected_lift: 33.5, after: 92.5, clears: True}]
    minimum_phases_to_pass: list[str] = field(default_factory=list)
    on_call_delta_if_unfixed: str = ""  # engineering persona only; explanatory line


@dataclass(slots=True)
class CostFrame:
    """Engineer-day (and optional dollar) cost per task and per phase.

    Built from ``remediation_plan.tasks[].effort`` and the editorial
    :data:`EFFORT_TO_DAYS` table in :mod:`._cost`. The ``$`` column is
    suppressed at render time when ``blended_engineer_day_rate_usd`` is
    ``None``.
    """

    blended_engineer_day_rate_usd: int | None
    effort_to_engineer_days: dict[str, tuple[float, float]] = field(default_factory=dict)
    per_task_cost: list[dict] = field(default_factory=list)
    # ↑ [{task_id, effort, low_days, high_days, low_usd, high_usd}, ...]
    per_phase_cost: list[dict] = field(default_factory=list)
    total_low_days: float = 0.0
    total_high_days: float = 0.0


@dataclass(slots=True)
class GlossaryEntry:
    """One reader-facing definition rendered in the back-of-doc glossary."""

    term: str
    short_def: str  # 1-line for tooltip / superscript hover
    long_def: str  # paragraph for appendix
    sources: list[str] = field(default_factory=list)  # ["sdlc_assessor/profiles/data/use_case_profiles.json", ...]


@dataclass(slots=True)
class ProvenanceHeader:
    """Identity + scan-context for the report's subject.

    Pinned at the top of every rendered report so the reader knows
    *what* was scanned, *where* it lives, *which commit*, *when*, and
    *with which scorer*. Without this, a diligence document is
    unauditable.
    """

    project_name: str  # e.g. "AgentSentry"
    source_location: str  # e.g. "https://github.com/calabamatex/AgentSentry"
    source_kind: str  # "git_remote" | "local_path" | "explicit"
    commit_sha: str | None  # short or full SHA at scan time, None if not a git checkout
    branch: str | None
    scanned_at: str  # ISO 8601 UTC
    scorer_version: str  # sdlc_assessor.__version__
    classifier: dict = field(default_factory=dict)
    # ↑ {repo_archetype, maturity_profile, network_exposure, classification_confidence,
    #    deployment_surface, release_surface}
    inventory_snapshot: dict = field(default_factory=dict)
    # ↑ {source_files, source_loc, test_files, workflow_files, runtime_dependencies, ...}


@dataclass(slots=True)
class MethodologyNote:
    """Renders as the methodology sidebar / box.

    Names the bar, the formula, the multiplier composition, and the
    verdict-rule table. Cites every claim so the reader can audit.
    """

    score_formula: str  # readable math, plain monospace
    threshold_explanation: str
    multiplier_explanation: str
    verdict_rule_table: list[dict] = field(default_factory=list)
    # ↑ [{score_band: "≥distinction", critical: 0, high: 0, verdict: "proceed"}, ...]
    calibration_band: str | None = None  # matched against docs/calibration_targets.md, or None


@dataclass(slots=True)
class SectionFact:
    """A small key/value pair rendered as a metric strip or definition list."""

    label: str
    value: str
    severity: str | None = None
    note: str | None = None


@dataclass(slots=True)
class Section:
    """One body section of the deliverable.

    Sections are intentionally polymorphic. ``kind`` tells the renderer
    how to lay it out; ``data`` carries the structured payload.

    Recognized kinds (renderers may handle more):

    - ``"prose"`` — ``data["paragraphs"]``: list[str]
    - ``"facts"`` — ``data["facts"]``: list[SectionFact-as-dict]
    - ``"chart"`` — ``data["svg"]``: str (full ``<svg…/>`` element)
    - ``"swot"`` — ``data["strengths" | "weaknesses" | "opportunities"
      | "threats"]``: list[str]
    - ``"day_n"`` — ``data["day_30" | "day_60" | "day_90"]``: list[str]
    - ``"options_ladder"`` — ``data["options"]``: list[{verdict,
      condition, score_target}]
    - ``"questions"`` — ``data["questions"]``: list[str]
    - ``"claims_evaluation"`` — ``data["claims"]``: list[{claim,
      evidence_status, evidence_text}]
    - ``"remediation_table"`` — ``data["tasks"]``: list[task dict]
      (already shaped by remediation/planner.py)
    """

    title: str
    kind: str
    summary: str = ""
    data: dict = field(default_factory=dict)
    facts: list[SectionFact] = field(default_factory=list)
    chart_svg: str = ""
    narrative_block: NarrativeBlock | None = None


@dataclass(slots=True)
class RecommendationOption:
    """One option in the deliverable's recommendation ladder."""

    verdict: RecommendationVerdict
    condition: str  # "if remediation phases 1 & 2 close in 30 days"
    expected_score_after: int | None = None
    rationale: str = ""


@dataclass(slots=True)
class Recommendation:
    """A consolidated 'what to do' block."""

    headline: str
    options: list[RecommendationOption] = field(default_factory=list)
    must_close_before_proceeding: list[str] = field(default_factory=list)


@dataclass(slots=True)
class EngineeringAppendix:
    """Pointer to the engineering-grade finding list.

    Renderers materialize this from the scored payload — keeping it as a
    small handle here means deliverables stay round-trippable as JSON
    without re-embedding every finding.
    """

    production_finding_count: int = 0
    fixture_finding_count: int = 0
    category_count: int = 0
    show_full_listing: bool = True


@dataclass(slots=True)
class Deliverable:
    """A persona-distinct document.

    The four use-cases each emit a different ``kind`` and a different
    ordered list of sections. Renderers (HTML, Markdown, JSON) consume
    the same shape.

    The 0.11.0 depth-pass fields (``score_decomposition``, ``gap``,
    ``cost_frame``, ``methodology``, ``glossary``, ``citations``,
    ``executive_summary``, ``economic_frame``) are populated by builders
    so the reader can audit every threshold, rule, and cost claim. They
    default to ``None`` / empty so 0.10.0-shape consumers keep working.
    """

    use_case: str
    kind: str  # "acquisition_memo" | "vc_thesis" | "engineering_health" | "remediation_plan"
    cover: CoverPage
    sections: list[Section] = field(default_factory=list)
    recommendation: Recommendation | None = None
    appendix: EngineeringAppendix = field(default_factory=EngineeringAppendix)
    persona_blocks: list[NarrativeBlock] = field(default_factory=list)

    # 0.11.0 depth pass.
    score_decomposition: ScoreDecomposition | None = None
    gap: GapAnalysis | None = None
    cost_frame: CostFrame | None = None
    methodology: MethodologyNote | None = None
    glossary: list[GlossaryEntry] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    executive_summary: list[str] = field(default_factory=list)  # 3–4 prose paragraphs
    economic_frame: dict | None = None  # persona-specific structure (holdback / tranche / sprint / manifest)
    provenance: ProvenanceHeader | None = None  # pinned identity / scan-context block
    persona_findings: list[dict] = field(default_factory=list)  # persona-prioritized finding list


def deliverable_to_dict(d: Deliverable) -> dict:
    """JSON-serializable view (sections drop SVG payloads' raw bytes intact)."""
    return asdict(d)


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

_BUILDERS: dict[str, Callable[[dict, dict], Deliverable]] = {}


def register_deliverable_builder(
    use_case: str, builder: Callable[[dict, dict], Deliverable]
) -> None:
    _BUILDERS[use_case] = builder


def registered_deliverables() -> list[str]:
    return sorted(_BUILDERS)


def build_deliverable(scored: dict, use_case_profile: dict) -> Deliverable:
    """Dispatch to the builder for the profile's ``use_case`` key.

    Falls back to :func:`_generic_deliverable` if no builder is
    registered. Importing this module's siblings (acquisition, vc,
    engineering, remediation) registers all four shipped builders.
    """
    # Force registration — siblings register on import.
    from sdlc_assessor.renderer.deliverables import (  # noqa: F401
        acquisition,
        engineering,
        remediation,
        vc,
    )

    use_case = use_case_profile.get("use_case") or use_case_profile.get("name") or ""
    if not use_case:
        # Some callers pass the raw profile dict (with no name field).
        # Fall back to the first recognized signal.
        use_case = use_case_profile.get("__use_case__", "")
    builder = _BUILDERS.get(use_case)
    if builder is None:
        return _generic_deliverable(scored, use_case_profile, use_case=use_case or "unknown")
    return builder(scored, use_case_profile)


# ---------------------------------------------------------------------------
# Shared helpers (used across builders)
# ---------------------------------------------------------------------------


def production_findings(scored: dict) -> list[dict]:
    from sdlc_assessor.normalizer.findings import is_fixture_finding

    return [f for f in (scored.get("findings") or []) if not is_fixture_finding(f)]


def fixture_findings(scored: dict) -> list[dict]:
    from sdlc_assessor.normalizer.findings import is_fixture_finding

    return [f for f in (scored.get("findings") or []) if is_fixture_finding(f)]


def critical_blockers(scored: dict) -> list[dict]:
    return [b for b in (scored.get("hard_blockers") or []) if b.get("severity") == "critical"]


def high_blockers(scored: dict) -> list[dict]:
    return [b for b in (scored.get("hard_blockers") or []) if b.get("severity") == "high"]


def category_scores_list(scored: dict) -> list[dict]:
    raw = (scored.get("scoring") or {}).get("category_scores") or []
    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]
    if isinstance(raw, dict):
        # Legacy shape — best-effort flatten without warning (we're a helper).
        out: list[dict] = []
        for cat, data in raw.items():
            out.append(
                {
                    "category": cat,
                    "applicable": data.get("applicability", "applicable") != "not_applicable",
                    "score": int(round(data.get("score", 0))),
                    "max_score": int(round(data.get("max", data.get("max_score", 0)))),
                    "summary": data.get("summary", ""),
                    "key_findings": data.get("key_findings", []),
                }
            )
        return out
    return []


_SEVERITY_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
_CONFIDENCE_RANK = {"high": 1.0, "medium": 0.9, "low": 0.7}


def finding_rank(f: dict) -> float:
    """Single-value impact score: severity × confidence × magnitude."""
    sev = _SEVERITY_RANK.get(f.get("severity", "low"), 0)
    conf = _CONFIDENCE_RANK.get(f.get("confidence", "medium"), 0.0)
    mag = float(f.get("score_impact", {}).get("magnitude", 0)) / 10.0
    return sev * conf * mag


def top_findings(scored: dict, *, n: int) -> list[dict]:
    return sorted(production_findings(scored), key=finding_rank, reverse=True)[:n]


def derive_recommendation(
    *,
    score: int,
    pass_threshold: int,
    distinction_threshold: int,
    critical_count: int,
    high_count: int,
) -> RecommendationVerdict:
    """Map score + blockers to a 4-state recommendation.

    The thresholds come from the use-case profile (acquisition has a
    higher bar than engineering triage). Critical blockers force the
    bottom two states regardless of score.
    """
    if critical_count > 0:
        return "decline" if score < pass_threshold else "proceed_with_conditions"
    if score >= distinction_threshold and high_count == 0:
        return "proceed"
    if score >= pass_threshold:
        return "proceed_with_conditions" if high_count > 0 else "proceed"
    if score >= max(40, pass_threshold - 15):
        return "defer"
    return "decline"


def classification_line(scored: dict) -> str:
    """Human-readable one-liner: archetype · maturity · network exposure."""
    cls = scored.get("classification") or {}
    archetype = (cls.get("repo_archetype") or "unknown").replace("_", " ")
    maturity = (cls.get("maturity_profile") or "unknown").replace("_", " ")
    network = "networked" if cls.get("network_exposure") else "non-networked"
    return f"{archetype} · {maturity} maturity · {network}"


def score_band(score: float) -> str:
    """Classify a 0..100 score into the four reporting bands."""
    if score >= 76:
        return "distinction"
    if score >= 56:
        return "pass"
    if score >= 36:
        return "conditional"
    return "fail"


# ---------------------------------------------------------------------------
# Generic fallback
# ---------------------------------------------------------------------------


def _generic_deliverable(
    scored: dict, profile: dict, *, use_case: str
) -> Deliverable:
    """Used when no persona-specific builder is registered.

    Produces a serviceable document driven by the persona narrative
    blocks alone — no charts, no SWOT, no Day-30/60/90.
    """
    from sdlc_assessor.renderer.charts import score_gauge
    from sdlc_assessor.renderer.persona import narrate_for_persona

    blocks = narrate_for_persona(scored, profile)
    scoring = scored.get("scoring") or {}
    score = int(round(float(scoring.get("overall_score", 0))))
    verdict = scoring.get("verdict", "fail")

    cover = CoverPage(
        title=f"Assessment — {use_case.replace('_', ' ').title() or 'Generic'}",
        subtitle="Generic profile (no persona-specific deliverable shape registered)",
        recommendation=derive_recommendation(
            score=score,
            pass_threshold=int(profile.get("pass_threshold", 70)),
            distinction_threshold=int(profile.get("distinction_threshold", 85)),
            critical_count=len(critical_blockers(scored)),
            high_count=len(high_blockers(scored)),
        ),
        recommendation_rationale=f"Verdict {verdict}; overall score {score}/100.",
        score=score,
        score_band=score_band(score),
        score_gauge_svg=score_gauge(score=score, verdict=verdict),
        classification_line=classification_line(scored),
    )

    sections: list[Section] = []
    for block in blocks:
        sections.append(
            Section(
                title=block.title,
                kind="prose",
                summary=block.summary,
                facts=[
                    SectionFact(label=fact.label, value=fact.value, severity=fact.severity)
                    for fact in block.facts
                ],
                narrative_block=block,
            )
        )

    return Deliverable(
        use_case=use_case,
        kind="generic",
        cover=cover,
        sections=sections,
        persona_blocks=blocks,
        appendix=_appendix_for(scored),
    )


def _appendix_for(scored: dict) -> EngineeringAppendix:
    return EngineeringAppendix(
        production_finding_count=len(production_findings(scored)),
        fixture_finding_count=len(fixture_findings(scored)),
        category_count=len(category_scores_list(scored)),
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
    "category_scores_list",
    "classification_line",
    "critical_blockers",
    "deliverable_to_dict",
    "derive_recommendation",
    "finding_rank",
    "fixture_findings",
    "high_blockers",
    "production_findings",
    "register_deliverable_builder",
    "registered_deliverables",
    "score_band",
    "top_findings",
    "_appendix_for",
]
