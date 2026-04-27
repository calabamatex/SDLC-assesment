"""Engineering-triage health report builder (SDLC-076).

Audience: an engineering lead (you, your tech lead, your platform team)
deciding what to fix this week and next quarter. Compared to the other
deliverables, the engineering report:

- leads with a code-health snapshot, not a recommendation pill;
- foregrounds the **effort × impact** matrix so triage is easy;
- enumerates failure modes with concrete code-level evidence;
- proposes a phased fix plan with explicit score lift per phase.
"""

from __future__ import annotations

from sdlc_assessor.renderer.charts import (
    category_radar,
    effort_impact_matrix,
    score_gauge,
    score_lift_trajectory,
)
from sdlc_assessor.renderer.charts.matrix import MatrixPoint
from sdlc_assessor.renderer.charts.trajectory import PhaseLift
from sdlc_assessor.renderer.deliverables.base import (
    CoverPage,
    Deliverable,
    Recommendation,
    RecommendationOption,
    Section,
    SectionFact,
    _appendix_for,
    category_scores_list,
    classification_line,
    critical_blockers,
    derive_recommendation,
    high_blockers,
    production_findings,
    register_deliverable_builder,
    score_band,
    top_findings,
)
from sdlc_assessor.renderer.deliverables._vocab import ENGINEERING_VOCAB
from sdlc_assessor.renderer.persona import narrate_for_persona

_VOCAB = ENGINEERING_VOCAB

_EFFORT_VALUE = {"XS": 0.1, "S": 0.3, "M": 0.55, "L": 0.8, "XL": 0.95}


def build(scored: dict, profile: dict) -> Deliverable:
    scoring = scored.get("scoring") or {}
    blocks = narrate_for_persona(scored, profile)

    score = int(round(float(scoring.get("overall_score", 0))))
    verdict = str(scoring.get("verdict", "fail"))
    crit = critical_blockers(scored)
    high = high_blockers(scored)

    pass_threshold = int(profile.get("pass_threshold", 70))
    distinction_threshold = int(profile.get("distinction_threshold", 85))
    recommendation_verdict = derive_recommendation(
        score=score,
        pass_threshold=pass_threshold,
        distinction_threshold=distinction_threshold,
        critical_count=len(crit),
        high_count=len(high),
    )

    cover = CoverPage(
        title="Engineering Health Report",
        subtitle=_subtitle(score, verdict, len(crit), len(high)),
        recommendation=recommendation_verdict,
        recommendation_rationale=_health_rationale(len(crit), len(high)),
        score=score,
        score_band=score_band(score),
        headline_facts=_cover_facts(scored),
        score_gauge_svg=score_gauge(score=score, verdict=verdict),
        classification_line=classification_line(scored),
    )

    sections: list[Section] = [
        _capability_radar_section(scored),
        _top_debts_section(scored),
        _failure_modes_section(scored, blocks),
        _effort_impact_section(scored),
        _phased_remediation_section(scored, current_score=score),
    ]

    for block in blocks:
        sections.append(
            Section(
                title=block.title,
                kind="prose",
                summary=block.summary,
                facts=[
                    SectionFact(label=f.label, value=f.value, severity=f.severity)
                    for f in block.facts
                ],
                narrative_block=block,
            )
        )

    recommendation = _build_recommendation(
        score=score,
        critical=crit,
        high=high,
    )

    deliverable = Deliverable(
        use_case="engineering_triage",
        kind="engineering_health",
        cover=cover,
        sections=sections,
        recommendation=recommendation,
        appendix=_appendix_for(scored),
        persona_blocks=blocks,
    )
    from sdlc_assessor.renderer.deliverables._integrate import apply_depth_pass

    return apply_depth_pass(deliverable, scored=scored, use_case_profile=profile)


# ---------------------------------------------------------------------------
# Cover-page helpers
# ---------------------------------------------------------------------------


def _subtitle(score: int, verdict: str, crit: int, high: int) -> str:
    band = score_band(score)
    severity_summary = (
        f"{crit} critical · {high} high blockers" if (crit or high) else "no hard blockers"
    )
    return f"Health band: {band} · score {score}/100 · verdict {verdict} · {severity_summary}."


def _health_rationale(crit: int, high: int) -> str:
    """Engineering cover rationale, in sprint-allocation language.

    Post-RSF: no made-up `pass_threshold`. The RSF assessment below
    surfaces the CTO/VP-Eng-row weighted total against the published §3
    matrix and the per-dimension means.
    """
    if crit:
        return (
            f"{crit} critical blocker(s) dominate health right now. Phase 1 "
            "(security) is the next sprint's must-ship — see the RSF "
            "assessment below for which sub-criteria drive that phase. "
            "Defer feature work until those land."
        )
    if high:
        return (
            f"No critical blockers, but {high} high-severity issue(s) remain. "
            "Plan them into next sprint or two; the RSF top-priorities table "
            "shows which ones map to the lowest dimension scores."
        )
    return (
        "No hard blockers and the RSF assessment below shows steady-state "
        "discipline. Treat this report as the maintenance baseline; re-run "
        "quarterly per the RSF cadence."
    )


def _cover_facts(scored: dict) -> list[tuple[str, str]]:
    inv = scored.get("inventory") or {}
    facts = [
        ("Source LOC / files", f"{inv.get('source_loc', 'n/a')} LOC · {inv.get('source_files', 'n/a')} files"),
        ("Test coverage signal", f"{inv.get('test_files', 'n/a')} test files · ratio {inv.get('test_to_source_ratio', 'n/a')}"),
        ("CI breadth", f"{inv.get('workflow_files', 'n/a')} workflows · {inv.get('workflow_jobs', 'n/a')} jobs"),
        ("Production findings", str(len([f for f in scored.get("findings") or [] if not (f.get("tags") or []) or "source:test_fixture" not in (f.get("tags") or [])]))),
        ("Critical / high blockers",
         f"{sum(1 for b in scored.get('hard_blockers') or [] if b.get('severity') == 'critical')} / "
         f"{sum(1 for b in scored.get('hard_blockers') or [] if b.get('severity') == 'high')}"),
    ]
    return facts


# ---------------------------------------------------------------------------
# §1 Capability radar
# ---------------------------------------------------------------------------


def _capability_radar_section(scored: dict) -> Section:
    cats = category_scores_list(scored)
    axes: list[tuple[str, int, int]] = []
    for c in cats:
        if not c.get("applicable", True):
            continue
        max_score = int(c.get("max_score", 0) or 0)
        if max_score <= 0:
            continue
        axes.append(
            (
                _VOCAB.category_labels.get(c.get("category", ""))
                or str(c.get("category", "")).replace("_", " ").title(),
                int(c.get("score", 0) or 0),
                max_score,
            )
        )
    svg = category_radar(axes=axes, title=_VOCAB.radar_title) if axes else ""
    return Section(
        title="1. Health by category",
        kind="chart",
        summary=_VOCAB.radar_caption,
        chart_svg=svg,
        data={"axes": axes},
    )


# ---------------------------------------------------------------------------
# §2 Top debts
# ---------------------------------------------------------------------------


def _top_debts_section(scored: dict) -> Section:
    findings = top_findings(scored, n=8)
    rows: list[dict] = []
    for f in findings:
        rows.append(
            {
                "title": (f.get("subcategory") or f.get("id") or "finding").replace("_", " ").title(),
                "severity": f.get("severity", "low"),
                "confidence": f.get("confidence", "medium"),
                "statement": (f.get("statement") or "").rstrip("."),
                "evidence": [
                    f"{e.get('path', '?')}:{e.get('line_start', '?')}"
                    for e in (f.get("evidence") or [])[:2]
                ],
                "id": f.get("id"),
            }
        )
    return Section(
        title="2. Top debts",
        kind="remediation_table",
        summary=(
            "Highest-impact production findings sorted by severity × confidence × "
            "deduction magnitude. Each row points at a specific path and line so "
            "the fix is one click away."
        ),
        data={"tasks": rows},
    )


# ---------------------------------------------------------------------------
# §3 Failure modes
# ---------------------------------------------------------------------------


def _failure_modes_section(scored: dict, blocks: list) -> Section:
    failure_block = next(
        (b for b in blocks if "failure" in (b.key or "").lower()),
        None,
    )
    paragraphs: list[str] = []
    if failure_block:
        paragraphs.append(failure_block.summary)
    else:
        paragraphs.append(
            "No persona-specific failure-mode narrative ran for this profile; "
            "see the top-debts table in §2 for the dominant risk patterns."
        )

    facts: list[SectionFact] = []
    if failure_block:
        for fact in failure_block.facts:
            facts.append(SectionFact(label=fact.label, value=fact.value, severity=fact.severity))

    return Section(
        title="3. Failure modes",
        kind="facts",
        summary="Concrete failure scenarios derived from the evidence — what breaks first, and how loud.",
        facts=facts,
        data={"paragraphs": paragraphs},
        narrative_block=failure_block,
    )


# ---------------------------------------------------------------------------
# §4 Effort × impact
# ---------------------------------------------------------------------------


def _effort_impact_section(scored: dict) -> Section:
    plan = scored.get("remediation_plan") or scored.get("remediation") or {}
    tasks = plan.get("tasks") or []
    points: list[MatrixPoint] = []
    if tasks:
        for t in tasks[:24]:
            effort = _EFFORT_VALUE.get(str(t.get("effort", "M")).upper(), 0.5)
            delta = float(t.get("expected_score_delta") or 1)
            # Normalize delta: most deltas live in 1..15; clamp + scale.
            impact = max(0.05, min(1.0, delta / 15.0))
            sev = (t.get("severity") or t.get("priority") or "medium").lower()
            label = (t.get("title") or t.get("subcategory") or "task").replace("_", " ")
            note = " | ".join((t.get("verification_commands") or [])[:1]) or None
            points.append(
                MatrixPoint(label=label, x=effort, y=impact, severity=sev, note=note)
            )
    else:
        # Fall back to top findings: severity proxies impact, confidence proxies effort.
        for f in top_findings(scored, n=12):
            sev = (f.get("severity") or "low").lower()
            conf = (f.get("confidence") or "medium").lower()
            impact = {"critical": 0.95, "high": 0.8, "medium": 0.55, "low": 0.3, "info": 0.15}.get(sev, 0.4)
            effort = {"high": 0.3, "medium": 0.55, "low": 0.8}.get(conf, 0.5)
            points.append(
                MatrixPoint(
                    label=(f.get("subcategory") or f.get("id") or "finding").replace("_", " "),
                    x=effort,
                    y=impact,
                    severity=sev,
                )
            )
    svg = effort_impact_matrix(
        tasks=points,
        title=_VOCAB.effort_title,
        x_label=_VOCAB.effort_x,
        y_label=_VOCAB.effort_y,
        quadrant_labels=_VOCAB.effort_quadrants,
    )
    return Section(
        title="4. Effort × impact triage",
        kind="chart",
        summary=_VOCAB.effort_caption,
        chart_svg=svg,
        data={"point_count": len(points)},
    )


# ---------------------------------------------------------------------------
# §5 Phased remediation trajectory
# ---------------------------------------------------------------------------


def _phased_remediation_section(scored: dict, *, current_score: int) -> Section:
    plan = scored.get("remediation_plan") or scored.get("remediation") or {}
    tasks = plan.get("tasks") or []
    deltas_by_phase: dict[str, float] = {}
    for t in tasks:
        phase = t.get("phase", "phase_other")
        deltas_by_phase[phase] = deltas_by_phase.get(phase, 0.0) + float(t.get("expected_score_delta") or 0)

    phase_order = [
        ("phase_1_security", "Phase 1 · Security"),
        ("phase_2_contracts", "Phase 2 · Contracts"),
        ("phase_3_tests", "Phase 3 · Tests"),
        ("phase_4_ci", "Phase 4 · CI / release"),
        ("phase_5_docs", "Phase 5 · Documentation"),
    ]
    phases: list[PhaseLift] = []
    for key, label in phase_order:
        if key in deltas_by_phase and deltas_by_phase[key] > 0:
            phases.append(PhaseLift(label=label, delta=deltas_by_phase[key]))
    # Dump anything that didn't fit one of the canonical buckets.
    extras = [
        (k, v) for k, v in deltas_by_phase.items() if k not in {p[0] for p in phase_order} and v > 0
    ]
    for key, delta in sorted(extras, key=lambda kv: -kv[1])[:2]:
        phases.append(PhaseLift(label=str(key).replace("_", " ").title(), delta=delta))

    svg = score_lift_trajectory(
        current_score=current_score,
        phases=phases,
        title=_VOCAB.trajectory_title,
    )
    return Section(
        title="5. Phased remediation trajectory",
        kind="chart",
        summary=_VOCAB.trajectory_caption,
        chart_svg=svg,
        data={"phases": [{"label": p.label, "delta": p.delta} for p in phases]},
    )


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------


def _build_recommendation(
    *, score: int, critical: list[dict], high: list[dict]
) -> Recommendation:
    if critical:
        headline = "Treat as a P0: hold non-critical merges until Phase 1 ships."
    elif score < 56:
        headline = "Concentrated remediation sprint required."
    elif high:
        headline = "Add Phase 2 + Phase 3 to next quarter's plan."
    else:
        headline = "Codebase is healthy. Maintain via existing CI + remediation cadence."

    options: list[RecommendationOption] = []
    if critical:
        options.append(
            RecommendationOption(
                verdict="proceed_with_conditions",
                condition="Phase 1 (security) closed within one sprint.",
                expected_score_after=min(100, score + 12),
                rationale="Removes critical blockers; unblocks downstream phases.",
            )
        )
    if high:
        options.append(
            RecommendationOption(
                verdict="proceed_with_conditions",
                condition="Phases 2–3 (contracts, tests) closed within two sprints.",
                expected_score_after=min(100, score + 8),
                rationale="Brings test discipline + type tightening online.",
            )
        )
    if score >= 70:
        options.append(
            RecommendationOption(
                verdict="proceed",
                condition="Maintain existing release / CI cadence.",
                expected_score_after=score,
                rationale="No urgent intervention; periodic re-run is sufficient.",
            )
        )
    if not options:
        options.append(
            RecommendationOption(
                verdict="defer",
                condition="No remediation plan available.",
                expected_score_after=score,
                rationale="Re-run with `--narrator both` after generating a remediation plan.",
            )
        )
    return Recommendation(
        headline=headline,
        options=options,
        must_close_before_proceeding=[
            f"Close: {b.get('title', 'Critical blocker')} — {b.get('reason', '')}"
            for b in critical
        ],
    )


register_deliverable_builder("engineering_triage", build)


__all__ = ["build"]
