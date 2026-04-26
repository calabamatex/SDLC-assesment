"""VC-diligence thesis-evaluation builder (SDLC-075).

Audience: an investor-side analyst evaluating whether the technology
substantiates the thesis pitched to them. The deliverable answers four
questions:

1. **Does the code substantiate the pitch?** — claim-by-claim evaluation
   table (status: substantiated / partial / unsubstantiated / contradicted).
2. **Is there a real technical moat?** — capability radar versus an
   archetype baseline.
3. **Is the team execution-mature?** — execution-maturity gap chart and
   commentary.
4. **Where is the risk concentration?** — risk matrix, founder questions,
   recommendation pill.

The full finding listing remains as the engineering appendix.
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
    high_blockers,
    production_findings,
    register_deliverable_builder,
    score_band,
    top_findings,
)
from sdlc_assessor.renderer.persona import narrate_for_persona

_CATEGORY_LABEL = {
    "architecture_design": "Architecture",
    "code_quality_contracts": "Code quality",
    "testing_quality_gates": "Testing",
    "security_posture": "Security",
    "dependency_release_hygiene": "Dependencies",
    "documentation_truthfulness": "Documentation",
    "maintainability_operability": "Maintainability",
    "reproducibility_research_rigor": "Reproducibility",
}

# Plausible "sufficient" capability ratios by category for an early-stage
# product company shopping a VC round. Used as the baseline polygon on the
# capability radar — a thesis is more credible when the founder's score is
# at least at this level on the load-bearing categories.
_VC_BASELINE = {
    "architecture_design": 0.6,
    "code_quality_contracts": 0.6,
    "testing_quality_gates": 0.55,
    "security_posture": 0.55,
    "dependency_release_hygiene": 0.5,
    "documentation_truthfulness": 0.6,
    "maintainability_operability": 0.5,
    "reproducibility_research_rigor": 0.4,
}


def build(scored: dict, profile: dict) -> Deliverable:
    scoring = scored.get("scoring") or {}
    blocks = narrate_for_persona(scored, profile)

    score = int(round(float(scoring.get("overall_score", 0))))
    verdict = str(scoring.get("verdict", "fail"))
    crit = critical_blockers(scored)
    high = high_blockers(scored)
    pass_threshold = int(profile.get("pass_threshold", 72))
    distinction_threshold = int(profile.get("distinction_threshold", 88))
    recommendation_verdict = derive_recommendation(
        score=score,
        pass_threshold=pass_threshold,
        distinction_threshold=distinction_threshold,
        critical_count=len(crit),
        high_count=len(high),
    )

    cover = CoverPage(
        title="VC Diligence — Thesis Evaluation",
        subtitle=_subtitle(recommendation_verdict, score),
        recommendation=recommendation_verdict,
        recommendation_rationale=_rationale(recommendation_verdict, score, len(crit), len(high)),
        score=score,
        score_band=score_band(score),
        headline_facts=_cover_facts(scored, blocks),
        score_gauge_svg=score_gauge(score=score, verdict=verdict),
        classification_line=classification_line(scored),
    )

    sections: list[Section] = []

    # §1 Thesis substantiation table.
    sections.append(_thesis_evaluation_section(scored, blocks))

    # §2 Capability radar vs VC baseline.
    sections.append(_moat_radar_section(scored))

    # §3 Execution-maturity gap.
    sections.append(_execution_maturity_section(scored, blocks))

    # §4 Risk concentration matrix.
    sections.append(_risk_concentration_section(scored))

    # §5 Founder questions.
    sections.append(_founder_questions_section(scored, blocks))

    # §6 Persona narrative blocks (faithful surfacing).
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

    recommendation = _build_recommendation(
        verdict=recommendation_verdict,
        score=score,
        pass_threshold=pass_threshold,
        distinction_threshold=distinction_threshold,
        critical=crit,
        high=high,
    )

    return Deliverable(
        use_case="vc_diligence",
        kind="vc_thesis",
        cover=cover,
        sections=sections,
        recommendation=recommendation,
        appendix=_appendix_for(scored),
        persona_blocks=blocks,
    )


# ---------------------------------------------------------------------------
# Cover-page helpers
# ---------------------------------------------------------------------------


def _subtitle(verdict: str, score: int) -> str:
    return {
        "proceed": f"Thesis substantiated. Investment-grade. Score {score}/100.",
        "proceed_with_conditions": f"Thesis partially substantiated. Score {score}/100.",
        "defer": f"Thesis under-substantiated. Defer pending diligence answers. Score {score}/100.",
        "decline": f"Thesis materially overclaims vs evidence. Score {score}/100.",
    }.get(verdict, f"Investment thesis evaluation. Score {score}/100.")


def _rationale(verdict: str, score: int, critical: int, high: int) -> str:
    if verdict == "proceed":
        return (
            "Code substantiates the pitched technical claims with no critical "
            "blockers; investment recommended subject to commercial diligence."
        )
    if verdict == "proceed_with_conditions":
        return (
            f"Substantiation is partial; {critical} critical and {high} high "
            "issues warrant founder Q&A before term-sheet."
        )
    if verdict == "defer":
        return (
            "Score sits below the diligence bar — recommend defer pending "
            "founder answers and a re-run after fixes."
        )
    return (
        "Evidence does not back the headline pitch and severe issues persist; "
        "decline at proposed terms."
    )


def _cover_facts(scored: dict, blocks: list) -> list[tuple[str, str]]:
    inv = scored.get("inventory") or {}
    facts: list[tuple[str, str]] = []
    facts.append(("Technical scale", f"{inv.get('source_loc', 'n/a')} LOC · {inv.get('source_files', 'n/a')} files"))
    facts.append(("Test coverage signal", f"{inv.get('test_files', 'n/a')} test files"))
    facts.append(("CI maturity", f"{inv.get('workflow_files', 'n/a')} workflows · {inv.get('workflow_jobs', 'n/a')} jobs"))
    overclaim = sum(1 for b in blocks if "overclaim" in (b.key or "").lower())
    if overclaim:
        facts.append(("Overclaim flags", f"{overclaim} narrative block(s) raised"))
    facts.append(("Critical blockers", str(sum(1 for b in scored.get("hard_blockers") or [] if b.get("severity") == "critical"))))
    return facts


# ---------------------------------------------------------------------------
# §1 Thesis substantiation table
# ---------------------------------------------------------------------------


def _thesis_evaluation_section(scored: dict, blocks: list) -> Section:
    """Claim-by-claim evaluation derived from inventory + classification.

    The four claims a VC pitch typically makes about a tech asset:

    1. We have built a substantive system.
    2. The codebase is engineered, not a demo.
    3. Operations are real (CI, releases, tests).
    4. The team can execute (commit history, contributor breadth).

    Each claim resolves to substantiated / partial / unsubstantiated /
    contradicted based on inventory and finding signals.
    """
    inv = scored.get("inventory") or {}
    cls = scored.get("classification") or {}
    git = (scored.get("repo_meta") or {}).get("git_summary") or {}

    claims: list[dict] = []

    # Claim 1: substantive system.
    loc = int(inv.get("source_loc") or 0)
    files = int(inv.get("source_files") or 0)
    if loc > 5000 and files > 30:
        c1_status = "substantiated"
        c1_evidence = f"{loc:,} LOC across {files} files supports a non-trivial system."
    elif loc > 1000:
        c1_status = "partial"
        c1_evidence = f"{loc:,} LOC across {files} files — substantive but small."
    elif loc > 0:
        c1_status = "unsubstantiated"
        c1_evidence = f"Only {loc:,} LOC — system is at the demo scale."
    else:
        c1_status = "contradicted"
        c1_evidence = "No source files detected."
    claims.append(
        {
            "claim": "We have built a substantive system.",
            "evidence_status": c1_status,
            "evidence_text": c1_evidence,
        }
    )

    # Claim 2: engineered codebase.
    secrets = sum(
        1 for f in production_findings(scored)
        if (f.get("subcategory") or "").lower() in {"probable_secrets", "subprocess_shell_true", "exec_call", "execsync"}
    )
    if secrets >= 3:
        c2_status = "contradicted"
        c2_evidence = f"{secrets} unsafe-pattern findings (secrets / shell exec) suggest demo-grade code."
    elif secrets > 0:
        c2_status = "partial"
        c2_evidence = f"{secrets} unsafe-pattern finding(s); engineering posture is mixed."
    else:
        confs = (cls.get("classification_confidence") or 0) >= 0.6
        c2_status = "substantiated" if confs else "partial"
        c2_evidence = "No unsafe-pattern findings; classification confidence aligns with engineered intent."
    claims.append(
        {
            "claim": "The codebase is engineered, not a demo.",
            "evidence_status": c2_status,
            "evidence_text": c2_evidence,
        }
    )

    # Claim 3: real operations (CI / releases / tests).
    workflows = int(inv.get("workflow_files") or 0)
    tests = int(inv.get("test_files") or 0)
    if workflows >= 1 and tests >= 5:
        c3_status = "substantiated"
        c3_evidence = f"{workflows} workflow file(s) and {tests} test file(s) indicate real CI + test discipline."
    elif workflows >= 1 or tests >= 1:
        c3_status = "partial"
        c3_evidence = f"{workflows} workflow file(s) and {tests} test file(s) — operations exist but are thin."
    else:
        c3_status = "contradicted"
        c3_evidence = "No CI workflows and no test files — operations are not in evidence."
    claims.append(
        {
            "claim": "Operations are real (CI, releases, tests).",
            "evidence_status": c3_status,
            "evidence_text": c3_evidence,
        }
    )

    # Claim 4: team can execute (commit cadence, contributor breadth).
    contributors = git.get("contributor_count") or git.get("unique_authors") or 0
    commits = git.get("commit_count") or inv.get("commit_count") or 0
    bus = git.get("estimated_bus_factor") or git.get("bus_factor")
    try:
        contributors_n = int(contributors)
    except (TypeError, ValueError):
        contributors_n = 0
    try:
        commits_n = int(commits)
    except (TypeError, ValueError):
        commits_n = 0
    if contributors_n >= 3 and commits_n >= 50:
        c4_status = "substantiated"
        c4_evidence = f"{contributors_n} contributors · {commits_n} commits — team is in evidence."
    elif contributors_n >= 1 and commits_n >= 10:
        c4_status = "partial"
        c4_evidence = (
            f"{contributors_n} contributor(s) · {commits_n} commits · bus factor {bus or 'n/a'}. "
            "Concentration risk if bus factor is 1."
        )
    else:
        c4_status = "unsubstantiated"
        c4_evidence = "Commit history thin; team scaling claim not in evidence."
    claims.append(
        {
            "claim": "The team can execute (commit history, contributor breadth).",
            "evidence_status": c4_status,
            "evidence_text": c4_evidence,
        }
    )

    # Pull any block-level callouts that mention overclaim or credibility.
    overclaim_callouts: list[str] = []
    for block in blocks:
        if "credib" in (block.key or "").lower() or "overclaim" in (block.key or "").lower():
            for callout in block.callouts or []:
                overclaim_callouts.append(callout.message)

    summary = (
        "Each headline pitch claim is rated against codebase evidence. "
        "Substantiated = code clearly backs the claim; partial = backs it but "
        "with caveats; unsubstantiated = no evidence either way; contradicted = "
        "evidence runs against the claim."
    )

    return Section(
        title="1. Thesis substantiation",
        kind="claims_evaluation",
        summary=summary,
        data={"claims": claims, "overclaim_callouts": overclaim_callouts},
    )


# ---------------------------------------------------------------------------
# §2 Capability radar vs baseline
# ---------------------------------------------------------------------------


def _moat_radar_section(scored: dict) -> Section:
    cats = category_scores_list(scored)
    axes: list[tuple[str, int, int]] = []
    baseline: list[float] = []
    for c in cats:
        if not c.get("applicable", True):
            continue
        max_score = int(c.get("max_score", 0) or 0)
        if max_score <= 0:
            continue
        category = c.get("category", "")
        axes.append(
            (
                _CATEGORY_LABEL.get(category, str(category).replace("_", " ").title()),
                int(c.get("score", 0) or 0),
                max_score,
            )
        )
        baseline.append(_VC_BASELINE.get(category, 0.55))

    svg = category_radar(axes=axes, baseline=baseline) if axes else ""
    return Section(
        title="2. Technical-moat support",
        kind="chart",
        summary=(
            "Capability spread (filled polygon) versus a typical-VC-bar baseline "
            "(dashed). Categories where the asset clears the baseline are the "
            "thesis's load-bearing strengths; those that fall short need founder Q&A."
        ),
        chart_svg=svg,
        data={"axes": axes, "baseline": baseline},
    )


# ---------------------------------------------------------------------------
# §3 Execution-maturity gap
# ---------------------------------------------------------------------------


def _execution_maturity_section(scored: dict, blocks: list) -> Section:
    inv = scored.get("inventory") or {}
    cls = scored.get("classification") or {}

    facts: list[SectionFact] = []
    facts.append(SectionFact(label="Maturity profile (declared)", value=str(cls.get("maturity_profile", "unknown"))))
    facts.append(SectionFact(label="Classification confidence", value=str(cls.get("classification_confidence", "n/a"))))
    facts.append(SectionFact(label="Workflow jobs", value=str(inv.get("workflow_jobs", "n/a"))))
    facts.append(SectionFact(label="Tag count", value=str(inv.get("tag_count", "n/a"))))
    facts.append(SectionFact(label="Release count", value=str(inv.get("release_count", "n/a"))))
    facts.append(
        SectionFact(
            label="Test/source ratio",
            value=str(inv.get("test_to_source_ratio", "n/a")),
        )
    )

    paragraphs = [
        (
            "Execution maturity is read from CI breadth, release cadence, and "
            "test depth. A thesis that pitches scale or enterprise readiness "
            "needs evidence in all three columns — partial evidence here is "
            "the most common cause of a 'proceed_with_conditions' verdict."
        )
    ]
    exec_block = next((b for b in blocks if "execution" in (b.key or "").lower()), None)
    if exec_block:
        paragraphs.append(exec_block.summary)

    return Section(
        title="3. Execution maturity",
        kind="facts",
        summary="Hard signals of operational discipline: CI breadth, release cadence, test depth.",
        facts=facts,
        data={"paragraphs": paragraphs},
    )


# ---------------------------------------------------------------------------
# §4 Risk concentration matrix
# ---------------------------------------------------------------------------


def _risk_concentration_section(scored: dict) -> Section:
    findings = top_findings(scored, n=10)
    points: list[MatrixPoint] = []
    for f in findings:
        sev = (f.get("severity") or "low").lower()
        conf = (f.get("confidence") or "medium").lower()
        mag = float(f.get("score_impact", {}).get("magnitude", 0)) / 10.0
        likelihood = {"high": 0.8, "medium": 0.5, "low": 0.3}.get(conf, 0.5)
        impact = min(
            1.0,
            {"critical": 0.95, "high": 0.8, "medium": 0.55, "low": 0.3, "info": 0.15}.get(sev, 0.4) * (0.7 + 0.3 * mag),
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
    svg = risk_matrix(risks=points)
    return Section(
        title="4. Risk concentration",
        kind="chart",
        summary=(
            "Findings plotted by likelihood (confidence) and impact (severity × "
            "deduction magnitude). Concentration in the upper-right quadrant "
            "is the thesis's downside scenario."
        ),
        chart_svg=svg,
        data={"point_count": len(points)},
    )


# ---------------------------------------------------------------------------
# §5 Founder questions
# ---------------------------------------------------------------------------


def _founder_questions_section(scored: dict, blocks: list) -> Section:
    questions: list[str] = []
    inv = scored.get("inventory") or {}
    git = (scored.get("repo_meta") or {}).get("git_summary") or {}
    cls = scored.get("classification") or {}

    if int(inv.get("workflow_files") or 0) == 0:
        questions.append("Why is there no CI? What's your release process today?")
    if int(inv.get("test_files") or 0) == 0:
        questions.append(
            "There are no test files in the repository. How do you validate behaviour pre-release?"
        )
    bus = git.get("estimated_bus_factor") or git.get("bus_factor")
    if str(bus) in {"1", "1.0"}:
        questions.append("Bus factor is 1 — what's the contingency plan if the lead engineer leaves?")
    if cls.get("network_exposure"):
        questions.append(
            "The system has network exposure. What's your security review cadence and last-pen-test status?"
        )
    crit = critical_blockers(scored)
    if crit:
        for blocker in crit[:3]:
            questions.append(f"Walk us through {blocker.get('title', 'the critical blocker')} and why it persists.")
    overclaim = sum(1 for b in blocks if "overclaim" in (b.key or "").lower())
    if overclaim:
        questions.append("Several pitch claims have only partial code-side substantiation — can you reconcile?")

    if not questions:
        questions.append("No critical due-diligence questions surfaced — confirm with commercial DD.")

    return Section(
        title="5. Founder questions",
        kind="questions",
        summary=(
            "Diligence questions inferred from gaps between the pitch and the "
            "code. Use these in the founder follow-up before term-sheet."
        ),
        data={"questions": questions[:8]},
    )


# ---------------------------------------------------------------------------
# Recommendation ladder
# ---------------------------------------------------------------------------


def _build_recommendation(
    *,
    verdict: str,
    score: int,
    pass_threshold: int,
    distinction_threshold: int,
    critical: list[dict],
    high: list[dict],
) -> Recommendation:
    headline = {
        "proceed": "Invest at proposed terms; thesis is substantiated.",
        "proceed_with_conditions": "Conditional invest pending founder Q&A and milestone covenants.",
        "defer": "Defer; re-run after seller closes the gap.",
        "decline": "Decline at proposed terms; thesis is under-substantiated.",
    }.get(verdict, "Recommendation pending.")

    options: list[RecommendationOption] = []
    if verdict == "proceed":
        options.append(
            RecommendationOption(
                verdict="proceed",
                condition="Standard close.",
                expected_score_after=score,
                rationale="Thesis substantiated and no critical blockers.",
            )
        )
    elif verdict == "proceed_with_conditions":
        options.append(
            RecommendationOption(
                verdict="proceed",
                condition=f"All {len(critical)} critical issue(s) closed and milestone covenants signed.",
                expected_score_after=min(100, score + 8),
                rationale="Removes critical risk before capital deploys.",
            )
        )
        options.append(
            RecommendationOption(
                verdict="proceed_with_conditions",
                condition="Tranched investment on remediation milestones.",
                expected_score_after=min(100, score + 5),
                rationale="Aligns capital release with proven execution.",
            )
        )
    elif verdict == "defer":
        options.append(
            RecommendationOption(
                verdict="defer",
                condition="Re-diligence in 60–90 days after seller-funded remediation.",
                expected_score_after=min(100, score + 10),
                rationale="Default path — give the asset a window to substantiate.",
            )
        )
        options.append(
            RecommendationOption(
                verdict="proceed_with_conditions",
                condition="Lower headline price by 25%+ to account for remediation cost.",
                expected_score_after=score,
                rationale="Mark-to-evidence rather than mark-to-pitch.",
            )
        )
    else:
        options.append(
            RecommendationOption(
                verdict="decline",
                condition="No path at proposed terms.",
                expected_score_after=score,
                rationale="Thesis materially overclaims vs evidence.",
            )
        )

    must_close = [
        f"Close: {b.get('title', 'Critical issue')} — {b.get('reason', '')}"
        for b in critical
    ]
    return Recommendation(
        headline=headline,
        options=options,
        must_close_before_proceeding=must_close,
    )


register_deliverable_builder("vc_diligence", build)


__all__ = ["build"]
