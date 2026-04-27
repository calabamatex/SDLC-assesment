"""Acquisition-diligence memo builder (SDLC-074).

Audience: an integration lead or M&A diligence reviewer deciding whether
to proceed with the deal and, if yes, what conditions to attach. The
document answers four questions in order:

1. **Should we proceed?** — recommendation pill + headline metric on the
   cover page.
2. **What are we buying?** — classification, archetype, network surface,
   inventory deltas vs an ordinary repo of this kind.
3. **What will integration cost us?** — risk matrix (likelihood ×
   impact), maintenance burden, dependency concentration, knowledge
   transfer risk.
4. **What does our first 90 days look like?** — Day-30 / Day-60 / Day-90
   plan derived from the remediation plan.

The deliverable's body is *not* a list of every finding. The full
finding listing is the engineering appendix at the back of the document.
"""

from __future__ import annotations

from sdlc_assessor.renderer.charts import (
    category_radar,
    risk_matrix,
    score_gauge,
)
from sdlc_assessor.renderer.charts.matrix import MatrixPoint
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
    finding_rank,
    high_blockers,
    production_findings,
    register_deliverable_builder,
    score_band,
    top_findings,
)
from sdlc_assessor.renderer.deliverables._vocab import ACQUISITION_VOCAB
from sdlc_assessor.renderer.persona import narrate_for_persona

_VOCAB = ACQUISITION_VOCAB


def build(scored: dict, profile: dict) -> Deliverable:
    scoring = scored.get("scoring") or {}
    inventory = scored.get("inventory") or {}
    blocks = narrate_for_persona(scored, profile)

    score = int(round(float(scoring.get("overall_score", 0))))
    verdict = str(scoring.get("verdict", "fail"))
    crit = critical_blockers(scored)
    high = high_blockers(scored)

    pass_threshold = int(profile.get("pass_threshold", 74))
    distinction_threshold = int(profile.get("distinction_threshold", 88))
    recommendation_verdict = derive_recommendation(
        score=score,
        pass_threshold=pass_threshold,
        distinction_threshold=distinction_threshold,
        critical_count=len(crit),
        high_count=len(high),
    )

    # ---------------------------------------------------------------- cover
    cover = CoverPage(
        title="Acquisition Diligence Memo",
        subtitle=_subtitle_for_recommendation(recommendation_verdict, score),
        recommendation=recommendation_verdict,
        recommendation_rationale=_rationale_sentence(
            recommendation_verdict,
            critical=len(crit),
            high=len(high),
        ),
        score=score,
        score_band=score_band(score),
        headline_facts=_cover_facts(scored),
        score_gauge_svg=score_gauge(score=score, verdict=verdict),
        classification_line=classification_line(scored),
    )

    sections: list[Section] = []

    # ---------------------------------------------------------------- §1 Position
    sections.append(_position_section(scored, blocks))

    # ---------------------------------------------------------------- §2 What we're buying (radar)
    sections.append(_what_we_are_buying_section(scored))

    # ---------------------------------------------------------------- §3 Integration risk matrix
    sections.append(_risk_matrix_section(scored))

    # ---------------------------------------------------------------- §4 SWOT
    sections.append(_swot_section(scored, blocks))

    # ---------------------------------------------------------------- §5 Maintenance burden
    sections.append(_maintenance_burden_section(scored, inventory))

    # ---------------------------------------------------------------- §6 Day-30/60/90 plan
    sections.append(_day_n_section(scored))

    # ---------------------------------------------------------------- §7 Persona narrative blocks (faithful surfacing)
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

    # ---------------------------------------------------------------- recommendation ladder
    recommendation = _build_recommendation_ladder(
        verdict=recommendation_verdict,
        score=score,
        pass_threshold=pass_threshold,
        distinction_threshold=distinction_threshold,
        critical=crit,
        high=high,
    )

    deliverable = Deliverable(
        use_case="acquisition_diligence",
        kind="acquisition_memo",
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


def _subtitle_for_recommendation(verdict: str, score: int) -> str:
    return {
        "proceed": f"Recommended for acquisition. Overall score {score}/100.",
        "proceed_with_conditions": f"Acquire only if conditions close. Score {score}/100.",
        "defer": f"Defer acquisition pending remediation. Score {score}/100.",
        "decline": f"Decline acquisition at this stage. Score {score}/100.",
    }.get(verdict, f"Acquisition assessment. Score {score}/100.")


def _rationale_sentence(
    verdict: str,
    *,
    critical: int,
    high: int,
) -> str:
    """Cover-page rationale, framed for the acquisition reader.

    Post-RSF: no longer cites the made-up ``pass_threshold`` / score-vs-bar
    arithmetic. The RSF assessment block immediately below the cover
    surfaces the persona-weighted total (PE/M&A row of the §3 matrix);
    this rationale frames the verdict in acquisition language without
    reciting the math.
    """
    if verdict == "proceed":
        return (
            "Asset clears the diligence bar with no critical blockers. "
            "Integration cost is bounded by the items called out in the RSF "
            "assessment below; see the recommendation ladder for closing items."
        )
    if verdict == "proceed_with_conditions":
        crit_text = f"{critical} critical blocker{'s' if critical != 1 else ''}" if critical else None
        high_text = f"{high} high-severity issue{'s' if high != 1 else ''}" if high else None
        constraints = ", ".join(t for t in (crit_text, high_text) if t) or "outstanding high-severity issues"
        return (
            f"Acquirable subject to closing items: {constraints} must resolve before close, "
            "either via seller-funded remediation or escrow holdback. "
            "See the RSF assessment for grounded sub-criterion scores; the "
            "recommendation ladder for the deal-term path."
        )
    if verdict == "defer":
        return (
            "Defer until the seller closes the gap shown in the RSF assessment "
            "below. Re-run diligence with updated evidence (SBOM, dependency-"
            "scan reports, signed releases) when seller has remediated."
        )
    return (
        f"Decline at proposed terms: {critical} critical blocker(s) gate the "
        "acquisition. Integration cost would dominate expected upside; the RSF "
        "assessment below names the specific issues. Recommendation ladder "
        "shows the conditions that would unlock a renewed offer."
    )


def _cover_facts(scored: dict) -> list[tuple[str, str]]:
    """Acquisition-side facts: inheritance scale, dep surface, on-call risk, KT risk."""
    inv = scored.get("inventory") or {}
    cls = scored.get("classification") or {}
    git = (scored.get("repo_meta") or {}).get("git_summary") or {}
    facts: list[tuple[str, str]] = []

    archetype = (cls.get("repo_archetype") or "unknown").replace("_", " ")
    facts.append(("Asset class", archetype))

    loc = inv.get("source_loc")
    files = inv.get("source_files")
    facts.append(
        ("Codebase you'd inherit", f"{loc:,} LOC across {files} files" if isinstance(loc, int) else f"{loc} LOC · {files} files")
    )

    deps = inv.get("runtime_dependencies", "n/a")
    facts.append(
        ("Runtime dep surface", f"{deps} packages — vetting cost on close" if deps != "n/a" else "n/a")
    )

    test_files = inv.get("test_files") or 0
    src_files = inv.get("source_files") or 0
    if isinstance(test_files, int) and isinstance(src_files, int) and src_files > 0:
        ratio = test_files / src_files
        facts.append(
            ("Test trust signal", f"{ratio:.0%} test/source — {'thin' if ratio < 0.2 else 'workable'}")
        )

    bus = git.get("estimated_bus_factor") or git.get("bus_factor")
    contributors = git.get("contributor_count") or git.get("unique_authors")
    if bus is not None or contributors is not None:
        bus_text = (
            "bus factor 1 — single point of failure" if str(bus) in {"1", "1.0"}
            else f"bus factor {bus or 'n/a'}"
        )
        facts.append(("Knowledge-transfer risk", f"{contributors or 'n/a'} contrib · {bus_text}"))

    network = "internet-facing" if cls.get("network_exposure") else "internal-only"
    facts.append(("Operational surface", network))

    return facts


# ---------------------------------------------------------------------------
# §1 Position
# ---------------------------------------------------------------------------


def _position_section(scored: dict, blocks: list) -> Section:
    integration_block = next(
        (b for b in blocks if (b.key or "").lower().replace(" ", "_") == "integration_risk"),
        None,
    )
    paragraphs: list[str] = []
    if integration_block:
        paragraphs.append(integration_block.summary)
    cls = scored.get("classification") or {}
    archetype = (cls.get("repo_archetype") or "unknown").replace("_", " ")
    confidence = cls.get("classification_confidence")
    paragraphs.append(
        f"The system is classified as a **{archetype}** with classification "
        f"confidence {confidence if confidence is not None else 'n/a'}. "
        "Integration cost depends primarily on whether your existing release "
        "and security tooling already covers this archetype."
    )
    return Section(
        title="1. Position",
        kind="prose",
        summary="Where this asset sits in your portfolio, and what you'd be integrating.",
        data={"paragraphs": paragraphs},
    )


# ---------------------------------------------------------------------------
# §2 What we're buying — capability radar
# ---------------------------------------------------------------------------


def _what_we_are_buying_section(scored: dict) -> Section:
    cats = category_scores_list(scored)
    axes = [
        (
            _VOCAB.category_labels.get(c.get("category", ""))
            or str(c.get("category", "")).replace("_", " ").title(),
            int(c.get("score", 0) or 0),
            int(c.get("max_score", 0) or 0),
        )
        for c in cats
        if c.get("applicable", True) and int(c.get("max_score", 0) or 0) > 0
    ]
    svg = category_radar(axes=axes, title=_VOCAB.radar_title) if axes else ""
    return Section(
        title="2. What you're acquiring",
        kind="chart",
        summary=_VOCAB.radar_caption,
        chart_svg=svg,
        data={"axes": axes},
    )


# ---------------------------------------------------------------------------
# §3 Risk matrix
# ---------------------------------------------------------------------------


def _risk_matrix_section(scored: dict) -> Section:
    findings = top_findings(scored, n=10)
    points: list[MatrixPoint] = []
    for f in findings:
        sev = (f.get("severity") or "low").lower()
        conf = (f.get("confidence") or "medium").lower()
        mag = float(f.get("score_impact", {}).get("magnitude", 0)) / 10.0
        # Likelihood proxy = confidence; impact proxy = severity × magnitude.
        likelihood = {"high": 0.85, "medium": 0.55, "low": 0.3}.get(conf, 0.5)
        impact = min(
            1.0,
            {"critical": 0.95, "high": 0.8, "medium": 0.55, "low": 0.3, "info": 0.15}.get(sev, 0.4)
            * (0.7 + 0.3 * mag),
        )
        label = (f.get("subcategory") or f.get("id") or "finding").replace("_", " ")
        points.append(
            MatrixPoint(
                label=label,
                x=likelihood,
                y=impact,
                severity=sev,
                note=(f.get("statement") or "")[:140],
            )
        )
    svg = risk_matrix(
        risks=points,
        title=_VOCAB.risk_title,
        x_label=_VOCAB.risk_x,
        y_label=_VOCAB.risk_y,
        quadrant_labels=_VOCAB.risk_quadrants,
    )
    return Section(
        title="3. Integration risk surface",
        kind="chart",
        summary=_VOCAB.risk_caption,
        chart_svg=svg,
        data={"point_count": len(points)},
    )


# ---------------------------------------------------------------------------
# §4 SWOT
# ---------------------------------------------------------------------------


def _swot_section(scored: dict, blocks: list) -> Section:
    cats = category_scores_list(scored)
    strengths: list[str] = []
    weaknesses: list[str] = []
    for c in cats:
        if not c.get("applicable", True):
            continue
        max_score = int(c.get("max_score", 0) or 0)
        score = int(c.get("score", 0) or 0)
        if max_score <= 0:
            continue
        ratio = score / max_score
        label = (
            _VOCAB.category_labels.get(c.get("category", ""))
            or str(c.get("category", "")).replace("_", " ").title()
        )
        if ratio >= 0.9:
            strengths.append(
                f"**{label}** scores {score}/{max_score} — you'd inherit this in good shape."
            )
        elif ratio < 0.5:
            weaknesses.append(
                f"**{label}** scores {score}/{max_score} — direct cost on day one."
            )

    if not strengths:
        strengths.append("No category retained ≥90% of its points — see §5 for the dominant burdens.")

    if not weaknesses:
        weaknesses.append("No category fell below 50% — primary risks come from individual findings (§3).")

    # Opportunities = score-lift potential from remediation; threats = blockers + dependency concentration.
    opportunities = _opportunities_from_remediation(scored)
    threats = _threats_from_blockers_and_deps(scored, blocks)

    return Section(
        title="4. SWOT",
        kind="swot",
        summary=(
            "Strengths and weaknesses are derived from per-category scores; "
            "opportunities map to score lift available from remediation; "
            "threats list the issues that would survive a 'pass' verdict."
        ),
        data={
            "strengths": strengths,
            "weaknesses": weaknesses,
            "opportunities": opportunities,
            "threats": threats,
        },
    )


def _opportunities_from_remediation(scored: dict) -> list[str]:
    plan = scored.get("remediation_plan") or scored.get("remediation") or {}
    tasks = plan.get("tasks") or []
    if not tasks:
        return ["Remediation plan not run — opportunities not enumerated."]
    grouped: dict[str, float] = {}
    for t in tasks:
        phase = t.get("phase", "phase_other")
        grouped[phase] = grouped.get(phase, 0.0) + float(t.get("expected_score_delta") or 0)
    out: list[str] = []
    for phase, delta in sorted(grouped.items(), key=lambda kv: -kv[1]):
        if delta <= 0:
            continue
        nice = phase.replace("_", " ").title()
        out.append(f"{nice}: closing this phase recovers ~{delta:.1f} points of score lift.")
    if not out:
        out.append("Remediation plan present but no positive score lift projected.")
    return out[:5]


def _threats_from_blockers_and_deps(scored: dict, blocks: list) -> list[str]:
    out: list[str] = []
    for block in blocks:
        for callout in block.callouts or []:
            sev = (callout.severity or "info").lower()
            if sev in {"critical", "high"}:
                out.append(f"[{sev}] {callout.message}")
    if not out:
        crits = critical_blockers(scored)
        for b in crits:
            out.append(f"[critical] {b.get('title', 'Critical blocker')}")
    return out[:6] or ["No critical or high callouts in persona narrative."]


# ---------------------------------------------------------------------------
# §5 Maintenance burden
# ---------------------------------------------------------------------------


def _maintenance_burden_section(scored: dict, inventory: dict) -> Section:
    cls = scored.get("classification") or {}
    git = (scored.get("repo_meta") or {}).get("git_summary") or {}

    facts: list[SectionFact] = []
    facts.append(SectionFact(label="Source LOC", value=str(inventory.get("source_loc", "n/a"))))
    facts.append(SectionFact(label="Test files", value=str(inventory.get("test_files", "n/a"))))
    facts.append(SectionFact(label="Test/source ratio", value=str(inventory.get("test_to_source_ratio", "n/a"))))
    facts.append(SectionFact(label="Runtime deps", value=str(inventory.get("runtime_dependencies", "n/a"))))
    facts.append(SectionFact(label="Workflow jobs", value=str(inventory.get("workflow_jobs", "n/a"))))
    bus_factor = git.get("estimated_bus_factor") or git.get("bus_factor")
    if bus_factor is not None:
        facts.append(SectionFact(label="Bus factor (estimate)", value=str(bus_factor),
                                 severity="critical" if str(bus_factor) in {"1", "1.0"} else None))
    network = "yes" if cls.get("network_exposure") else "no"
    facts.append(SectionFact(label="Network exposure", value=network,
                             severity="high" if cls.get("network_exposure") else None))

    paragraphs: list[str] = [
        (
            "Maintenance burden is the steady-state cost of owning the codebase "
            "after the deal closes. The metrics below summarize the inputs your "
            "team will inherit on day one."
        ),
        _knowledge_transfer_paragraph(git),
    ]

    return Section(
        title="5. Maintenance burden",
        kind="facts",
        summary="Steady-state ownership cost: scale, test coverage signal, dependency surface.",
        facts=facts,
        data={"paragraphs": paragraphs},
    )


def _knowledge_transfer_paragraph(git: dict) -> str:
    bus = git.get("estimated_bus_factor") or git.get("bus_factor")
    contributors = git.get("contributor_count") or git.get("unique_authors") or "n/a"
    if bus and str(bus) in {"1", "1.0"}:
        return (
            f"Knowledge-transfer risk is **high**: bus factor of 1 against "
            f"{contributors} historical contributors. Plan a hands-on transition "
            "with the original author(s) for at least the first two release cycles."
        )
    return (
        f"Knowledge-transfer risk is moderate ({contributors} historical contributors, "
        f"bus factor {bus or 'n/a'}). Standard onboarding via README + docs should suffice."
    )


# ---------------------------------------------------------------------------
# §6 Day-30/60/90 plan
# ---------------------------------------------------------------------------


def _day_n_section(scored: dict) -> Section:
    plan = scored.get("remediation_plan") or scored.get("remediation") or {}
    tasks = plan.get("tasks") or []

    by_phase: dict[str, list[dict]] = {}
    for t in tasks:
        by_phase.setdefault(t.get("phase", "phase_other"), []).append(t)

    day_30 = _day_n_items(by_phase, ["phase_1_security"], default_label="Phase 1 (security)")
    day_60 = _day_n_items(
        by_phase,
        ["phase_2_contracts", "phase_3_tests"],
        default_label="Phase 2–3 (contracts / tests)",
    )
    day_90 = _day_n_items(
        by_phase,
        ["phase_4_ci", "phase_5_docs"],
        default_label="Phase 4–5 (CI / docs)",
    )

    if not tasks:
        # Without a remediation plan we still emit an honest schedule.
        crit = critical_blockers(scored)
        high = high_blockers(scored)
        day_30 = [f"Close {len(crit)} critical blocker(s) and rotate any leaked credentials."] if crit else [
            "Re-run assessment with remediation enabled to populate this plan."
        ]
        day_60 = [
            f"Address {len(high)} high-severity issue(s) and tighten dependency hygiene."
        ] if high else ["Stand up CI parity with your house standard."]
        day_90 = ["Migrate ownership, finalize docs, and integrate into the standard release pipeline."]

    return Section(
        title="6. Day-30 / Day-60 / Day-90 integration plan",
        kind="day_n",
        summary=(
            "Time-boxed plan derived from the remediation phases. Each window "
            "is scoped so a single owner can ship it without holding open the "
            "next window's work."
        ),
        data={"day_30": day_30, "day_60": day_60, "day_90": day_90},
    )


def _day_n_items(by_phase: dict[str, list[dict]], phases: list[str], *, default_label: str) -> list[str]:
    items: list[str] = []
    for phase in phases:
        for t in by_phase.get(phase, []):
            title = t.get("title") or t.get("subcategory") or "Remediation task"
            effort = t.get("effort", "n/a")
            delta = t.get("expected_score_delta")
            delta_text = f" (+{float(delta):.1f} pts)" if delta else ""
            items.append(f"{title} — effort {effort}{delta_text}")
    return items[:6] or [f"No tasks routed to {default_label}; window left for integration overhead."]


# ---------------------------------------------------------------------------
# Recommendation ladder
# ---------------------------------------------------------------------------


def _build_recommendation_ladder(
    *,
    verdict: str,
    score: int,
    pass_threshold: int,
    distinction_threshold: int,
    critical: list[dict],
    high: list[dict],
) -> Recommendation:
    headline_map = {
        "proceed": "Proceed with the acquisition.",
        "proceed_with_conditions": "Proceed only if conditions close before close.",
        "defer": "Defer until the seller closes the gap.",
        "decline": "Decline at the current price/terms.",
    }
    headline = headline_map.get(verdict, "Recommendation pending.")

    options: list[RecommendationOption] = []
    must_close: list[str] = []

    for blocker in critical:
        must_close.append(
            f"Close: {blocker.get('title', 'Critical blocker')} — {blocker.get('reason', '')}"
        )

    if verdict == "proceed":
        options.append(
            RecommendationOption(
                verdict="proceed",
                condition="Standard close.",
                expected_score_after=score,
                rationale="Score above distinction threshold and no critical blockers.",
            )
        )
    elif verdict == "proceed_with_conditions":
        options.append(
            RecommendationOption(
                verdict="proceed",
                condition=f"All {len(critical)} critical blocker(s) closed before close.",
                expected_score_after=min(100, score + 10),
                rationale="Removes critical blockers from steady-state inheritance.",
            )
        )
        options.append(
            RecommendationOption(
                verdict="proceed_with_conditions",
                condition=f"Phase-1 remediation (security) committed in 30 days post-close.",
                expected_score_after=min(100, score + 5),
                rationale="Bridge the gap with contractual remediation milestones.",
            )
        )
        options.append(
            RecommendationOption(
                verdict="defer",
                condition="Seller declines to close blockers in escrow window.",
                expected_score_after=score,
                rationale="Without remediation, integration cost likely exceeds upside.",
            )
        )
    elif verdict == "defer":
        options.append(
            RecommendationOption(
                verdict="proceed_with_conditions",
                condition=f"Score reaches ≥{pass_threshold} after seller-funded remediation.",
                expected_score_after=pass_threshold,
                rationale="Acquirable at the post-remediation score, not the current one.",
            )
        )
        options.append(
            RecommendationOption(
                verdict="defer",
                condition="Standard re-run in 60 days with seller's remediation evidence.",
                expected_score_after=score + 8,
                rationale="Default path — give the seller a window to lift the score.",
            )
        )
        options.append(
            RecommendationOption(
                verdict="decline",
                condition="No remediation forthcoming.",
                expected_score_after=score,
                rationale="Asset is below the diligence bar; integration cost dominates.",
            )
        )
    else:  # decline
        options.append(
            RecommendationOption(
                verdict="decline",
                condition="Asset stays below the bar; no path to proceed at current price.",
                expected_score_after=score,
                rationale=f"Score {score} with {len(critical)} critical blocker(s) — integration risk too high.",
            )
        )

    return Recommendation(
        headline=headline,
        options=options,
        must_close_before_proceeding=must_close,
    )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

register_deliverable_builder("acquisition_diligence", build)


__all__ = ["build"]
