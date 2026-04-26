"""Per-persona vocabulary tables (SDLC-073 follow-up).

A persona deliverable is more than rearranged sections — every label the
reader sees is in their frame. A VC reading a "Code quality" axis on a
radar reads engineering jargon; reading "Engineering rigor" they read a
quality the thesis depends on. Same axis, same data, different persona.

This module centralises the vocabulary so the four builders stay terse
and consistent. Each persona registers:

- ``category_labels``: {category_id → reader-facing label}
- ``risk_axes``: x/y axis labels and quadrant labels for the 2×2 risk matrix
- ``effort_axes``: x/y axis labels and quadrant labels for the effort×impact matrix
- ``radar_title``, ``risk_title``, ``effort_title``, ``trajectory_title``
- ``section_captions``: short copy keys → persona-voiced caption text

A single :func:`vocab_for` helper resolves all of the above and falls
back to a neutral "engineering" voice for unknown personas.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PersonaVocab:
    """All persona-specific copy in one place."""

    category_labels: dict[str, str] = field(default_factory=dict)
    risk_x: str = "Likelihood"
    risk_y: str = "Impact"
    risk_quadrants: tuple[str, str, str, str] = (
        "Low likelihood · High impact",
        "High likelihood · High impact",
        "Low likelihood · Low impact",
        "High likelihood · Low impact",
    )
    effort_x: str = "Effort"
    effort_y: str = "Score impact"
    effort_quadrants: tuple[str, str, str, str] = (
        "Low effort · High impact (DO FIRST)",
        "High effort · High impact",
        "Low effort · Low impact",
        "High effort · Low impact (DEFER)",
    )
    radar_title: str = "Capability radar"
    risk_title: str = "Risk matrix"
    effort_title: str = "Effort × impact"
    trajectory_title: str = "Score trajectory"
    radar_caption: str = (
        "Capability spread across the eight assessment categories. "
        "Anywhere the polygon dips inward is a thin spot worth attention."
    )
    risk_caption: str = (
        "Top production findings plotted by likelihood (confidence) and "
        "impact (severity × magnitude)."
    )
    effort_caption: str = (
        "Tasks plotted by engineering effort (x) and projected score lift (y). "
        "Upper-left is do-first; lower-right defers."
    )
    trajectory_caption: str = (
        "Cumulative projected score after each remediation phase."
    )


_BASE_CATEGORY_LABELS = {
    "architecture_design": "Architecture",
    "code_quality_contracts": "Code quality",
    "testing_quality_gates": "Testing",
    "security_posture": "Security",
    "dependency_release_hygiene": "Dependency hygiene",
    "documentation_truthfulness": "Documentation",
    "maintainability_operability": "Maintainability",
    "reproducibility_research_rigor": "Reproducibility",
}


# ---------------------------------------------------------------------------
# Acquisition diligence — the reader is a buyer / integration lead.
# ---------------------------------------------------------------------------

ACQUISITION_VOCAB = PersonaVocab(
    category_labels={
        "architecture_design": "Architecture portability",
        "code_quality_contracts": "Code maintainability",
        "testing_quality_gates": "Test trust",
        "security_posture": "Inherited security debt",
        "dependency_release_hygiene": "Dependency drag",
        "documentation_truthfulness": "Onboarding readiness",
        "maintainability_operability": "Day-1 ownership cost",
        "reproducibility_research_rigor": "Build reproducibility",
    },
    risk_x="Probability we hit this during integration",
    risk_y="Day-1 ownership cost if it fires",
    risk_quadrants=(
        "Latent — could surface post-close",
        "Surfaces on integration · costly to absorb",
        "Tolerable noise — file under maintenance",
        "Surfaces but contained — annoyance, not blocker",
    ),
    effort_x="Engineer-days to close in our org",
    effort_y="Reduction in inherited risk",
    effort_quadrants=(
        "Cheap wins — capture in escrow conditions",
        "Heavy lift — negotiate seller-funded",
        "Defer — accept as steady-state cost",
        "Skip — not worth the engineer time",
    ),
    radar_title="Capability radar — what you'd inherit on close",
    risk_title="Integration risk surface",
    effort_title="Integration cost vs. risk reduction",
    trajectory_title="Score lift if seller funds remediation",
    radar_caption=(
        "Each axis is rated against what your org would have to assume on day one. "
        "Low values on Day-1 ownership cost or Inherited security debt translate "
        "directly into integration headcount. Anything below 50% is a candidate "
        "for an escrow condition or price adjustment."
    ),
    risk_caption=(
        "Each dot is a finding from the seller's codebase that would land in your "
        "lap on close. Read the upper-right quadrant as: high confidence we'll hit "
        "this, and it costs real engineer time to resolve. Those drive the "
        "must-close list before signing."
    ),
    effort_caption=(
        "Cost-vs-reduction triage of inherited issues. Items in the upper-left are "
        "the cheap-wins-in-escrow list — fix-cost is small relative to the risk "
        "they retire. Lower-right items are the kind your team should refuse to "
        "absorb without seller funding."
    ),
    trajectory_caption=(
        "Where the asset's score would land if the seller closes each remediation "
        "phase before close. Use this to size escrow holdbacks or price "
        "adjustments — deal size should not exceed the post-remediation score."
    ),
)


# ---------------------------------------------------------------------------
# VC diligence — the reader is an investor checking the pitch against the code.
# ---------------------------------------------------------------------------

VC_VOCAB = PersonaVocab(
    category_labels={
        "architecture_design": "Technical moat support",
        "code_quality_contracts": "Engineering rigor",
        "testing_quality_gates": "Shipping discipline",
        "security_posture": "Customer-trust signal",
        "dependency_release_hygiene": "Vendor concentration risk",
        "documentation_truthfulness": "Pitch ↔ code consistency",
        "maintainability_operability": "Operational maturity",
        "reproducibility_research_rigor": "Result reproducibility",
    },
    risk_x="Likelihood we encounter in diligence",
    risk_y="Downside to the investment thesis",
    risk_quadrants=(
        "Tail risk — only surfaces under stress",
        "Will surface in DD · contradicts thesis",
        "Background noise — not thesis-relevant",
        "Surfaces in DD · ignorable for thesis",
    ),
    effort_x="Founder time to address",
    effort_y="Thesis credibility lift",
    effort_quadrants=(
        "Founder can de-risk in a sprint",
        "Heavy lift — re-priced or re-staged round",
        "Already covered — no thesis impact",
        "Not worth founder time pre-close",
    ),
    radar_title="Where the code substantiates the pitch (filled) vs. typical investable baseline (dashed)",
    risk_title="Risks that would surface in technical DD",
    effort_title="Founder-effort vs. thesis-credibility lift",
    trajectory_title="Credibility lift per remediation phase",
    radar_caption=(
        "Filled polygon: where this asset actually scores against each axis "
        "of the technical thesis. Dashed line: the median early-stage tech "
        "company a check of this size typically pursues. Wherever the dashed "
        "line sits OUTSIDE the filled polygon, the pitch claim has thin code "
        "evidence — those are the founder questions."
    ),
    risk_caption=(
        "Each dot is a finding likely to come up in technical due diligence. "
        "Position is interpreted from the investor side: x is how confident we "
        "are it'll surface; y is how much it punctures the thesis if true. "
        "Upper-right items become priced-in or kill the round."
    ),
    effort_caption=(
        "What it would take the founder to address each issue against how "
        "much credibility lift it buys the thesis. Upper-left is what to ask "
        "the founder to ship before term-sheet; lower-right is what NOT to "
        "spend founder time on pre-close."
    ),
    trajectory_caption=(
        "Treat each phase as a credibility milestone tied to a tranche. "
        "Capital release should track the founder's actual delivery against "
        "these projected lifts."
    ),
)


# ---------------------------------------------------------------------------
# Engineering triage — the reader is the engineer who owns the codebase.
# ---------------------------------------------------------------------------

ENGINEERING_VOCAB = PersonaVocab(
    category_labels={
        "architecture_design": "Architecture",
        "code_quality_contracts": "Code health",
        "testing_quality_gates": "Test discipline",
        "security_posture": "Security",
        "dependency_release_hygiene": "Dep / release hygiene",
        "documentation_truthfulness": "Docs accuracy",
        "maintainability_operability": "Maintainability",
        "reproducibility_research_rigor": "Build reproducibility",
    },
    risk_x="Confidence (likely to actually hit prod)",
    risk_y="Customer-visible impact when it does",
    risk_quadrants=(
        "Latent — only matters under load",
        "Will hit prod · pages someone",
        "Annoyance — backlog candidate",
        "Hits prod but invisible to users",
    ),
    effort_x="Engineer-days to close",
    effort_y="Customer-visible reliability gain",
    effort_quadrants=(
        "Pick up this sprint",
        "Plan for next quarter",
        "Defer — cleanup tax",
        "Don't bother",
    ),
    radar_title="Code health by category",
    risk_title="Failure modes — likelihood × user impact",
    effort_title="Triage matrix — effort vs. reliability gain",
    trajectory_title="Score lift per remediation phase",
    radar_caption=(
        "Score per applicable category. Categories with the smallest filled "
        "radius are where reliability is thinnest — those drive the next "
        "sprint's planning."
    ),
    risk_caption=(
        "Each dot is a finding. Position is interpreted operationally: how "
        "likely is this to actually land on the on-call rotation, and how "
        "loud will it be when it does. Upper-right is the page-someone "
        "list."
    ),
    effort_caption=(
        "Engineering-effort vs. customer-visible reliability gain. Treat the "
        "DO FIRST quadrant as the unblock list; treat DEFER as cleanup tax "
        "you don't owe today."
    ),
    trajectory_caption=(
        "Score lift per phase if we work the remediation plan in order. "
        "Use this to size the sprint allocation and pace expectations with "
        "the team."
    ),
)


# ---------------------------------------------------------------------------
# Remediation agent — the reader is an automated coding agent.
# ---------------------------------------------------------------------------

REMEDIATION_VOCAB = PersonaVocab(
    category_labels={
        "architecture_design": "architecture",
        "code_quality_contracts": "code_quality",
        "testing_quality_gates": "testing",
        "security_posture": "security",
        "dependency_release_hygiene": "deps_release",
        "documentation_truthfulness": "docs",
        "maintainability_operability": "maintainability",
        "reproducibility_research_rigor": "reproducibility",
    },
    risk_x="finding.confidence",
    risk_y="finding.severity × magnitude",
    risk_quadrants=(
        "low confidence · high severity",
        "high confidence · high severity",
        "low confidence · low severity",
        "high confidence · low severity",
    ),
    effort_x="task.effort",
    effort_y="task.expected_score_delta",
    effort_quadrants=(
        "low effort · high delta — execute first",
        "high effort · high delta — schedule",
        "low effort · low delta — execute when blocked",
        "high effort · low delta — skip",
    ),
    radar_title="category_score / max_score per category",
    risk_title="finding cluster · confidence × impact",
    effort_title="task cluster · effort × score-delta",
    trajectory_title="cumulative score after each phase",
    radar_caption=(
        "Per-category score ratio. Use to validate that remediation "
        "monotonically improves each axis between phase commits — any axis "
        "regression is a calibration error."
    ),
    risk_caption=(
        "Finding distribution. Address in the order: high confidence × high "
        "severity → linked task IDs. Items outside the upper-right quadrant "
        "are not allowed to advance the task pointer."
    ),
    effort_caption=(
        "Task distribution by effort and expected score delta. Execute "
        "upper-left first; commit per task; verify with the task's "
        "verification_commands before advancing."
    ),
    trajectory_caption=(
        "Calibration target: cumulative score after each phase. After "
        "executing a phase, re-run the assessor; observed score must land "
        "within ±25% of the projection or stop and re-plan."
    ),
)


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, PersonaVocab] = {
    "acquisition_diligence": ACQUISITION_VOCAB,
    "vc_diligence": VC_VOCAB,
    "engineering_triage": ENGINEERING_VOCAB,
    "remediation_agent": REMEDIATION_VOCAB,
}


def vocab_for(use_case: str) -> PersonaVocab:
    """Return the vocabulary for ``use_case`` or a neutral default."""
    return _REGISTRY.get(use_case, PersonaVocab(category_labels=dict(_BASE_CATEGORY_LABELS)))


def relabel_category(use_case: str, category_id: str) -> str:
    """Persona-specific category label, falling back to the base label."""
    vocab = vocab_for(use_case)
    return (
        vocab.category_labels.get(category_id)
        or _BASE_CATEGORY_LABELS.get(category_id)
        or category_id.replace("_", " ").title()
    )


__all__ = [
    "ACQUISITION_VOCAB",
    "ENGINEERING_VOCAB",
    "PersonaVocab",
    "REMEDIATION_VOCAB",
    "VC_VOCAB",
    "relabel_category",
    "vocab_for",
]
