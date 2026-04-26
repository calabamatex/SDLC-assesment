"""RSF v1.0 criterion definitions.

Every level anchor below is reproduced **verbatim** from the canonical
framework document at ``docs/frameworks/rsf_v1.0.md``. If any anchor
text appears to differ, the doc is the source of truth and this file is
wrong — open an issue, do not edit the anchors here without updating the
doc and verifying the change is intentional.

Identifier format: ``v1.0-D<dimension>.<subcriterion>``.
"""

from __future__ import annotations

from dataclasses import dataclass


RSF_VERSION = "v1.0"


@dataclass(frozen=True, slots=True)
class CriterionLevel:
    """One row of a sub-criterion's 0–5 anchor table."""

    level: int  # 0..5
    anchor: str


@dataclass(frozen=True, slots=True)
class Criterion:
    """A single RSF sub-criterion (e.g., ``v1.0-D2.3``)."""

    id: str  # "D1.1", "D2.3", etc.
    dimension_id: str  # "D1", "D2", etc.
    title: str
    levels: tuple[CriterionLevel, ...]
    framework_anchor: str  # the "Derived from" attribution at the dimension level
    primary_url: str  # the verified primary-source URL


@dataclass(frozen=True, slots=True)
class Dimension:
    """One of the 8 RSF dimensions (D1–D8)."""

    id: str  # "D1"..."D8"
    title: str
    scope: str  # "Repo" | "Repo (history-derived)" | "Repo (history + community)" | "Org-scoped"
    derived_from: str  # the "Derived from" attribution


# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------

RSF_DIMENSIONS: tuple[Dimension, ...] = (
    Dimension(
        id="D1",
        title="Code Quality & Maintainability",
        scope="Repo",
        derived_from=(
            "OpenSSF Scorecard CI-Tests / SAST / Code-Review probes; OWASP ASVS v5.0"
        ),
    ),
    Dimension(
        id="D2",
        title="Application Security Posture",
        scope="Repo",
        derived_from="OWASP Top 10; OWASP ASVS; MITRE CWE; NIST SSDF",
    ),
    Dimension(
        id="D3",
        title="Supply Chain Integrity",
        scope="Repo",
        derived_from=(
            "SLSA; CycloneDX; SPDX; Sigstore; in-toto; OpenSSF Scorecard"
        ),
    ),
    Dimension(
        id="D4",
        title="Delivery Performance",
        scope="Repo (history-derived)",
        derived_from=(
            "DORA Core Model. DORA performance levels (Elite / High / Medium / Low) "
            "are mapped to RSF 2/3/4/5; sub-Low maps to 0–1."
        ),
    ),
    Dimension(
        id="D5",
        title="Engineering Discipline",
        scope="Repo",
        derived_from=(
            "OpenSSF Scorecard Code-Review / Branch-Protection / CI-Tests probes; "
            "SPACE Activity dimension"
        ),
    ),
    Dimension(
        id="D6",
        title="Documentation & Transparency",
        scope="Repo",
        derived_from=(
            "OpenSSF Best Practices Badge passing/silver/gold criteria; "
            "OpenSSF Scorecard; OWASP SAMM Education & Guidance practice"
        ),
    ),
    Dimension(
        id="D7",
        title="Sustainability & Team Health",
        scope="Repo (history + community)",
        derived_from=(
            "SPACE Satisfaction & Performance dimensions; OpenSSF Scorecard "
            "Maintained probe; CHAOSS metrics (not independently verified during "
            "this build; flag for review)"
        ),
    ),
    Dimension(
        id="D8",
        title="Compliance & Governance Posture",
        scope="Org-scoped",
        derived_from=(
            "NIST CSF 2.0; NIST SSDF; ISO/IEC 27001:2022; AICPA SOC 2 / Trust "
            "Services Criteria; CSA CAIQ v4; regulatory frameworks per sector"
        ),
    ),
)


def _levels(*pairs: tuple[int, str]) -> tuple[CriterionLevel, ...]:
    return tuple(CriterionLevel(level=lvl, anchor=text) for lvl, text in pairs)


# ---------------------------------------------------------------------------
# Criteria — verbatim from RSF v1.0 §2
# ---------------------------------------------------------------------------

# Primary URLs from §11 Appendix.
_OPENSSF_SCORECARD = "https://github.com/ossf/scorecard/blob/main/docs/checks.md"
_OWASP_ASVS = "https://owasp.org/www-project-application-security-verification-standard/"
_OWASP_TOP10 = "https://owasp.org/www-project-top-ten/"
_MITRE_CWE = "https://cwe.mitre.org/"
_NIST_SSDF = "https://csrc.nist.gov/projects/ssdf"
_CYCLONEDX = "https://cyclonedx.org/"
_SPDX = "https://spdx.dev/"
_SIGSTORE = "https://sigstore.dev/"
_SLSA_LEVELS = "https://slsa.dev/spec/v1.0/levels"
_DORA_GUIDE = "https://dora.dev/guides/dora-metrics/"
_SPACE_ACM = "https://queue.acm.org/detail.cfm?id=3454124"
_OPENSSF_BADGE = "https://www.bestpractices.dev/"
_OWASP_SAMM = "https://owaspsamm.org/"
_CHAOSS = "https://chaoss.community/"
_NIST_CSF = "https://www.nist.gov/cyberframework"
_ISO_27001 = "https://www.iso.org/standard/27001"
_AICPA_SOC2 = (
    "https://www.aicpa-cima.com/topic/audit-assurance/audit-and-assurance-greater-than-soc-2"
)
_CSA_CAIQ = "https://cloudsecurityalliance.org/research/topics/caiq"


# Each criterion's `levels` are the 0–5 anchors from RSF v1.0 §2, verbatim.
# The order of bullets matches the doc; do not reorder.

RSF_CRITERIA: tuple[Criterion, ...] = (
    # --- D1. Code Quality & Maintainability -----------------------------------
    Criterion(
        id="D1.1",
        dimension_id="D1",
        title="Automated test coverage",
        levels=_levels(
            (0, "No automated tests in the repo."),
            (1, "Tests exist; not run in CI; coverage unmeasured."),
            (2, "Tests run in CI; line coverage <50% or suite has known flaky tests."),
            (3, "Line coverage 50–70%; CI gates merges on test pass; flakiness tracked."),
            (4, "Line coverage >70%; branch coverage measured; CI gates merges; flakiness <2%."),
            (5, "Line coverage >85%; mutation or property-based testing in continuous use; flakiness <0.5%."),
        ),
        framework_anchor="OpenSSF Scorecard CI-Tests",
        primary_url=_OPENSSF_SCORECARD,
    ),
    Criterion(
        id="D1.2",
        dimension_id="D1",
        title="Static analysis & lint discipline",
        levels=_levels(
            (0, "No SAST or linter in CI."),
            (1, "Linter or SAST configured but findings ignored."),
            (2, "Linter blocking; SAST advisory only."),
            (3, "Both linter and SAST configured; new findings block merge."),
            (4, "SAST tuned to project (custom rules), CodeQL or Semgrep policies versioned."),
            (5, "Continuous SAST + IaC + container scanning; findings tracked to closure with SLA."),
        ),
        framework_anchor="OpenSSF Scorecard SAST",
        primary_url=_OPENSSF_SCORECARD,
    ),
    Criterion(
        id="D1.3",
        dimension_id="D1",
        title="Code complexity / hotspot management",
        levels=_levels(
            (0, "No complexity tracking."),
            (1, "Complexity measurable but unaddressed; known hotspots accumulating."),
            (2, "Hotspots identified; refactor backlog exists."),
            (3, "Hotspot reduction part of every release."),
            (4, "Behavioral code analysis (e.g., CodeScene-style) tracked in dashboards."),
            (5, "Hotspot remediation tied to feature work; knowledge-concentration data informs onboarding."),
        ),
        framework_anchor="(no single primary; behavioral analysis literature)",
        primary_url="",
    ),
    # --- D2. Application Security Posture -------------------------------------
    Criterion(
        id="D2.1",
        dimension_id="D2",
        title="Known vulnerabilities in dependencies (CVE/OSV)",
        levels=_levels(
            (0, "≥1 critical CVE open >30 days; no scanning."),
            (1, "Scanning in place; critical findings >7 days unresolved."),
            (2, "Critical resolved <7 days; high findings tracked but unbounded."),
            (3, "All severity tiers have SLAs and are tracked to closure."),
            (4, "Automated dependency updates (Dependabot/Renovate) plus reachability analysis."),
            (5, "VEX statements published for unfixed findings to disambiguate exposure."),
        ),
        framework_anchor="NIST SSDF RV.1; OSV",
        primary_url=_NIST_SSDF,
    ),
    Criterion(
        id="D2.2",
        dimension_id="D2",
        title="Secrets in source / git history",
        levels=_levels(
            (0, "Active secrets discoverable; no scanning."),
            (1, "Secret scanning configured; historical secrets present and unrotated."),
            (2, "Pre-commit secret scanning; historical findings rotated and removed via filter-repo."),
            (3, "All secrets in vault (e.g., HashiCorp, AWS Secrets Manager); CI uses short-lived tokens."),
            (4, "OIDC / workload-identity for all CI secrets; no long-lived tokens."),
            (5, "Above + automated rotation cadence; periodic key-pair attestations."),
        ),
        framework_anchor="OWASP ASVS V2",
        primary_url=_OWASP_ASVS,
    ),
    Criterion(
        id="D2.3",
        dimension_id="D2",
        title="ASVS / Top 10 conformance",
        levels=_levels(
            (0, "No declared ASVS level; common Top 10 patterns visible (hardcoded creds, raw SQL)."),
            (1, "Top 10 awareness documented; informal review."),
            (2, "ASVS Level 1 targeted; partial pass."),
            (3, "ASVS Level 1 fully met; Level 2 partial."),
            (4, "ASVS Level 2 fully met for the application's risk profile."),
            (5, "ASVS Level 3 met; threat model reviewed quarterly."),
        ),
        framework_anchor="OWASP ASVS, OWASP Top 10",
        primary_url=f"{_OWASP_ASVS} ; {_OWASP_TOP10}",
    ),
    Criterion(
        id="D2.4",
        dimension_id="D2",
        title="Branch protection & code review enforcement",
        levels=_levels(
            (0, "Direct push to default branch allowed."),
            (1, "Default branch protected; admins can bypass."),
            (2, "Branch protection on default; required reviewers for protected branches."),
            (3, "CODEOWNERS in place; required reviewers cannot be self-approved; signed commits encouraged."),
            (4, "Above + signed commits required; rulesets enforce checks for all contributors including admins."),
            (5, "Above + required reviews from independent owners (e.g., security review for security-relevant paths)."),
        ),
        framework_anchor="OpenSSF Scorecard Branch-Protection / Code-Review",
        primary_url=_OPENSSF_SCORECARD,
    ),
    # --- D3. Supply Chain Integrity -------------------------------------------
    Criterion(
        id="D3.1",
        dimension_id="D3",
        title="SBOM availability",
        levels=_levels(
            (0, "No SBOM produced."),
            (1, "SBOM generated ad hoc, not published."),
            (2, "SBOM generated per release in CycloneDX or SPDX format; published with releases."),
            (3, "SBOM generated per build; consumable via documented URL or registry."),
            (4, "SBOM signed and verifiable; ingested by downstream consumers."),
            (5, "SBOM + VEX statements published; SBOM diffing tracked release-over-release."),
        ),
        framework_anchor="CycloneDX (ECMA-424); SPDX (ISO/IEC 5962:2021)",
        primary_url=f"{_CYCLONEDX} ; {_SPDX}",
    ),
    Criterion(
        id="D3.2",
        dimension_id="D3",
        title="Artifact signing",
        levels=_levels(
            (0, "No artifact signing."),
            (1, "Artifacts signed with long-lived keys; manual rotation."),
            (2, "Sigstore / cosign signing on releases; signatures published."),
            (3, "Sigstore keyless signing tied to OIDC identity; recorded in Rekor."),
            (4, "Signed in-toto attestations for build provenance accompany every release."),
            (5, "Above + admission control / verification policy in deployment pipeline rejects unsigned artifacts."),
        ),
        framework_anchor="Sigstore",
        primary_url=_SIGSTORE,
    ),
    Criterion(
        id="D3.3",
        dimension_id="D3",
        title="SLSA build track level",
        levels=_levels(
            (0, "SLSA L0 — builds on developer machines."),
            (1, "SLSA L1 — provenance generated, may be unsigned."),
            (2, "SLSA L1 + provenance distributed with artifacts."),
            (3, "SLSA L2 — hosted build platform (GitHub Actions, GitLab CI) signs provenance."),
            (4, "SLSA L3 — hardened build platform; tamper-resistant provenance generation."),
            (5, "SLSA L3 + reproducible builds verified by independent rebuilders."),
        ),
        framework_anchor="SLSA v1.0 build track",
        primary_url=_SLSA_LEVELS,
    ),
    Criterion(
        id="D3.4",
        dimension_id="D3",
        title="Dependency-update automation",
        levels=_levels(
            (0, "Dependencies pinned and never updated."),
            (1, "Manual updates only; no automation; updates >90 days behind."),
            (2, "Dependabot/Renovate configured for security updates only."),
            (3, "Automated updates for security and minor versions; merge automation for green builds."),
            (4, "Automated updates including major version review; renovate config versioned."),
            (5, "Above + reachability-aware prioritization; lockfile diffing reviewed in PR."),
        ),
        framework_anchor="OpenSSF Scorecard Dependency-Update-Tool",
        primary_url=_OPENSSF_SCORECARD,
    ),
    # --- D4. Delivery Performance --------------------------------------------
    Criterion(
        id="D4.1",
        dimension_id="D4",
        title="Deployment frequency",
        levels=_levels(
            (0, "<1 deploy/quarter."),
            (1, "1–4 deploys/quarter (Low)."),
            (2, "Monthly (Low/Medium boundary)."),
            (3, "Weekly (Medium)."),
            (4, "Daily (High)."),
            (5, "On-demand, multiple per day (Elite)."),
        ),
        framework_anchor="DORA Core Model",
        primary_url=_DORA_GUIDE,
    ),
    Criterion(
        id="D4.2",
        dimension_id="D4",
        title="Change lead time (commit to production)",
        levels=_levels(
            (0, ">6 months."),
            (1, "1–6 months (Low)."),
            (2, "1 week to 1 month (Medium)."),
            (3, "1 day to 1 week (High lower bound)."),
            (4, "<1 day (High)."),
            (5, "<1 hour (Elite)."),
        ),
        framework_anchor="DORA Core Model",
        primary_url=_DORA_GUIDE,
    ),
    Criterion(
        id="D4.3",
        dimension_id="D4",
        title="Change failure rate",
        levels=_levels(
            (0, ">60%."),
            (1, "30–60% (Low)."),
            (2, "16–30% (Medium)."),
            (3, "11–15% (High lower bound)."),
            (4, "5–10%."),
            (5, "0–5% (Elite)."),
        ),
        framework_anchor="DORA Core Model",
        primary_url=_DORA_GUIDE,
    ),
    Criterion(
        id="D4.4",
        dimension_id="D4",
        title="Failed-deployment recovery time",
        levels=_levels(
            (0, ">1 month."),
            (1, "1 week to 1 month (Low)."),
            (2, "1 day to 1 week (Medium)."),
            (3, "<1 day (High)."),
            (4, "<1 hour (Elite lower bound)."),
            (5, "<15 minutes (Elite)."),
        ),
        framework_anchor="DORA Core Model",
        primary_url=_DORA_GUIDE,
    ),
    # --- D5. Engineering Discipline ------------------------------------------
    Criterion(
        id="D5.1",
        dimension_id="D5",
        title="PR review depth",
        levels=_levels(
            (0, "PRs merged without review."),
            (1, "Reviews requested but often skipped or rubber-stamped."),
            (2, "Required reviewer count enforced; review depth uneven."),
            (3, "CODEOWNERS routes reviews; review comments substantive on >50% of PRs."),
            (4, "Review SLAs measured; pickup time tracked."),
            (5, "Review depth, comment density, and rework metrics tracked dimension-by-dimension."),
        ),
        framework_anchor="OpenSSF Scorecard Code-Review; SPACE Activity",
        primary_url=f"{_OPENSSF_SCORECARD} ; {_SPACE_ACM}",
    ),
    Criterion(
        id="D5.2",
        dimension_id="D5",
        title="CI health (green rate, time, flakiness)",
        levels=_levels(
            (0, "No CI or CI broken on default branch."),
            (1, "CI configured; default-branch green rate <80%."),
            (2, "Green rate 80–90%; build times >30 min."),
            (3, "Green rate >90%; build times <30 min."),
            (4, "Green rate >95%; build times <15 min; flakiness <2%."),
            (5, "Green rate >98%; build times <10 min; test impact analysis in use."),
        ),
        framework_anchor="OpenSSF Scorecard CI-Tests",
        primary_url=_OPENSSF_SCORECARD,
    ),
    Criterion(
        id="D5.3",
        dimension_id="D5",
        title="Branch hygiene",
        levels=_levels(
            (0, "Long-lived feature branches; ad hoc merges."),
            (1, "Trunk-based intent; long-lived branches still common."),
            (2, "Trunk-based with short-lived branches; some history mess."),
            (3, "Linear history enforced; squash or rebase merges only."),
            (4, "Above + conventional commits / structured commit messages."),
            (5, "Above + automated changelog generation tied to commit conventions."),
        ),
        framework_anchor="(community practice)",
        primary_url="",
    ),
    Criterion(
        id="D5.4",
        dimension_id="D5",
        title="Release cadence and tagging",
        levels=_levels(
            (0, "No releases or untagged releases."),
            (1, "Releases tagged but irregular; no notes."),
            (2, "SemVer tagging; release notes manual."),
            (3, "SemVer + automated release notes; release branches as needed."),
            (4, "Release-please / changesets / semantic-release automation."),
            (5, "Above + release attestations (SLSA provenance attached)."),
        ),
        framework_anchor="OpenSSF Scorecard Signed-Releases",
        primary_url=_OPENSSF_SCORECARD,
    ),
    # --- D6. Documentation & Transparency ------------------------------------
    Criterion(
        id="D6.1",
        dimension_id="D6",
        title="README and onboarding",
        levels=_levels(
            (0, "No README or stub README."),
            (1, "README describes purpose; setup instructions incomplete."),
            (2, "New contributor can clone and run locally within 1 hour."),
            (3, "Above + architecture overview, key abstractions documented."),
            (4, "Above + ADRs (architectural decision records) published."),
            (5, "Above + runbook for production operations + threat model summary."),
        ),
        framework_anchor="OpenSSF Best Practices Badge passing criteria",
        primary_url=_OPENSSF_BADGE,
    ),
    Criterion(
        id="D6.2",
        dimension_id="D6",
        title="License clarity",
        levels=_levels(
            (0, "No LICENSE file."),
            (1, "License declared in README only."),
            (2, "LICENSE file matches an SPDX identifier."),
            (3, "SPDX identifier in every source file or top-level declaration; third-party licenses tracked."),
            (4, "Above + license-compatibility CI check; SBOM includes license fields."),
            (5, "Above + Developer Certificate of Origin or CLA enforced; license attestation per release."),
        ),
        framework_anchor="OpenSSF Scorecard License; SPDX",
        primary_url=f"{_OPENSSF_SCORECARD} ; {_SPDX}",
    ),
    Criterion(
        id="D6.3",
        dimension_id="D6",
        title="Security policy & disclosure",
        levels=_levels(
            (0, "No SECURITY.md."),
            (1, "SECURITY.md present but vague."),
            (2, "SECURITY.md names a contact; vulnerability disclosure process defined."),
            (3, "Above + named SLA for triage and disclosure."),
            (4, "Above + CVE-numbering authority assignment or coordinated-disclosure agreement."),
            (5, "Above + bug bounty or VDP program with public scope and history."),
        ),
        framework_anchor="OpenSSF Scorecard Security-Policy",
        primary_url=_OPENSSF_SCORECARD,
    ),
    Criterion(
        id="D6.4",
        dimension_id="D6",
        title="Contribution guidance & governance",
        levels=_levels(
            (0, "No CONTRIBUTING.md, no governance."),
            (1, "CONTRIBUTING.md present."),
            (2, "Above + Code of Conduct."),
            (3, "Above + GOVERNANCE.md or named maintainers; review SLAs published."),
            (4, "Above + roadmap or release planning visible."),
            (5, "Above + open governance with public meetings or recorded decisions."),
        ),
        framework_anchor="OpenSSF Best Practices Badge",
        primary_url=_OPENSSF_BADGE,
    ),
    # --- D7. Sustainability & Team Health ------------------------------------
    Criterion(
        id="D7.1",
        dimension_id="D7",
        title="Bus factor / knowledge concentration",
        levels=_levels(
            (0, "Single contributor authored >80% of code; no co-maintainers."),
            (1, "2 contributors share most work; high concentration in critical paths."),
            (2, "3+ active contributors; some critical paths still single-owner."),
            (3, "5+ active contributors; CODEOWNERS includes ≥2 reviewers per critical path."),
            (4, "Above + onboarding pipeline producing new committers annually."),
            (5, "Above + governance prevents single-point-of-failure ownership at any layer."),
        ),
        framework_anchor="(community practice; CodeScene-style hotspot)",
        primary_url="",
    ),
    Criterion(
        id="D7.2",
        dimension_id="D7",
        title="Activity (sustained, not spiky)",
        levels=_levels(
            (0, "No commits in 6+ months."),
            (1, "Commits clustered; long quiet periods."),
            (2, "Commits roughly weekly."),
            (3, "Commits multiple times per week with trailing-90-day stability."),
            (4, "Sustained 12-month activity; no >2-week quiet windows."),
            (5, "Sustained activity with diverse contributor base across geographies/orgs."),
        ),
        framework_anchor="OpenSSF Scorecard Maintained",
        primary_url=_OPENSSF_SCORECARD,
    ),
    Criterion(
        id="D7.3",
        dimension_id="D7",
        title="Issue and PR responsiveness",
        levels=_levels(
            (0, "Issues / PRs accumulate untriaged for months."),
            (1, "Median triage time >7 days."),
            (2, "Median triage time 2–7 days."),
            (3, "Median triage time <48 hours; PR pickup time <24 hours."),
            (4, "Median PR cycle time <3 days; abandonment rate <10%."),
            (5, "Above + responsiveness tracked as an explicit team metric."),
        ),
        framework_anchor="SPACE Performance dimension",
        primary_url=_SPACE_ACM,
    ),
    Criterion(
        id="D7.4",
        dimension_id="D7",
        title="Maintainer continuity",
        levels=_levels(
            (0, "Original creator inactive; no successor."),
            (1, "Original creator only active maintainer; no succession plan."),
            (2, "≥2 active maintainers; succession informal."),
            (3, "≥2 active maintainers; written succession or sponsorship."),
            (4, "Project sponsored by foundation or company with continuity commitment."),
            (5, "Above + governance with rotation, term limits, or independent steering committee."),
        ),
        framework_anchor="(community practice)",
        primary_url="",
    ),
    # --- D8. Compliance & Governance Posture (org-scoped) --------------------
    Criterion(
        id="D8.1",
        dimension_id="D8",
        title="Secure SDLC framework conformance (NIST SSDF / OWASP SAMM)",
        levels=_levels(
            (0, "No documented secure SDLC."),
            (1, "Practices exist informally."),
            (2, "NIST SSDF or SAMM gap assessment completed; remediation plan in progress."),
            (3, "SSDF attestation submitted (per EO 14028) or SAMM Level 1 met across practices."),
            (4, "SAMM Level 2 met across practices; or BSIMM benchmarking completed."),
            (5, "SAMM Level 3 in target practices; continuous improvement evidence."),
        ),
        framework_anchor="NIST SSDF; OWASP SAMM",
        primary_url=f"{_NIST_SSDF} ; {_OWASP_SAMM}",
    ),
    Criterion(
        id="D8.2",
        dimension_id="D8",
        title="Audit attestation (ISO 27001 / SOC 2)",
        levels=_levels(
            (0, "No audits."),
            (1, "Internal audit only."),
            (2, "SOC 2 Type I or ISO 27001 readiness assessment completed."),
            (3, "SOC 2 Type II or ISO 27001 certification covering current period."),
            (4, "Both SOC 2 Type II and ISO 27001:2022 in good standing."),
            (5, "Above + alignment to NIST CSF 2.0 with annual reassessment."),
        ),
        framework_anchor="ISO/IEC 27001:2022; AICPA SOC 2",
        primary_url=f"{_ISO_27001} ; {_AICPA_SOC2}",
    ),
    Criterion(
        id="D8.3",
        dimension_id="D8",
        title="Sectoral regulatory conformance (when applicable)",
        levels=_levels(
            (0, "Required attestation absent or expired."),
            (1, "Gap assessment underway."),
            (2, "Initial attestation in progress."),
            (3, "Current attestation valid (HIPAA, PCI DSS, FedRAMP, CMMC, FDA SaMD, EU AI Act high-risk conformity, etc.)."),
            (4, "Current attestation + automated continuous-monitoring evidence."),
            (5, "Above + cross-framework mapping (e.g., CSA CAIQ used to satisfy multiple)."),
        ),
        framework_anchor="EU AI Act; HIPAA; PCI DSS; FedRAMP; CMMC; FDA SaMD",
        primary_url=(
            "https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng ; "
            "https://www.hhs.gov/hipaa/for-professionals/security/index.html ; "
            "https://www.pcisecuritystandards.org/ ; "
            "https://www.fedramp.gov/ ; "
            "https://dodcio.defense.gov/CMMC/ ; "
            "https://www.fda.gov/medical-devices/digital-health-center-excellence/cybersecurity"
        ),
    ),
    Criterion(
        id="D8.4",
        dimension_id="D8",
        title="Vendor-risk readiness",
        levels=_levels(
            (0, "No standardized vendor questionnaire response."),
            (1, "Ad hoc questionnaire responses."),
            (2, "CSA CAIQ-Lite completed."),
            (3, "CSA CAIQ v4 completed and posted to STAR Registry (or equivalent)."),
            (4, "Above + Trust Center page with downloadable evidence."),
            (5, "Above + automated trust-portal updates from underlying control state."),
        ),
        framework_anchor="CSA CAIQ v4",
        primary_url=_CSA_CAIQ,
    ),
)


# ---------------------------------------------------------------------------
# Index helpers
# ---------------------------------------------------------------------------


def criterion_by_id(criterion_id: str) -> Criterion:
    """Look up a criterion by its RSF id (e.g., ``D2.3``)."""
    for c in RSF_CRITERIA:
        if c.id == criterion_id:
            return c
    raise KeyError(f"unknown RSF criterion: {criterion_id!r}")


def dimension_by_id(dimension_id: str) -> Dimension:
    """Look up a dimension by id (e.g., ``D2``)."""
    for d in RSF_DIMENSIONS:
        if d.id == dimension_id:
            return d
    raise KeyError(f"unknown RSF dimension: {dimension_id!r}")


def criteria_for_dimension(dimension_id: str) -> tuple[Criterion, ...]:
    """All criteria belonging to a given dimension, in spec order."""
    return tuple(c for c in RSF_CRITERIA if c.dimension_id == dimension_id)


__all__ = [
    "Criterion",
    "CriterionLevel",
    "Dimension",
    "RSF_CRITERIA",
    "RSF_DIMENSIONS",
    "RSF_VERSION",
    "criteria_for_dimension",
    "criterion_by_id",
    "dimension_by_id",
]
