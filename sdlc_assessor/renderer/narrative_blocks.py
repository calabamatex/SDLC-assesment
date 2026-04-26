"""Per-emphasis narrative-block builders (SDLC-068).

One builder per ``narrative_emphasis`` term across the four shipped
use-case profiles. Each builder returns a :class:`NarrativeBlock`
populated entirely from the scored payload — no LLM, no invented prose.

The builders are split by emphasis term (not by profile) so a profile
can mix and match. Importing this module registers all builders with
:func:`sdlc_assessor.renderer.persona.register_builder`.
"""

from __future__ import annotations

from collections.abc import Callable

from sdlc_assessor.renderer.persona import (
    NarrativeBlock,
    NarrativeCallout,
    NarrativeFact,
    category_score,
    count_by_subcategory,
    critical_blockers,
    find_one,
    high_blockers,
    production_findings,
    register_builder,
    top_findings,
)


def _scoring(scored: dict) -> dict:
    return scored.get("scoring") or {}


def _classification(scored: dict) -> dict:
    return scored.get("classification") or {}


def _inventory(scored: dict) -> dict:
    return scored.get("inventory") or {}


def _git_summary(scored: dict) -> dict:
    return (scored.get("repo_meta") or {}).get("git_summary") or {}


def _format_pct(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "n/a"
    return f"{(numerator / denominator) * 100:.0f}% ({numerator}/{denominator})"


# ---------------------------------------------------------------------------
# acquisition_diligence emphasis terms
# ---------------------------------------------------------------------------


def integration_risk(scored: dict, _profile: dict) -> NarrativeBlock:
    classification = _classification(scored)
    archetype = classification.get("repo_archetype", "unknown")
    network_exposure = classification.get("network_exposure", False)
    deployment = classification.get("deployment_surface", "unknown")
    crit = critical_blockers(scored)
    high = high_blockers(scored)

    facts: list[NarrativeFact] = [
        NarrativeFact("Repository archetype", str(archetype)),
        NarrativeFact("Deployment surface", str(deployment)),
        NarrativeFact("Network exposure", "yes" if network_exposure else "no"),
        NarrativeFact(
            "Critical / high blockers",
            f"{len(crit)} critical, {len(high)} high",
            severity="critical" if crit else ("high" if high else None),
        ),
    ]

    callouts: list[NarrativeCallout] = []
    for blocker in crit:
        callouts.append(
            NarrativeCallout(
                severity="critical",
                message=f"Pre-integration blocker: {blocker.get('title') or blocker.get('reason', '?')}",
            )
        )

    if archetype == "service" and network_exposure:
        summary = (
            "This repository exposes network-facing surface in a deployed-service "
            "shape. Integration into an acquirer's infrastructure carries the "
            "usual networked-service risks: TLS posture, ingress/egress controls, "
            "and runtime dependency parity must be validated before cutover."
        )
    elif archetype == "library":
        summary = (
            "Integration as a library carries comparatively low surface — the "
            "primary risk is API stability and consumer-side migration cost "
            "rather than runtime exposure."
        )
    elif crit:
        summary = (
            f"{len(crit)} critical hard-blocker(s) gate any acquisition integration. "
            "Each must be resolved on the seller side or carry an explicit "
            "carve-out in the deal terms before code can be merged into "
            "acquirer infrastructure."
        )
    else:
        summary = (
            "No critical integration blockers were detected. Proceed to dependency "
            "and maintenance-burden assessment."
        )
    return NarrativeBlock(
        key="integration_risk",
        title="Integration risk",
        summary=summary,
        facts=facts,
        callouts=callouts,
    )


def maintenance_burden(scored: dict, _profile: dict) -> NarrativeBlock:
    inventory = _inventory(scored)
    git = _git_summary(scored)
    test_files = int(inventory.get("test_files", 0) or 0)
    source_files = int(inventory.get("source_files", 0) or 0)
    workflow_files = int(inventory.get("workflow_files", 0) or 0)
    bus_factor = git.get("bus_factor")
    test_to_source = inventory.get("test_to_source_ratio")

    facts: list[NarrativeFact] = [
        NarrativeFact("Source files", str(source_files)),
        NarrativeFact("Test files", str(test_files)),
        NarrativeFact(
            "Test-to-source ratio",
            f"{float(test_to_source):.2f}" if isinstance(test_to_source, (int, float)) else "n/a",
        ),
        NarrativeFact("CI workflow files", str(workflow_files)),
        NarrativeFact(
            "Bus factor (≥5% commit share)",
            str(bus_factor) if isinstance(bus_factor, int) else "n/a",
            severity="high" if bus_factor == 1 else None,
        ),
    ]

    callouts: list[NarrativeCallout] = []
    if isinstance(bus_factor, int) and bus_factor == 1:
        callouts.append(
            NarrativeCallout(
                severity="high",
                message=(
                    "Bus factor of 1 — a single contributor authored ≥5% of recent "
                    "commits. Maintenance continuity is a serious post-acquisition "
                    "risk; surface this in the term sheet."
                ),
            )
        )

    if source_files == 0:
        summary = (
            "No production source files were detected. Maintenance burden cannot be "
            "estimated from this corpus; verify the scan scope is correct."
        )
    elif test_files == 0:
        summary = (
            "Zero test files were detected. Inheriting this codebase post-acquisition "
            "means inheriting an undiagnosed test-coverage gap; expect 4–8 weeks of "
            "stabilization work before confident change-making."
        )
    elif workflow_files == 0:
        summary = (
            "Tests exist but no CI workflows are configured. Maintenance overhead is "
            "manual: every change requires the acquirer's pipeline to run the test "
            "suite. Migrating to CI is a 1–2 day onboarding cost."
        )
    else:
        summary = (
            f"{test_files} tests over {source_files} source files (ratio "
            f"{float(test_to_source or 0):.2f}). CI is configured. Maintenance "
            "burden is shaped primarily by author concentration and dependency "
            "graph rather than testing posture."
        )
    return NarrativeBlock(
        key="maintenance_burden",
        title="Maintenance burden",
        summary=summary,
        facts=facts,
        callouts=callouts,
    )


def release_hygiene(scored: dict, _profile: dict) -> NarrativeBlock:
    inventory = _inventory(scored)
    classification = _classification(scored)
    git = _git_summary(scored)
    release_surface = classification.get("release_surface", "unknown")
    workflow_files = int(inventory.get("workflow_files", 0) or 0)
    workflow_jobs = int(inventory.get("workflow_jobs", 0) or 0)
    signing_coverage = git.get("signing_coverage")

    dep_graph = inventory.get("dependency_graph") or {}
    lockfile_count = len(dep_graph.get("lockfiles", []) or [])
    lockfile_missing = find_one(scored, "lockfile_missing")
    no_dependabot = find_one(scored, "no_dependabot_or_renovate")

    facts: list[NarrativeFact] = [
        NarrativeFact("Release surface", str(release_surface)),
        NarrativeFact("CI workflows", f"{workflow_files} ({workflow_jobs} jobs)"),
        NarrativeFact(
            "Commit signing coverage",
            f"{float(signing_coverage):.0%}" if isinstance(signing_coverage, (int, float)) else "n/a",
            severity="medium" if isinstance(signing_coverage, (int, float)) and signing_coverage < 0.2 else None,
        ),
        NarrativeFact("Lockfiles present", str(lockfile_count)),
    ]

    callouts: list[NarrativeCallout] = []
    if lockfile_missing:
        callouts.append(
            NarrativeCallout(
                severity="medium",
                message=(
                    f"{lockfile_missing.get('statement')}. Reproducible installs "
                    "depend on whoever runs the resolver next; for an acquired "
                    "codebase that's an unknown."
                ),
            )
        )
    if no_dependabot:
        callouts.append(
            NarrativeCallout(
                severity="low",
                message=(
                    "No Dependabot or Renovate configuration found. Dependency "
                    "upgrades require manual triage — a recurring carrying cost."
                ),
            )
        )
    if workflow_files == 0:
        callouts.append(
            NarrativeCallout(
                severity="high",
                message=(
                    "No CI workflows configured. Release hygiene depends on developer "
                    "discipline alone; in a production-maturity context this is a gap."
                ),
            )
        )

    if workflow_files > 0 and lockfile_count > 0 and not lockfile_missing:
        summary = (
            "Release hygiene is solid: CI is configured, lockfiles cover declared "
            "ecosystems, and the release surface is explicit. Continuity post-"
            "acquisition is straightforward."
        )
    else:
        summary = (
            "Release hygiene has gaps that translate to integration overhead. The "
            "acquirer should expect to author CI workflows, lockfiles, or both "
            "before treating this as a deployable artifact."
        )
    return NarrativeBlock(
        key="release_hygiene",
        title="Release hygiene",
        summary=summary,
        facts=facts,
        callouts=callouts,
    )


def dependency_concentration(scored: dict, _profile: dict) -> NarrativeBlock:
    inventory = _inventory(scored)
    dep_graph = inventory.get("dependency_graph") or {}
    runtime = dep_graph.get("runtime") or []
    dev = dep_graph.get("dev") or []
    lockfiles = dep_graph.get("lockfiles") or []
    excessive = find_one(scored, "excessive_runtime_deps")
    cargo_advisories = count_by_subcategory(
        scored,
        {f for f in {f.get("subcategory") for f in production_findings(scored)} if isinstance(f, str) and f.startswith("cargo_audit_")},
    )

    runtime_count = len(runtime)
    dev_count = len(dev)
    ecosystems = sorted({entry.get("ecosystem") for entry in runtime + dev if entry.get("ecosystem")})

    facts: list[NarrativeFact] = [
        NarrativeFact("Runtime dependencies", str(runtime_count)),
        NarrativeFact("Dev dependencies", str(dev_count)),
        NarrativeFact("Ecosystems", ", ".join(ecosystems) or "none"),
        NarrativeFact("Lockfiles present", str(len(lockfiles))),
    ]

    callouts: list[NarrativeCallout] = []
    if excessive:
        callouts.append(
            NarrativeCallout(
                severity="low",
                message=(
                    f"{runtime_count} runtime dependencies — supply-chain surface "
                    "is broad. Each is a future CVE-tracking obligation."
                ),
            )
        )
    if cargo_advisories:
        callouts.append(
            NarrativeCallout(
                severity="high",
                message=(
                    f"{cargo_advisories} RustSec advisory finding(s) from cargo-audit. "
                    "Treat as known unpatched CVE surface."
                ),
            )
        )

    if runtime_count == 0 and dev_count == 0:
        summary = (
            "No declared dependencies were detected. Either this codebase has zero "
            "runtime dependencies or the manifest format is not in the supported "
            "set (pip / npm / cargo / go); confirm before drawing conclusions."
        )
    elif runtime_count > 50:
        summary = (
            f"Runtime dependency surface is broad ({runtime_count} declared). Each "
            "transitive resolution is a future ownership cost; prioritize a "
            "dependency reduction pass during integration."
        )
    elif len(ecosystems) > 1:
        summary = (
            f"Polyglot dependency footprint across {len(ecosystems)} ecosystems "
            f"({', '.join(ecosystems)}). Each ecosystem carries its own update "
            "cadence and vulnerability tooling; budget for it."
        )
    else:
        summary = (
            f"{runtime_count} runtime / {dev_count} dev dependencies in a single "
            f"ecosystem ({ecosystems[0] if ecosystems else 'n/a'}). Concentration "
            "risk is modest."
        )
    return NarrativeBlock(
        key="dependency_concentration",
        title="Dependency concentration",
        summary=summary,
        facts=facts,
        callouts=callouts,
    )


def knowledge_transfer_risk(scored: dict, _profile: dict) -> NarrativeBlock:
    git = _git_summary(scored)
    bus_factor = git.get("bus_factor")
    top_authors = git.get("top_authors") or []
    codeowners = git.get("codeowners_present", False)
    coverage = git.get("codeowners_coverage")

    leading_author_share = top_authors[0].get("share") if top_authors else None
    facts: list[NarrativeFact] = [
        NarrativeFact(
            "Bus factor",
            str(bus_factor) if isinstance(bus_factor, int) else "n/a",
            severity="high" if bus_factor == 1 else ("medium" if bus_factor in (2, 3) else None),
        ),
        NarrativeFact(
            "Top-author share",
            f"{float(leading_author_share):.0%}" if isinstance(leading_author_share, (int, float)) else "n/a",
        ),
        NarrativeFact("CODEOWNERS present", "yes" if codeowners else "no"),
        NarrativeFact(
            "CODEOWNERS file coverage",
            f"{float(coverage):.0%}" if isinstance(coverage, (int, float)) else "n/a",
        ),
    ]

    callouts: list[NarrativeCallout] = []
    if isinstance(bus_factor, int) and bus_factor == 1:
        callouts.append(
            NarrativeCallout(
                severity="high",
                message=(
                    "A single author dominates recent commits. Knowledge-transfer risk "
                    "is concentrated in one person — a clean acquisition requires "
                    "a documented retention plan or a knowledge-extraction sprint."
                ),
            )
        )
    if not codeowners:
        callouts.append(
            NarrativeCallout(
                severity="low",
                message=(
                    "No CODEOWNERS file was found. Review responsibility is implicit "
                    "rather than codified — a hidden knowledge-transfer cost."
                ),
            )
        )

    if isinstance(bus_factor, int) and bus_factor >= 4 and codeowners:
        summary = (
            "Knowledge is distributed across at least four contributors and review "
            "responsibility is codified via CODEOWNERS. Knowledge-transfer risk is low."
        )
    elif isinstance(bus_factor, int) and bus_factor == 1:
        summary = (
            "Knowledge is concentrated in a single author. Plan a 4–8 week parallel-"
            "operation period after acquisition or expect velocity to drop "
            "sharply when the author exits."
        )
    else:
        summary = (
            "Knowledge transfer risk is moderate. The acquirer should plan for an "
            "explicit handoff sprint; review patterns and dependency boundaries "
            "are not yet self-documenting."
        )
    return NarrativeBlock(
        key="knowledge_transfer_risk",
        title="Knowledge-transfer risk",
        summary=summary,
        facts=facts,
        callouts=callouts,
    )


# ---------------------------------------------------------------------------
# vc_diligence emphasis terms
# ---------------------------------------------------------------------------


def credibility(scored: dict, _profile: dict) -> NarrativeBlock:
    documentation = category_score(scored, "documentation_truthfulness") or {}
    missing_readme = find_one(scored, "missing_readme")
    missing_security = find_one(scored, "missing_security_md")
    inventory = _inventory(scored)
    workflow_files = int(inventory.get("workflow_files", 0) or 0)

    doc_score = documentation.get("score")
    doc_max = documentation.get("max_score")

    facts: list[NarrativeFact] = [
        NarrativeFact(
            "documentation_truthfulness score",
            f"{doc_score}/{doc_max}" if doc_score is not None and doc_max else "n/a",
        ),
        NarrativeFact("README present", "no" if missing_readme else "yes"),
        NarrativeFact("SECURITY.md present", "no" if missing_security else "yes"),
        NarrativeFact("CI workflows", str(workflow_files)),
    ]

    callouts: list[NarrativeCallout] = []
    if missing_readme:
        callouts.append(
            NarrativeCallout(
                severity="medium",
                message=(
                    "README is missing. The first surface a diligence reviewer sees "
                    "is undocumented — a low-effort tell that contradicts maturity claims."
                ),
            )
        )

    if doc_score is not None and doc_max and doc_score >= doc_max - 1:
        summary = (
            "Documentation track-record is solid (full or near-full points). The "
            "claims-to-evidence ratio appears defensible; further diligence should "
            "probe execution maturity rather than narrative integrity."
        )
    else:
        summary = (
            "Documentation gaps are present. Marketing claims should be cross-"
            "checked against the codebase before being used in investor materials."
        )
    return NarrativeBlock(
        key="credibility",
        title="Credibility",
        summary=summary,
        facts=facts,
        callouts=callouts,
    )


def technical_moat_support(scored: dict, _profile: dict) -> NarrativeBlock:
    arch = category_score(scored, "architecture_design") or {}
    code_quality = category_score(scored, "code_quality_contracts") or {}
    inventory = _inventory(scored)
    source_loc = int(inventory.get("source_loc", 0) or 0)
    classification = _classification(scored)
    archetype = classification.get("repo_archetype", "unknown")

    facts: list[NarrativeFact] = [
        NarrativeFact(
            "architecture_design score",
            f"{arch.get('score', '?')}/{arch.get('max_score', '?')}",
        ),
        NarrativeFact(
            "code_quality_contracts score",
            f"{code_quality.get('score', '?')}/{code_quality.get('max_score', '?')}",
        ),
        NarrativeFact("Total source LOC", str(source_loc)),
        NarrativeFact("Archetype", str(archetype)),
    ]

    callouts: list[NarrativeCallout] = []
    arch_score = arch.get("score")
    arch_max = arch.get("max_score")
    if isinstance(arch_score, (int, float)) and isinstance(arch_max, (int, float)) and arch_max > 0:
        ratio = arch_score / arch_max
        if ratio < 0.5:
            callouts.append(
                NarrativeCallout(
                    severity="medium",
                    message=(
                        "Architecture-design score is below 50% of available points. "
                        "Defensibility claims should be calibrated against this gap."
                    ),
                )
            )

    if source_loc == 0:
        summary = (
            "No production source LOC was detected; technical moat cannot be assessed "
            "from this corpus."
        )
    else:
        summary = (
            f"Codebase is {source_loc} LOC of {archetype} shape. The strength of any "
            "technical moat narrative should be measured against the architecture and "
            "code-quality scores above, plus the distinctive detector signal (or lack of it)."
        )
    return NarrativeBlock(
        key="technical_moat_support",
        title="Technical moat support",
        summary=summary,
        facts=facts,
        callouts=callouts,
    )


def execution_maturity(scored: dict, _profile: dict) -> NarrativeBlock:
    inventory = _inventory(scored)
    git = _git_summary(scored)
    test_files = int(inventory.get("test_files", 0) or 0)
    workflow_files = int(inventory.get("workflow_files", 0) or 0)
    test_to_source = inventory.get("test_to_source_ratio")
    signing = git.get("signing_coverage")
    classification = _classification(scored)
    maturity_profile = classification.get("maturity_profile", "unknown")

    facts: list[NarrativeFact] = [
        NarrativeFact("Inferred maturity", str(maturity_profile)),
        NarrativeFact("Test files", str(test_files)),
        NarrativeFact(
            "Test-to-source ratio",
            f"{float(test_to_source):.2f}" if isinstance(test_to_source, (int, float)) else "n/a",
        ),
        NarrativeFact("CI workflows", str(workflow_files)),
        NarrativeFact(
            "Commit signing coverage",
            f"{float(signing):.0%}" if isinstance(signing, (int, float)) else "n/a",
        ),
    ]

    callouts: list[NarrativeCallout] = []
    if test_files == 0 and workflow_files == 0:
        callouts.append(
            NarrativeCallout(
                severity="high",
                message=(
                    "Zero tests and zero CI workflows. Execution maturity is "
                    "inconsistent with any production-readiness narrative."
                ),
            )
        )

    if maturity_profile == "production":
        summary = (
            "Repository is shaped like a production project (CI present, tests "
            "present, packaging declared). Execution maturity narrative is "
            "supportable on the structural evidence."
        )
    elif maturity_profile == "prototype":
        summary = (
            "Repository is shaped like a prototype, not a product. Investor "
            "materials calling this 'production-ready' should be challenged on "
            "specific evidence (test coverage, CI gates, release process)."
        )
    elif maturity_profile == "research":
        summary = (
            "Repository is shaped like a research artifact. Reproducibility, "
            "not production maturity, is the relevant frame."
        )
    else:
        summary = (
            "Maturity could not be inferred from structural signals alone. Manual "
            "review is required before claiming any specific execution maturity tier."
        )
    return NarrativeBlock(
        key="execution_maturity",
        title="Execution maturity",
        summary=summary,
        facts=facts,
        callouts=callouts,
    )


def risk_concentration(scored: dict, _profile: dict) -> NarrativeBlock:
    findings = production_findings(scored)
    by_category: dict[str, int] = {}
    for f in findings:
        cat = f.get("category", "unknown")
        by_category[cat] = by_category.get(cat, 0) + 1

    sorted_cats = sorted(by_category.items(), key=lambda t: -t[1])
    facts: list[NarrativeFact] = [
        NarrativeFact("Production findings (excl. fixtures)", str(len(findings)))
    ]
    for cat, count in sorted_cats[:5]:
        facts.append(NarrativeFact(cat, f"{count} findings"))

    callouts: list[NarrativeCallout] = []
    if sorted_cats:
        top_cat, top_count = sorted_cats[0]
        if len(findings) > 0 and top_count / len(findings) > 0.4:
            callouts.append(
                NarrativeCallout(
                    severity="medium",
                    message=(
                        f"{top_cat} alone accounts for {top_count/len(findings):.0%} of "
                        "production findings. Risk is concentrated in one category — a "
                        "single remediation focus could materially shift the score."
                    ),
                )
            )

    if not findings:
        summary = "No production findings — there is no risk concentration to report."
    else:
        summary = (
            f"{len(findings)} production findings span {len(by_category)} categories. "
            "Concentration is shown above; the strongest category is the natural "
            "first investment for remediation effort."
        )
    return NarrativeBlock(
        key="risk_concentration",
        title="Risk concentration",
        summary=summary,
        facts=facts,
        callouts=callouts,
    )


def overclaim_detection(scored: dict, _profile: dict) -> NarrativeBlock:
    """Find spots where the structural evidence contradicts a likely claim."""
    inventory = _inventory(scored)
    classification = _classification(scored)
    test_files = int(inventory.get("test_files", 0) or 0)
    workflow_files = int(inventory.get("workflow_files", 0) or 0)
    archetype = classification.get("repo_archetype", "unknown")
    maturity = classification.get("maturity_profile", "unknown")
    missing_readme = find_one(scored, "missing_readme")

    callouts: list[NarrativeCallout] = []
    facts: list[NarrativeFact] = []

    if archetype == "service" and test_files == 0:
        callouts.append(
            NarrativeCallout(
                severity="high",
                message=(
                    "Service-archetype repository with zero tests. A 'production' "
                    "claim against this codebase contradicts the structural evidence."
                ),
            )
        )
        facts.append(NarrativeFact("Service repo with zero tests", "yes", severity="high"))
    if maturity == "production" and workflow_files == 0:
        callouts.append(
            NarrativeCallout(
                severity="high",
                message=(
                    "Production-maturity inference, but no CI workflows. Either the "
                    "maturity claim is overstated or CI is configured outside "
                    "GitHub Actions (verify manually)."
                ),
            )
        )
        facts.append(NarrativeFact("Production claim with no CI", "yes", severity="high"))
    if missing_readme and archetype != "research_repo":
        callouts.append(
            NarrativeCallout(
                severity="medium",
                message=(
                    "Repository ships without a README. Marketing materials describing "
                    "this codebase as 'developer-ready' are not supported by the "
                    "structural evidence."
                ),
            )
        )
        facts.append(NarrativeFact("Missing README", "yes", severity="medium"))

    if not callouts:
        summary = (
            "No obvious overclaims surfaced — structural evidence and inferred "
            "shape line up. Diligence reviewers should still cross-check specific "
            "marketing claims against the detailed findings list."
        )
    else:
        summary = (
            f"{len(callouts)} potential overclaim(s) flagged below — points where "
            "structural evidence contradicts the typical narrative for this "
            "archetype/maturity combination. Investigate before relying on the "
            "associated marketing language."
        )
    return NarrativeBlock(
        key="overclaim_detection",
        title="Overclaim detection",
        summary=summary,
        facts=facts,
        callouts=callouts,
    )


# ---------------------------------------------------------------------------
# engineering_triage emphasis terms
# ---------------------------------------------------------------------------


def technical_debt(scored: dict, _profile: dict) -> NarrativeBlock:
    debt_subcats = {
        "broad_except_exception",
        "bare_except",
        "type_ignore",
        "any_usage",
        "empty_catch",
        "as_any",
        "console_usage",
        "print_usage",
        "go_fmt_println",
        "rust_unwrap_call",
        "rust_expect_call",
        "kotlin_not_null_assertion",
        "csharp_dynamic_type",
        "java_print_stack_trace",
        "module_level_assert",
        "mutable_default_argument",
    }
    findings = production_findings(scored)
    debt_findings = [f for f in findings if f.get("subcategory") in debt_subcats]

    by_subcat: dict[str, int] = {}
    for f in debt_findings:
        subcat = f.get("subcategory", "unknown")
        by_subcat[subcat] = by_subcat.get(subcat, 0) + 1

    facts: list[NarrativeFact] = [
        NarrativeFact("Technical-debt findings (production)", str(len(debt_findings))),
    ]
    for subcat, count in sorted(by_subcat.items(), key=lambda t: -t[1])[:6]:
        facts.append(NarrativeFact(subcat, f"{count}"))

    if not debt_findings:
        summary = (
            "No technical-debt patterns surfaced in production source. The codebase "
            "is in good shape for active development."
        )
    else:
        summary = (
            f"{len(debt_findings)} technical-debt findings across "
            f"{len(by_subcat)} pattern(s). These are not bugs — they're "
            "shortcuts that compound during refactors. Address them when "
            "touching the affected modules; don't open standalone debt-cleanup PRs."
        )
    return NarrativeBlock(
        key="technical_debt",
        title="Technical debt",
        summary=summary,
        facts=facts,
    )


def failure_modes(scored: dict, _profile: dict) -> NarrativeBlock:
    failure_subcats = {
        "subprocess_shell_true",
        "exec_usage",
        "exec_sync_usage",
        "eval_or_exec",
        "eval_usage",
        "function_constructor",
        "pickle_load_untrusted",
        "go_panic_call",
        "rust_unsafe_block",
        "rust_panic_macro",
        "rust_transmute_call",
        "kotlin_runtime_exec",
        "java_runtime_exec",
        "csharp_process_start",
        "csharp_unsafe_method",
        "go_unsafe_pointer",
    }
    findings = production_findings(scored)
    failures = [f for f in findings if f.get("subcategory") in failure_subcats]

    facts: list[NarrativeFact] = [
        NarrativeFact("Failure-mode findings", str(len(failures))),
        NarrativeFact("Critical blockers", str(len(critical_blockers(scored)))),
        NarrativeFact("High blockers", str(len(high_blockers(scored)))),
    ]

    callouts: list[NarrativeCallout] = []
    for f in failures[:3]:
        ev = (f.get("evidence") or [{}])[0]
        callouts.append(
            NarrativeCallout(
                severity=f.get("severity", "medium"),
                message=(
                    f"{f.get('statement', '')} — "
                    f"{ev.get('path', 'n/a')}:{ev.get('line_start', '?')}"
                ),
            )
        )

    if not failures:
        summary = "No production failure-mode signals (panic / unsafe / shell-out) were detected."
    else:
        summary = (
            f"{len(failures)} failure-mode signals warrant first-priority attention. "
            "Each is a runtime safety risk; deduplicate against the SAST findings "
            "above before opening tickets."
        )
    return NarrativeBlock(
        key="failure_modes",
        title="Failure modes",
        summary=summary,
        facts=facts,
        callouts=callouts,
    )


def code_level_evidence(scored: dict, _profile: dict) -> NarrativeBlock:
    top = top_findings(scored, n=8)
    facts: list[NarrativeFact] = []
    for f in top:
        ev = (f.get("evidence") or [{}])[0]
        location = f"{ev.get('path', 'n/a')}:{ev.get('line_start', '?')}"
        facts.append(
            NarrativeFact(
                label=f.get("subcategory") or "?",
                value=f"{f.get('statement', '')} — {location}",
                severity=f.get("severity"),
            )
        )

    if not top:
        summary = "No production findings to surface."
    else:
        summary = (
            f"Top {len(top)} production findings ranked by severity × confidence × "
            "magnitude. Each row is grounded in a concrete file and line number — "
            "use these as the engineering-triage starting set."
        )
    return NarrativeBlock(
        key="code_level_evidence",
        title="Code-level evidence",
        summary=summary,
        facts=facts,
    )


def implementation_priority(scored: dict, _profile: dict) -> NarrativeBlock:
    findings = production_findings(scored)
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

    def _rank(f: dict) -> tuple:
        return (
            severity_order.get(f.get("severity", "low"), 5),
            -float(f.get("score_impact", {}).get("magnitude", 0)),
            f.get("category", ""),
        )

    sorted_findings = sorted(findings, key=_rank)
    facts: list[NarrativeFact] = [
        NarrativeFact("Production findings (sorted by impact)", str(len(findings)))
    ]
    for f in sorted_findings[:8]:
        ev = (f.get("evidence") or [{}])[0]
        facts.append(
            NarrativeFact(
                label=f.get("subcategory") or "?",
                value=f"{f.get('statement', '')} ({ev.get('path', 'n/a')}:{ev.get('line_start', '?')})",
                severity=f.get("severity"),
            )
        )

    if not findings:
        summary = "No production findings — no implementation priority to set."
    else:
        critical_count = sum(1 for f in findings if f.get("severity") == "critical")
        high_count = sum(1 for f in findings if f.get("severity") == "high")
        summary = (
            f"Suggested order: critical first ({critical_count}), then high "
            f"({high_count}), then medium/low. Cluster fixes by category to "
            "reduce review overhead — single-category PRs review faster than "
            "scatter-shot ones."
        )
    return NarrativeBlock(
        key="implementation_priority",
        title="Implementation priority",
        summary=summary,
        facts=facts,
    )


# ---------------------------------------------------------------------------
# remediation_agent emphasis terms
# ---------------------------------------------------------------------------


def task_order(scored: dict, _profile: dict) -> NarrativeBlock:
    findings = production_findings(scored)
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for f in findings:
        sev = f.get("severity", "info")
        if sev in by_severity:
            by_severity[sev] += 1

    facts = [
        NarrativeFact("Critical findings", str(by_severity["critical"]), severity="critical" if by_severity["critical"] else None),
        NarrativeFact("High findings", str(by_severity["high"]), severity="high" if by_severity["high"] else None),
        NarrativeFact("Medium findings", str(by_severity["medium"])),
        NarrativeFact("Low findings", str(by_severity["low"])),
        NarrativeFact("Info findings", str(by_severity["info"])),
    ]
    summary = (
        "Recommended task order: resolve all critical and high findings before "
        "opening medium/low PRs. Each severity tier maps to a different review "
        "cadence — critical findings should be hot-fixed; medium and low can "
        "batch into weekly cleanup PRs."
    )
    _ = severity_order  # reserved for future ordering refinements
    return NarrativeBlock(
        key="task_order",
        title="Task order",
        summary=summary,
        facts=facts,
    )


def verification(scored: dict, _profile: dict) -> NarrativeBlock:
    inventory = _inventory(scored)
    test_files = int(inventory.get("test_files", 0) or 0)
    workflow_files = int(inventory.get("workflow_files", 0) or 0)
    test_to_source = inventory.get("test_to_source_ratio")

    facts = [
        NarrativeFact("Test files", str(test_files)),
        NarrativeFact("CI workflows", str(workflow_files)),
        NarrativeFact(
            "Test-to-source ratio",
            f"{float(test_to_source):.2f}" if isinstance(test_to_source, (int, float)) else "n/a",
        ),
    ]

    callouts: list[NarrativeCallout] = []
    if test_files == 0:
        callouts.append(
            NarrativeCallout(
                severity="high",
                message=(
                    "No tests detected. Every remediation PR will need to include "
                    "regression coverage as part of the change — the suite cannot "
                    "validate the fix on its own."
                ),
            )
        )
    if workflow_files == 0:
        callouts.append(
            NarrativeCallout(
                severity="medium",
                message="No CI workflows. Verification of agent-authored fixes is local-only.",
            )
        )

    summary = (
        "Each remediation task in the plan ships with a `verification_commands` "
        "block. Run those commands as the gate; do not assume passing tests imply "
        "the finding is fixed unless the test was written to prove it."
    )
    return NarrativeBlock(
        key="verification",
        title="Verification",
        summary=summary,
        facts=facts,
        callouts=callouts,
    )


def patch_safety(scored: dict, _profile: dict) -> NarrativeBlock:
    inventory = _inventory(scored)
    git = _git_summary(scored)
    bus_factor = git.get("bus_factor")
    test_to_source = inventory.get("test_to_source_ratio")

    facts: list[NarrativeFact] = [
        NarrativeFact(
            "Test-to-source ratio (rollback signal)",
            f"{float(test_to_source):.2f}" if isinstance(test_to_source, (int, float)) else "n/a",
        ),
        NarrativeFact("Bus factor", str(bus_factor) if isinstance(bus_factor, int) else "n/a"),
    ]

    callouts: list[NarrativeCallout] = []
    if isinstance(test_to_source, (int, float)) and test_to_source < 0.2:
        callouts.append(
            NarrativeCallout(
                severity="medium",
                message=(
                    "Test-to-source ratio is below 0.2 — patch-safety is low. "
                    "Prefer surgical fixes with explicit regression tests over "
                    "broad refactors."
                ),
            )
        )

    summary = (
        "Use stable anchors (function names, symbols, snippet text) rather than "
        "line numbers when applying fixes — line numbers drift during reviews. "
        "The remediation plan's `anchor_guidance` field is built for this."
    )
    return NarrativeBlock(
        key="patch_safety",
        title="Patch safety",
        summary=summary,
        facts=facts,
        callouts=callouts,
    )


def expected_score_lift(scored: dict, _profile: dict) -> NarrativeBlock:
    """Sum the expected-score-delta from a freshly-built remediation plan."""
    from sdlc_assessor.remediation.planner import build_remediation_plan

    plan = build_remediation_plan(scored)
    summary_block = plan.get("summary", {}) or {}
    total_delta = float(summary_block.get("expected_score_delta", 0) or 0)
    task_count = int(summary_block.get("task_count", 0) or 0)
    overall = (scored.get("scoring") or {}).get("overall_score")

    facts: list[NarrativeFact] = [
        NarrativeFact("Current overall score", str(overall) if overall is not None else "n/a"),
        NarrativeFact("Remediation tasks", str(task_count)),
        NarrativeFact("Expected total score lift", f"+{total_delta:.1f}"),
    ]

    if isinstance(overall, (int, float)):
        facts.append(
            NarrativeFact(
                "Projected score after remediation",
                str(min(100, int(round(overall + total_delta)))),
            )
        )

    if task_count == 0:
        summary = "No remediation tasks generated — nothing to lift."
    else:
        summary = (
            f"Remediation plan contains {task_count} tasks with a combined expected "
            f"score lift of +{total_delta:.1f} points. Per-phase deltas are in the "
            "remediation report; resolve phase 1 (security) tasks first for the "
            "largest single-PR impact."
        )
    return NarrativeBlock(
        key="expected_score_lift",
        title="Expected score lift",
        summary=summary,
        facts=facts,
    )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, Callable[[dict, dict], NarrativeBlock]] = {
    "integration_risk": integration_risk,
    "maintenance_burden": maintenance_burden,
    "release_hygiene": release_hygiene,
    "dependency_concentration": dependency_concentration,
    "knowledge_transfer_risk": knowledge_transfer_risk,
    "credibility": credibility,
    "technical_moat_support": technical_moat_support,
    "execution_maturity": execution_maturity,
    "risk_concentration": risk_concentration,
    "overclaim_detection": overclaim_detection,
    "technical_debt": technical_debt,
    "failure_modes": failure_modes,
    "code_level_evidence": code_level_evidence,
    "implementation_priority": implementation_priority,
    "task_order": task_order,
    "verification": verification,
    "patch_safety": patch_safety,
    "expected_score_lift": expected_score_lift,
}

for _key, _fn in _REGISTRY.items():
    register_builder(_key, _fn)


__all__ = [
    "code_level_evidence",
    "credibility",
    "dependency_concentration",
    "execution_maturity",
    "expected_score_lift",
    "failure_modes",
    "implementation_priority",
    "integration_risk",
    "knowledge_transfer_risk",
    "maintenance_burden",
    "overclaim_detection",
    "patch_safety",
    "release_hygiene",
    "risk_concentration",
    "task_order",
    "technical_debt",
    "technical_moat_support",
    "verification",
]
