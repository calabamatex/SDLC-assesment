"""Remediation-agent action plan builder (SDLC-077).

Audience: an automated coding agent (or a human acting as one). The
deliverable is closer to an executable script than a memo:

- explicit task order (no "we recommend you consider…");
- per-task verification commands taken from the remediation plan;
- patch-safety pre-flight checks (working-tree clean, branch parity);
- a score-lift trajectory so the agent can sanity-check its own progress.

Compared to the engineering-triage report, this deliverable's body sticks
to imperative actions and machine-friendly fields. It still emits the
score gauge and trajectory chart so a human reviewer can audit the agent
quickly.
"""

from __future__ import annotations

from sdlc_assessor.renderer.charts import (
    score_gauge,
    score_lift_trajectory,
)
from sdlc_assessor.renderer.charts.trajectory import PhaseLift
from sdlc_assessor.renderer.deliverables._vocab import REMEDIATION_VOCAB
from sdlc_assessor.renderer.deliverables.base import (
    CoverPage,
    Deliverable,
    Recommendation,
    RecommendationOption,
    Section,
    SectionFact,
    _appendix_for,
    classification_line,
    critical_blockers,
    derive_recommendation,
    high_blockers,
    register_deliverable_builder,
    score_band,
)
from sdlc_assessor.renderer.persona import narrate_for_persona

_VOCAB = REMEDIATION_VOCAB


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
        title="Remediation Action Plan",
        subtitle=_subtitle(score, verdict, len(crit)),
        recommendation=recommendation_verdict,
        recommendation_rationale=(
            "Execute phases 1→5 in order; commit per task; verify after each "
            "phase. Re-run the RSF assessment between phases — observed sub-"
            "criterion deltas should align with the RSF anchors below. Halt "
            "and re-plan if any sub-criterion regresses between phases."
        ),
        score=score,
        score_band=score_band(score),
        headline_facts=_cover_facts(scored),
        score_gauge_svg=score_gauge(score=score, verdict=verdict),
        classification_line=classification_line(scored),
    )

    sections: list[Section] = [
        _preflight_section(scored),
        _ordered_tasks_section(scored),
        _verification_section(scored),
        _trajectory_section(scored, current_score=score),
        _patch_safety_section(scored),
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

    recommendation = Recommendation(
        headline="Execute task list in order; do not skip verification commands.",
        options=[
            RecommendationOption(
                verdict="proceed",
                condition="Each task's verification commands exit 0 before moving to the next.",
                rationale="Verification is the contract — no green, no advance.",
            ),
            RecommendationOption(
                verdict="proceed_with_conditions",
                condition="Hold open a session-level checkpoint between phases.",
                rationale="Lets a human spot regression before the next phase compounds it.",
            ),
        ],
        must_close_before_proceeding=[
            f"Close: {b.get('title', 'Critical blocker')} — {b.get('reason', '')}"
            for b in crit
        ],
    )

    deliverable = Deliverable(
        use_case="remediation_agent",
        kind="remediation_plan",
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


def _subtitle(score: int, verdict: str, crit: int) -> str:
    return (
        f"Imperative action plan for an autonomous fix loop. "
        f"Current score {score}/100 ({verdict}); {crit} critical blocker(s)."
    )


def _cover_facts(scored: dict) -> list[tuple[str, str]]:
    plan = scored.get("remediation_plan") or scored.get("remediation") or {}
    tasks = plan.get("tasks") or []
    by_phase: dict[str, int] = {}
    for t in tasks:
        by_phase[t.get("phase", "phase_other")] = by_phase.get(t.get("phase", "phase_other"), 0) + 1
    facts: list[tuple[str, str]] = []
    facts.append(("Total tasks", str(len(tasks))))
    for phase in ("phase_1_security", "phase_2_contracts", "phase_3_tests", "phase_4_ci", "phase_5_docs"):
        if phase in by_phase:
            facts.append((phase.replace("_", " ").title(), str(by_phase[phase])))
    return facts


# ---------------------------------------------------------------------------
# §1 Pre-flight
# ---------------------------------------------------------------------------


def _preflight_section(scored: dict) -> Section:
    """Static checklist any remediation agent must clear before starting."""
    items = [
        "`git status` — working tree must be clean.",
        "`git rev-parse --abbrev-ref HEAD` — confirm you are on the intended remediation branch.",
        "`git fetch && git rev-list HEAD..origin/main --count` — ensure no remote drift.",
        "`pip install -e \".[dev]\"` — install dependencies; confirm exit 0.",
        "`pytest -q` — capture pre-remediation baseline; record pass count.",
        "`python -m sdlc_assessor.cli run . --use-case remediation_agent --out-dir /tmp/baseline`"
        " — capture baseline scored.json and remediation_plan.json.",
    ]
    return Section(
        title="1. Pre-flight",
        kind="prose",
        summary="Run these checks before touching code. Bail if any fails.",
        data={"paragraphs": items},
    )


# ---------------------------------------------------------------------------
# §2 Ordered task list
# ---------------------------------------------------------------------------


def _ordered_tasks_section(scored: dict) -> Section:
    plan = scored.get("remediation_plan") or scored.get("remediation") or {}
    tasks = plan.get("tasks") or []
    rows: list[dict] = []
    phase_order = {
        "phase_1_security": 1,
        "phase_2_contracts": 2,
        "phase_3_tests": 3,
        "phase_4_ci": 4,
        "phase_5_docs": 5,
    }
    sev_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    for t in sorted(
        tasks,
        key=lambda t: (
            phase_order.get(t.get("phase", "phase_5_docs"), 9),
            sev_rank.get((t.get("severity") or "medium").lower(), 5),
            -float(t.get("expected_score_delta") or 0),
        ),
    ):
        rows.append(
            {
                "id": t.get("id"),
                "phase": t.get("phase", "phase_other"),
                "title": t.get("title") or t.get("subcategory") or "Remediation task",
                "change_type": t.get("change_type") or [],
                "target_paths": t.get("target_paths") or [],
                "anchor_guidance": t.get("anchor_guidance") or "",
                "implementation_steps": t.get("implementation_steps") or [],
                "verification_commands": t.get("verification_commands") or ["pytest -q"],
                "effort": t.get("effort") or "M",
                "expected_score_delta": t.get("expected_score_delta") or 0,
                "linked_finding_ids": t.get("linked_finding_ids") or [],
            }
        )
    if not rows:
        rows.append(
            {
                "id": "T-NO-PLAN",
                "phase": "phase_5_docs",
                "title": "Run the remediation planner to populate this section.",
                "change_type": ["update_docs"],
                "target_paths": [],
                "anchor_guidance": "",
                "implementation_steps": ["python -m sdlc_assessor.cli remediate <evidence> <scored> -o <out>"],
                "verification_commands": ["test -s <out>/remediation_plan.json"],
                "effort": "XS",
                "expected_score_delta": 0,
                "linked_finding_ids": [],
            }
        )
    return Section(
        title="2. Ordered task list",
        kind="remediation_table",
        summary=(
            "Tasks ordered by phase, then severity, then expected score delta. "
            "Execute top-to-bottom. Do not skip a task whose verification "
            "command fails."
        ),
        data={"tasks": rows, "task_count": len(rows)},
    )


# ---------------------------------------------------------------------------
# §3 Verification protocol
# ---------------------------------------------------------------------------


def _verification_section(scored: dict) -> Section:
    plan = scored.get("remediation_plan") or scored.get("remediation") or {}
    tasks = plan.get("tasks") or []
    cmd_set: dict[str, int] = {}
    for t in tasks:
        for cmd in t.get("verification_commands") or []:
            cmd_set[cmd] = cmd_set.get(cmd, 0) + 1
    paragraphs = [
        (
            "Run a task's `verification_commands` after every code change. "
            "If any exits non-zero, revert the change and re-plan; do not "
            "advance the task pointer until the gate is green."
        ),
        (
            "After completing a phase, re-run the assessment "
            "(`python -m sdlc_assessor.cli run . --use-case remediation_agent`) "
            "and compare the new score against the trajectory in §4. A delta "
            "more than 25% off the projection is a calibration warning."
        ),
    ]
    facts = [
        SectionFact(label=cmd, value=f"used by {count} task(s)")
        for cmd, count in sorted(cmd_set.items(), key=lambda kv: -kv[1])[:8]
    ]
    return Section(
        title="3. Verification protocol",
        kind="facts",
        summary="One verification gate per task; a phase-level gate after each phase.",
        facts=facts,
        data={"paragraphs": paragraphs, "command_frequencies": cmd_set},
    )


# ---------------------------------------------------------------------------
# §4 Score-lift trajectory
# ---------------------------------------------------------------------------


def _trajectory_section(scored: dict, *, current_score: int) -> Section:
    plan = scored.get("remediation_plan") or scored.get("remediation") or {}
    tasks = plan.get("tasks") or []
    deltas: dict[str, float] = {}
    for t in tasks:
        deltas[t.get("phase", "phase_other")] = deltas.get(t.get("phase", "phase_other"), 0.0) + float(
            t.get("expected_score_delta") or 0
        )
    phase_order = [
        ("phase_1_security", "Phase 1 · Security"),
        ("phase_2_contracts", "Phase 2 · Contracts"),
        ("phase_3_tests", "Phase 3 · Tests"),
        ("phase_4_ci", "Phase 4 · CI / release"),
        ("phase_5_docs", "Phase 5 · Documentation"),
    ]
    phases: list[PhaseLift] = []
    for key, label in phase_order:
        if key in deltas and deltas[key] > 0:
            phases.append(PhaseLift(label=label, delta=deltas[key]))
    svg = score_lift_trajectory(
        current_score=current_score,
        phases=phases,
        title=_VOCAB.trajectory_title,
    )
    return Section(
        title="4. Score-lift trajectory",
        kind="chart",
        summary=_VOCAB.trajectory_caption,
        chart_svg=svg,
        data={"phases": [{"label": p.label, "delta": p.delta} for p in phases]},
    )


# ---------------------------------------------------------------------------
# §5 Patch-safety reminders
# ---------------------------------------------------------------------------


def _patch_safety_section(scored: dict) -> Section:
    items = [
        "Make minimal diffs — one logical change per commit; conventional commit messages.",
        "Never delete files referenced from `target_paths` without confirming no other task depends on them.",
        "If a verification command depends on a tool that isn't installed, install it (note the install in the commit body); do not silently weaken the gate.",
        "Re-run `pytest -q` end-to-end after each phase even if the phase's tasks specified narrower verification commands.",
        "When closing a critical blocker, add a regression test in the same commit before declaring the blocker closed.",
    ]
    return Section(
        title="5. Patch-safety reminders",
        kind="prose",
        summary="Hard rules for the agent; ignore them and you will regress.",
        data={"paragraphs": items},
    )


register_deliverable_builder("remediation_agent", build)


__all__ = ["build"]
