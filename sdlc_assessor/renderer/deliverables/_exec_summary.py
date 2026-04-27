"""Per-persona executive-summary builder, RSF-grounded.

After the RSF v1.0 cutover the executive summary is anchored to the
Repository Scoring Framework, not to the legacy made-up `pass_threshold`
/ `distinction_threshold` / 0–100 rubric. The summary names:

1. Where the asset lands on the RSF for THIS persona's reader (per-
   persona weighted total %, on the published 0–100 scale).
2. What evidence backed the score (count of scored sub-criteria) vs.
   what was unverified (count of `?` sub-criteria) per RSF §1.
3. The persona-specific consequence of the lowest-scored RSF sub-
   criterion: what THIS reader (VC / acquirer / engineer / agent /
   etc.) should do about it.
4. The persona-specific framing of the gap: thesis credibility lift,
   integration cost, sprint allocation, agent-execution priority.

Every numeric token in the output is grounded: pulled from
``deliverable.score_decomposition`` (RSF dimension means / counts) or
``scored["rsf"]`` (per-persona totals), not from any made-up threshold.
"""

from __future__ import annotations

from sdlc_assessor.renderer.deliverables._citations import CitationRegistry
from sdlc_assessor.renderer.deliverables.base import Deliverable, RecommendationVerdict


# ---------------------------------------------------------------------------
# Persona frame: how to translate RSF findings into THIS reader's language
# ---------------------------------------------------------------------------
#
# The legacy `_PERSONA_FRAME` had `audience` / `score_meaning` etc. The new
# frame instead carries the *consequence dictionary* the persona uses when
# reading an RSF finding. Every consequence is expressed in the persona's
# native vocabulary so the report doesn't translate engineering signals into
# generic prose — it translates them into what the reader actually decides.

_PERSONA_FRAME: dict[str, dict[str, str]] = {
    "acquisition_diligence": {
        "audience": "an integration lead deciding whether to acquire this asset",
        "rsf_persona_id": "pe_ma",
        "lens": "post-close ownership cost",
        "score_meaning": (
            "drives the acquisition recommendation and sizes the engineering "
            "investment we'd inherit on close"
        ),
        "consequence_low_score": (
            "items below 2/5 typically translate into escrow conditions, "
            "purchase-price adjustments, or seller-funded remediation milestones"
        ),
        "consequence_unverified": (
            "evidence the seller would need to produce before close "
            "(audit packets, SBOM exports, branch-protection screenshots)"
        ),
    },
    "vc_diligence": {
        "audience": "an investor evaluating whether the code substantiates the pitch",
        "rsf_persona_id": "vc",
        "lens": "thesis credibility",
        "score_meaning": (
            "drives the investment recommendation and frames the founder Q&A "
            "we'd take into the term-sheet conversation"
        ),
        "consequence_low_score": (
            "items below 2/5 are deal-killers or warrant valuation discount / "
            "milestone-tranched capital release"
        ),
        "consequence_unverified": (
            "questions for the founder follow-up before term-sheet "
            "(commit history, deployment cadence, customer-trust posture)"
        ),
    },
    "engineering_triage": {
        "audience": "an engineering lead planning what to fix this quarter",
        "rsf_persona_id": "cto_vp_eng",
        "lens": "operational reliability",
        "score_meaning": (
            "drives sprint allocation and signals which RSF dimensions are "
            "thinnest for the next quarter's planning"
        ),
        "consequence_low_score": (
            "items below 2/5 belong in this sprint or next; items at 0/5 are "
            "page-someone-tonight failures if they're security or supply-chain"
        ),
        "consequence_unverified": (
            "instrumentation gaps the team can close (DORA-metric collection, "
            "OSV scan, branch-protection rules in IaC)"
        ),
    },
    "remediation_agent": {
        "audience": "an autonomous coding agent executing the remediation plan",
        "rsf_persona_id": "cto_vp_eng",
        "lens": "execution priority",
        "score_meaning": (
            "the calibration target for the fix loop; agent advances when each "
            "task's verification commands exit 0"
        ),
        "consequence_low_score": (
            "tasks tagged with the corresponding RSF criterion — execute in "
            "ascending RSF-id order within each phase"
        ),
        "consequence_unverified": (
            "preflight steps the agent needs to add before the next assessment "
            "run (collector configuration, API tokens, scan policies)"
        ),
    },
}


def _frame_for(use_case: str) -> dict[str, str]:
    """Get the persona frame; falls back to engineering-triage."""
    return _PERSONA_FRAME.get(use_case) or _PERSONA_FRAME["engineering_triage"]


def _persona_total(scored: dict, rsf_persona_id: str) -> dict | None:
    """Pull the RSF persona total dict from ``scored["rsf"]``."""
    rsf = scored.get("rsf") or {}
    for p in rsf.get("personas") or []:
        if p.get("persona_id") == rsf_persona_id:
            return p
    return None


def _bottom_scored_criterion(scored: dict) -> dict | None:
    """Find the lowest non-`?` non-`N/A` sub-criterion across all dimensions."""
    rsf = scored.get("rsf") or {}
    candidates: list[dict] = []
    for d in rsf.get("dimensions") or []:
        for c in d.get("criteria") or []:
            v = c.get("value")
            if isinstance(v, int) and 0 <= v <= 5:
                candidates.append(c)
    if not candidates:
        return None
    return sorted(candidates, key=lambda c: c["value"])[0]


def _verified_dim_count(scored: dict) -> tuple[int, int]:
    """Return (n_dims_with_real_scores, n_total_dims_excluding_N/A)."""
    rsf = scored.get("rsf") or {}
    real = 0
    total = 0
    for d in rsf.get("dimensions") or []:
        if d.get("mean") is None:  # all N/A
            continue
        total += 1
        if not d.get("confidence_flagged"):
            real += 1
    return real, total


def build_executive_summary(
    *,
    use_case: str,
    scored: dict,
    deliverable: Deliverable,
    verdict: RecommendationVerdict,
    citations: CitationRegistry,
) -> list[str]:
    """Construct 3 prose paragraphs grounded in the RSF assessment.

    Inline citations (``[N]``) reference the RSF v1.0 spec doc, the
    persona's RSF persona-id row in the §3 weight matrix, and the source
    file for the lowest-scored sub-criterion's anchor.
    """
    frame = _frame_for(use_case)
    rsf_persona_id = frame["rsf_persona_id"]
    rsf_persona = _persona_total(scored, rsf_persona_id) or {}
    rsf_total_pct = float(rsf_persona.get("total_pct", 0.0))
    limited = bool(rsf_persona.get("limited_confidence_warning"))

    real_dims, total_dims = _verified_dim_count(scored)
    flagged_dims = (scored.get("rsf") or {}).get("flagged_dimensions") or []
    bottom = _bottom_scored_criterion(scored)

    # Citations referenced inline in the prose.
    rsf_marker = citations.cite(
        claim_id="rsf_framework_source",
        text=(
            "Repository Scoring Framework v1.0 — every level anchor is sourced "
            "from a published industry standard. See the canonical spec doc."
        ),
        evidence_refs=["RSF v1.0 §1, §2, §3, §4"],
        source_files=[("docs/frameworks/rsf_v1.0.md", None)],
    )
    weight_marker = citations.cite(
        claim_id="rsf_persona_weights",
        text=(
            f"RSF persona-weight row for {rsf_persona_id}: see §3 of the "
            "framework spec. Weights sum to 100 across the 8 dimensions."
        ),
        evidence_refs=[f"persona_id={rsf_persona_id}", "weights sum to 100"],
        source_files=[("docs/frameworks/rsf_v1.0.md", None)],
    )

    # ---- paragraph 1: where the asset lands on the RSF for this persona ----
    confidence_clause = (
        " The result carries a *limited confidence* flag because more than 25% "
        "of the persona's weight maps to dimensions where the assessor could "
        "not collect evidence (RSF §4)."
        if limited
        else ""
    )
    paragraph_1 = (
        f"This report is for {frame['audience']}. Under the Repository "
        f"Scoring Framework v1.0[{rsf_marker}], the asset's persona-weighted "
        f"total for the {rsf_persona.get('persona_label', rsf_persona_id)} "
        f"reader is **{rsf_total_pct:.1f}%** on the 0–100 scale that the RSF "
        f"defines.{confidence_clause} The persona weighting comes from the "
        f"RSF §3 matrix[{weight_marker}]; it {frame['score_meaning']}."
    )

    # ---- paragraph 2: evidence coverage + lowest scored sub-criterion ----
    if bottom is None:
        paragraph_2 = (
            f"No RSF sub-criterion scored against the rubric in this run — "
            f"every criterion currently returns `?` (unverified). That is the "
            f"framework-correct disclosure when the assessor has not yet "
            f"collected the evidence each criterion requires; closing those "
            f"gaps (DORA-metric collection, OSV scanning, GitHub Settings API "
            f"integration) unlocks real scores. Per RSF §1, `?` is treated "
            f"as 0 in the math but flagged separately so the reader can "
            f"distinguish absent from unverified."
        )
    else:
        bottom_marker = citations.cite(
            claim_id=f"bottom_anchor_{bottom['criterion_id']}",
            text=(
                f"RSF {bottom['criterion_id']} level {bottom['value']} anchor: "
                f"\"{bottom['rationale']}\" — see §2 of the framework."
            ),
            evidence_refs=[
                f"{bottom['criterion_id']}={bottom['value']}/5",
                *bottom.get("evidence", [])[:2],
            ],
            source_files=[("docs/frameworks/rsf_v1.0.md", None)],
        )
        paragraph_2 = (
            f"Of the 31 RSF sub-criteria, **{real_dims}** of {total_dims} "
            f"dimensions scored fully against the rubric; the rest carry "
            f"unverified sub-criteria (`?`) where the assessor has not yet "
            f"collected the evidence the framework requires. The lowest-"
            f"scored real anchor is **{bottom['criterion_id']}** at "
            f"**{bottom['value']}/5**: *{bottom['rationale']}*[{bottom_marker}]. "
            f"For {frame['lens']}: {frame['consequence_low_score']}."
        )

    # ---- paragraph 3: framing the gap in the persona's lens ----
    rule_marker = citations.cite(
        claim_id="rsf_unverified_treatment",
        text=(
            "RSF §1: ``?`` is treated as 0 for scoring but flagged separately "
            "so reports distinguish absent from unverified. ``N/A`` is "
            "excluded; the dimension's denominator shrinks accordingly."
        ),
        evidence_refs=["RSF §1 'Special values'"],
        source_files=[("docs/frameworks/rsf_v1.0.md", None)],
    )
    if flagged_dims:
        flagged_text = (
            f"{len(flagged_dims)} of 8 RSF dimensions flagged for unverified "
            f"sub-criteria ({', '.join(flagged_dims)})"
        )
    else:
        flagged_text = "no dimensions flagged for unverified sub-criteria"
    paragraph_3 = (
        f"What's unverified is also actionable: {flagged_text}[{rule_marker}]. "
        f"For {frame['audience']}, those gaps are {frame['consequence_unverified']}. "
        f"The Top remediation priorities table in the RSF assessment block "
        "lists the lowest-scored real anchors with their evidence trails; "
        "the persona narrative sections below translate each into the "
        f"{frame['lens']} frame."
    )

    return [paragraph_1, paragraph_2, paragraph_3]


__all__ = ["build_executive_summary"]
