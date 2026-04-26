"""Per-persona executive-summary builder (0.11.0 depth pass).

Generates 3–4 prose paragraphs naming:

1. The bar (the persona's pass_threshold) — with the source path cited.
2. The asset's score and the gap.
3. The decision rule that produced the recommendation — with the
   verdict-rule source cited.
4. The phases that close the gap, with their projected score lifts —
   labelled as projections, not historical outcomes.

Every numeric token in the output is grounded: pulled from
``ScoreDecomposition`` (real arithmetic), ``GapAnalysis`` (real
distances), ``scored.json`` (real findings/blockers), or the
canonical scorer constants.

The 0.11.0 cut explicitly excludes:

- holdback / tranche / valuation-discount language (no real labor or
  outcome data behind it),
- engineer-day cost claims (no calibrated effort table),
- comparable-benchmark language ("median monorepo is X" — no corpus).

Persona-specific framing comes from the persona's :class:`PersonaVocab`,
not new editorial copy.
"""

from __future__ import annotations

from sdlc_assessor.renderer.deliverables._citations import CitationRegistry
from sdlc_assessor.renderer.deliverables.base import (
    GapAnalysis,
    RecommendationVerdict,
    ScoreDecomposition,
)


_VERDICT_HEADLINE = {
    "acquisition_diligence": {
        "proceed": "Acquisition recommendation: **proceed to close**.",
        "proceed_with_conditions": "Acquisition recommendation: **proceed only if conditions close before close**.",
        "defer": "Acquisition recommendation: **defer until seller closes the gap**.",
        "decline": "Acquisition recommendation: **decline at proposed terms**.",
    },
    "vc_diligence": {
        "proceed": "Investment recommendation: **lead at proposed terms**.",
        "proceed_with_conditions": "Investment recommendation: **conditional invest pending founder Q&A**.",
        "defer": "Investment recommendation: **defer; re-diligence after seller-funded fixes**.",
        "decline": "Investment recommendation: **decline at proposed terms**.",
    },
    "engineering_triage": {
        "proceed": "Engineering recommendation: **maintain existing release cadence**.",
        "proceed_with_conditions": "Engineering recommendation: **schedule a concentrated remediation sprint**.",
        "defer": "Engineering recommendation: **plan a multi-sprint cleanup before next major release**.",
        "decline": "Engineering recommendation: **freeze feature work until phase 1 ships**.",
    },
    "remediation_agent": {
        "proceed": "Agent directive: **idle; codebase at calibration target**.",
        "proceed_with_conditions": "Agent directive: **execute the plan from phase 1; commit per task; verify per phase**.",
        "defer": "Agent directive: **execute plan with extra verification gates between phases**.",
        "decline": "Agent directive: **halt; humans must review the blocker list before any patch advances**.",
    },
}


def _verdict_headline_for(use_case: str, verdict: str) -> str:
    """Persona-specific verdict headline; falls back to a generic phrasing."""
    by_persona = _VERDICT_HEADLINE.get(use_case, {})
    return by_persona.get(verdict) or f"Recommendation: **{verdict.replace('_', ' ')}**."


_PERSONA_FRAME = {
    "acquisition_diligence": {
        "audience": "an integration lead deciding whether to acquire this asset",
        "score_meaning": (
            "drives the acquisition recommendation and sizes the post-close "
            "engineering cost we'd inherit"
        ),
        "gap_meaning": (
            "the work the seller would have to ship before close, or that "
            "we'd absorb post-close"
        ),
        "phase_meaning": "phases of remediation the seller could ship before signing",
        "blocker_consequence": "gate the acquisition unless seller-funded or carved out of the deal",
        "no_gap_consequence": (
            "the asset clears the acquisition bar; sizing the deal becomes a "
            "valuation conversation rather than a remediation negotiation"
        ),
    },
    "vc_diligence": {
        "audience": "an investor evaluating whether the code substantiates the pitch",
        "score_meaning": (
            "drives the investment recommendation and frames the diligence "
            "questions we'd take into the founder follow-up"
        ),
        "gap_meaning": "thesis-credibility gap we'd need addressed before term-sheet",
        "phase_meaning": "remediation phases the founder would commit to as milestones",
        "blocker_consequence": "puncture the investment thesis and force tranching or a re-priced round",
        "no_gap_consequence": (
            "the code substantiates the pitch as presented; remaining diligence "
            "is commercial and team-shaped, not technical"
        ),
    },
    "engineering_triage": {
        "audience": "an engineering lead planning what to fix this quarter",
        "score_meaning": (
            "drives sprint allocation and signals which categories are thinnest"
        ),
        "gap_meaning": "the score lift available from working the remediation plan",
        "phase_meaning": "remediation phases the team would work in order",
        "blocker_consequence": "page the on-call rotation and dominate the next sprint regardless of score",
        "no_gap_consequence": (
            "no concentrated remediation sprint required; treat this report as "
            "the maintenance baseline and watch the radar between releases"
        ),
    },
    "remediation_agent": {
        "audience": "an autonomous coding agent executing the remediation plan",
        "score_meaning": "the calibration target for the fix loop",
        "gap_meaning": "cumulative score lift available from completing the plan",
        "phase_meaning": "phases of the plan, executed sequentially with verification gates",
        "blocker_consequence": "block agent advancement; the task pointer must not move past an unresolved blocker",
        "no_gap_consequence": (
            "the asset is at the calibration target; agent should idle or "
            "schedule the next assessment rather than open new tasks"
        ),
    },
}


def build_executive_summary(
    *,
    use_case: str,
    scored: dict,
    decomposition: ScoreDecomposition,
    gap: GapAnalysis,
    verdict: RecommendationVerdict,
    citations: CitationRegistry,
) -> list[str]:
    """Construct 3–4 prose paragraphs for the executive summary.

    Inline citations (``[N]``) are emitted using the shared
    ``CitationRegistry`` so the rendered footnotes line up.
    """
    frame = _PERSONA_FRAME.get(use_case, _PERSONA_FRAME["engineering_triage"])

    overall = decomposition.overall
    pass_threshold = decomposition.pass_threshold
    distinction_threshold = decomposition.distinction_threshold

    # Citations the exec summary will reference inline.
    threshold_marker = citations.cite(
        claim_id="pass_threshold_source",
        text=(
            f"The {use_case} pass threshold is {pass_threshold}. "
            f"This value is defined in {decomposition.threshold_source}."
        ),
        evidence_refs=[f"pass_threshold={pass_threshold}", f"distinction_threshold={distinction_threshold}"],
        source_files=[("sdlc_assessor/profiles/data/use_case_profiles.json", None)],
    )

    overall_marker = citations.cite(
        claim_id="overall_score_source",
        text=f"The overall score is {overall}. Computed by sdlc_assessor/scorer/engine.py.",
        evidence_refs=[f"scoring.overall_score={overall}"],
        source_files=[("sdlc_assessor/scorer/engine.py", 271)],
    )

    rule_marker = citations.cite(
        claim_id="verdict_rule_source",
        text=(
            "Verdict rule. The four-way mapping from (score, blockers) to "
            "verdict lives in sdlc_assessor/scorer/engine.py:244-251."
        ),
        evidence_refs=["score >= distinction AND no blockers => pass_with_distinction",
                       "score >= pass AND no critical => pass",
                       "(score >= pass AND has critical) OR (score < pass AND any blocker) => conditional_pass",
                       "otherwise => fail"],
        source_files=[("sdlc_assessor/scorer/engine.py", 244)],
    )

    crit_count = sum(
        1 for b in scored.get("hard_blockers") or [] if b.get("severity") == "critical"
    )
    high_count = sum(
        1 for b in scored.get("hard_blockers") or [] if b.get("severity") == "high"
    )

    # ---- paragraph 1: bar + score + gap ------------------------------------
    band_label = (
        f"clears the distinction band ({distinction_threshold}+)"
        if overall >= distinction_threshold
        else f"clears the pass bar ({pass_threshold}+)"
        if overall >= pass_threshold
        else f"falls {gap.gap_to_pass} points short of the {use_case} pass bar of {pass_threshold}"
    )

    paragraph_1 = (
        f"This report is for {frame['audience']}. The asset scores "
        f"**{overall}/100**[{overall_marker}] against an {use_case} pass threshold of "
        f"**{pass_threshold}**[{threshold_marker}] (distinction at {distinction_threshold}). "
        f"The score {band_label}; it {frame['score_meaning']}."
    )

    # ---- paragraph 2: blockers + decision rule ----------------------------
    if crit_count == 0 and high_count == 0:
        blocker_clause = "No hard blockers fired."
    else:
        parts: list[str] = []
        if crit_count:
            parts.append(f"**{crit_count} critical**")
        if high_count:
            parts.append(f"**{high_count} high**")
        blocker_clause = (
            f"{' and '.join(parts)} hard-blocker(s) {frame['blocker_consequence']}."
        )

    rule_text = _verdict_rule_clause(
        verdict=verdict,
        overall=overall,
        pass_threshold=pass_threshold,
        distinction_threshold=distinction_threshold,
        crit_count=crit_count,
        high_count=high_count,
    )

    paragraph_2 = (
        f"{_verdict_headline_for(use_case, verdict)} {blocker_clause} "
        f"Rule: {rule_text}[{rule_marker}]."
    )

    # ---- paragraph 3: gap closure ----------------------------------------
    if gap.gap_to_pass <= 0:
        paragraph_3 = (
            f"No gap to close: {frame['no_gap_consequence']}. "
            f"Distinction sits {gap.gap_to_distinction} points above the current score "
            f"({distinction_threshold} − {overall}); the score-decomposition section breaks "
            "out the per-category contributions."
        )
    elif gap.closing_phases:
        # The first closing phase is the one with the largest projected lift
        # that — alone or in combination — clears the bar.
        closing_marker = citations.cite(
            claim_id="phase_projection_source",
            text=(
                "Phase score lifts are projections from sdlc_assessor/remediation/planner.py, "
                "not historical outcomes. Real-world deltas after remediation may differ; "
                "outcome-calibrated projections arrive in 0.14.0."
            ),
            evidence_refs=["expected_score_delta defined in remediation/planner.py"],
            source_files=[("sdlc_assessor/remediation/planner.py", None)],
        )
        head = gap.closing_phases[0]
        proj_after = head.get("after", overall + head.get("projected_lift", 0))
        head_label = head.get("phase", "phase_other").replace("_", " ").title()
        paragraph_3 = (
            f"Closing the gap. {head_label} carries a projected lift of "
            f"+{head.get('projected_lift', 0):.1f} points across "
            f"{head.get('task_count', 0)} task(s); after that phase the projected score is "
            f"**{proj_after:.1f}**, which "
            f"{'clears' if proj_after >= pass_threshold else 'still falls short of'} "
            f"the {pass_threshold}-point bar. These are scoring-engine projections[{closing_marker}], "
            f"not measurements against historical outcomes."
        )
    else:
        paragraph_3 = (
            f"Closing the gap requires {gap.gap_to_pass} points of score lift. "
            "No remediation plan was attached to this run, so per-phase projections "
            "are not available; re-run with the remediation plan enabled to see "
            f"which phases recover ground."
        )

    return [paragraph_1, paragraph_2, paragraph_3]


def _verdict_rule_clause(
    *,
    verdict: str,
    overall: int,
    pass_threshold: int,
    distinction_threshold: int,
    crit_count: int,
    high_count: int,
) -> str:
    """Spell out which branch of the verdict ladder fired for THIS asset.

    No hand-wave — names the exact predicate from scorer/engine.py.
    """
    if verdict == "pass_with_distinction":
        return (
            f"score {overall} ≥ distinction_threshold {distinction_threshold} "
            f"AND zero blockers"
        )
    if verdict == "pass":
        return (
            f"score {overall} ≥ pass_threshold {pass_threshold} "
            f"AND zero critical blockers"
        )
    if verdict == "conditional_pass":
        if overall >= pass_threshold:
            return (
                f"score {overall} ≥ pass_threshold {pass_threshold} "
                f"AND {crit_count} critical blocker(s) fired"
            )
        return (
            f"score {overall} < pass_threshold {pass_threshold} "
            f"AND at least one blocker fired ({crit_count} critical, {high_count} high)"
        )
    # decline / fail / defer all fall through here
    return (
        f"score {overall} < pass_threshold {pass_threshold} "
        f"OR critical blocker(s) without rescue"
    )


__all__ = ["build_executive_summary"]
