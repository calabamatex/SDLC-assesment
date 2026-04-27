"""Per-persona, per-criterion translation map for RSF top-5 findings.

The persona report layer translates each top-5 RSF sub-criterion into
the reader's lens. A VC reads investment language; an acquisition
reviewer reads liability / integration cost; an engineering lead reads
sprint allocation; a remediation agent reads imperative-task language.

This module is the data layer for that translation. Every entry carries:

- ``consequence``: what the finding *means* in this persona's frame
  (1–2 sentences). Persona-distinct prose.
- ``action``: what this persona should DO about it (1–2 sentences).
  Persona-distinct prose.
- ``framework_ref``: published-framework reference per RSF §11. Same
  across personas because the framework anchor is the same; this is the
  audit trail that proves the consequence isn't invented — the reader
  can follow the reference back to the published spec.

Coverage: the criteria most likely to fire in real assessments based on
the current detector pipeline (D2.2, D2.3, D3.1, D3.2, D3.4, D5.4,
D6.1–D6.4, D7.1, D7.2, D7.4). Criteria not in the map fall back to a
generic translation built from the criterion's title + level anchor.

Per RSF discipline: this module **does not invent threshold values**.
Every numeric reference (e.g., "GDPR Article 32") is a citation to the
published framework, not a value the assessor scored against.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PersonaTranslation:
    """One persona-specific consequence + action for a single RSF criterion."""

    consequence: str
    action: str
    framework_ref: str


# Criterion IDs in this map use the RSF v1.0 identifier scheme (D<dim>.<sub>).
# Persona keys use the legacy use_case names (which determine which builder
# runs); the RSF persona-weight matrix is applied separately in the RSF
# block, not here.

_TRANSLATIONS: dict[str, dict[str, PersonaTranslation]] = {
    # =====================================================================
    # D2.2 — Secrets in source / git history
    # =====================================================================
    "D2.2": {
        "vc_diligence": PersonaTranslation(
            consequence=(
                "Active credentials in source code is a pre-term-sheet "
                "founder Q&A item — it punctures the engineering-rigor "
                "claim and surfaces customer-trust exposure before "
                "investment lands."
            ),
            action=(
                "Tranche the round against milestone closure: tranche-1 "
                "gated on rotation + scanning hookup. Add to the founder "
                "follow-up list before term-sheet."
            ),
            framework_ref=(
                "OWASP ASVS V2.10 (Authentication / Service Authentication); "
                "NIST SSDF PS.5 (Archive and Protect Software)"
            ),
        ),
        "acquisition_diligence": PersonaTranslation(
            consequence=(
                "Inherited credential exposure on close. Carries direct "
                "GDPR Article 32 / CCPA personal-info-safeguard liability "
                "if any leaked credential reached customer data."
            ),
            action=(
                "Escrow condition: seller rotates credentials + installs "
                "secret-scanning before close, OR holdback covers the "
                "rotation + breach-notification cost."
            ),
            framework_ref=(
                "OWASP ASVS V2; NIST SSDF PS.5; GDPR Art. 32 / CCPA §1798.150"
            ),
        ),
        "engineering_triage": PersonaTranslation(
            consequence=(
                "Phase-1 must-ship. Live credentials in source equal a "
                "page-someone-tonight risk if any of them touch production."
            ),
            action=(
                "This sprint: rotate every detected credential; install "
                "gitleaks pre-commit hook; add `.github/secret_scanning.yml`; "
                "purge git history with `git filter-repo --invert-paths`."
            ),
            framework_ref=(
                "OWASP ASVS V2; NIST SSDF PS.5; OpenSSF Scorecard "
                "Secret-Scanning probe"
            ),
        ),
        "remediation_agent": PersonaTranslation(
            consequence=(
                "Phase-1 task — blocks all later phases. Credential exposure "
                "must close before any downstream task advances."
            ),
            action=(
                "Task: rotate exposed credentials; verify with `git grep -nE "
                "'AKIA|sk_live|ghp_'`; idempotency check returns zero before "
                "advancing the task pointer."
            ),
            framework_ref=(
                "OWASP ASVS V2; NIST SSDF RV.1 (Identify and Confirm "
                "Vulnerabilities)"
            ),
        ),
    },
    # =====================================================================
    # D2.3 — ASVS / Top 10 conformance (Top-10 patterns visible)
    # =====================================================================
    "D2.3": {
        "vc_diligence": PersonaTranslation(
            consequence=(
                "Common OWASP Top 10 patterns in production code "
                "(hardcoded creds, raw SQL, shell-out) signal demo-grade "
                "engineering, not a Series A-ready security posture."
            ),
            action=(
                "Founder Q&A: ask for ASVS Level 1 self-assessment and "
                "remediation timeline. Apply valuation discount or stage "
                "investment against ASVS Level 1 attestation milestone."
            ),
            framework_ref="OWASP Top 10 (2021); OWASP ASVS Level 1",
        ),
        "acquisition_diligence": PersonaTranslation(
            consequence=(
                "Top 10 patterns in inherited code translate directly to "
                "post-close engineering cost — every flagged pattern is an "
                "incident waiting to happen on your customer base."
            ),
            action=(
                "Pre-close: require seller to either remediate or document "
                "each pattern with a known-acceptable risk justification. "
                "Post-close: ASVS Level 1 attestation should be a 90-day "
                "integration milestone."
            ),
            framework_ref="OWASP Top 10 (2021); OWASP ASVS Level 1",
        ),
        "engineering_triage": PersonaTranslation(
            consequence=(
                "Top 10 patterns in production code are open-and-shut "
                "engineering debts. Each one is a potential incident; "
                "concentration of patterns indicates a pattern-blind "
                "review process upstream."
            ),
            action=(
                "Add Semgrep / Bandit / ESLint rule packs targeting the "
                "specific Top 10 categories detected. Block CI on new "
                "violations of the same rule. Pay down existing in priority "
                "order: command injection > SQL injection > hardcoded creds."
            ),
            framework_ref=(
                "OWASP Top 10 (2021); CWE Top 25; OpenSSF Scorecard SAST probe"
            ),
        ),
        "remediation_agent": PersonaTranslation(
            consequence=(
                "Each detected pattern is a discrete remediation task with "
                "a CWE-classified severity. Sequence by CWE rank: CWE-78 "
                "(OS command injection) > CWE-89 (SQL injection) > CWE-798 "
                "(hardcoded credentials)."
            ),
            action=(
                "For each detected pattern: open a remediation task tagged "
                "with its CWE ID; verification command is the corresponding "
                "Semgrep / Bandit rule; idempotency check is `semgrep "
                "--config p/owasp-top-10` returning zero matches for that "
                "rule."
            ),
            framework_ref="OWASP Top 10 (2021); CWE Top 25; OWASP ASVS",
        ),
    },
    # =====================================================================
    # D3.1 — SBOM availability
    # =====================================================================
    "D3.1": {
        "vc_diligence": PersonaTranslation(
            consequence=(
                "No SBOM = no enterprise sales pipeline into regulated "
                "verticals (federal per EO 14028, FedRAMP, FDA SaMD, EU AI "
                "Act high-risk). Caps the addressable market."
            ),
            action=(
                "Add SBOM generation as a Series-A milestone; investors "
                "should treat its absence as a TAM-limit signal. Founder "
                "Q&A: customer-pipeline gating on supply-chain attestation."
            ),
            framework_ref=(
                "EO 14028 §4(e); CycloneDX (ECMA-424); SPDX (ISO/IEC 5962:2021)"
            ),
        ),
        "acquisition_diligence": PersonaTranslation(
            consequence=(
                "No SBOM = no ready answer to enterprise vendor "
                "questionnaires (CSA CAIQ, Trust Center). Acquirer inherits "
                "the disclosure burden plus the procurement-cycle cost it "
                "implies."
            ),
            action=(
                "Day-30 integration item: stand up `syft` in the seller's "
                "release pipeline; backfill SBOMs for the last N releases. "
                "Cost: ~1 engineer-week for setup."
            ),
            framework_ref=(
                "CycloneDX (ECMA-424); SPDX (ISO/IEC 5962:2021); CSA CAIQ v4"
            ),
        ),
        "engineering_triage": PersonaTranslation(
            consequence=(
                "Missing SBOM is a one-day fix that unblocks "
                "supply-chain-aware customers. Every release without one "
                "is a missed compliance signal."
            ),
            action=(
                "Add `syft packages dir:. -o cyclonedx-json=sbom.json` to "
                "the release workflow. Publish alongside artifacts. Sign "
                "with cosign for level-4 of D3.1."
            ),
            framework_ref=(
                "CycloneDX (ECMA-424); SPDX (ISO/IEC 5962:2021); OpenSSF "
                "Scorecard SBOM probe"
            ),
        ),
        "remediation_agent": PersonaTranslation(
            consequence=(
                "Concrete deliverable. Single workflow change; verifiable "
                "post-merge via release-asset inspection."
            ),
            action=(
                "Task: install `anchore/sbom-action@v0` in `.github/"
                "workflows/release.yml`; output `sbom.cdx.json` as a "
                "release asset. Verification: `gh release view <tag> --json "
                "assets | jq '.assets[].name' | grep -i sbom`."
            ),
            framework_ref="CycloneDX; SPDX; SLSA v1.0 build track",
        ),
    },
    # =====================================================================
    # D3.2 — Artifact signing
    # =====================================================================
    "D3.2": {
        "vc_diligence": PersonaTranslation(
            consequence=(
                "Unsigned releases close out the federal / regulated-customer "
                "channel post EO 14028. Investors should treat this as a "
                "go-to-market constraint, not a hygiene issue."
            ),
            action=(
                "Add Sigstore keyless signing as a fundable milestone. "
                "Pair with founder commitment on customer-pipeline timing "
                "into regulated verticals."
            ),
            framework_ref=(
                "Sigstore + cosign; in-toto attestation framework; EO 14028"
            ),
        ),
        "acquisition_diligence": PersonaTranslation(
            consequence=(
                "Lack of signing closes regulated-buyer doors that the "
                "acquirer's existing channel may already have open. "
                "Integration friction is opportunity-cost for cross-sell."
            ),
            action=(
                "Day-30: adopt Sigstore keyless signing for all release "
                "artifacts. Tie to the acquirer's existing CI provenance "
                "policy."
            ),
            framework_ref="Sigstore; in-toto; EO 14028",
        ),
        "engineering_triage": PersonaTranslation(
            consequence=(
                "Unsigned artifacts mean any compromised CI step or "
                "downstream registry can publish without detection. "
                "Detection-and-recovery cost on a real incident is days, "
                "not hours."
            ),
            action=(
                "Add `cosign sign-blob` to the release workflow with OIDC "
                "keyless signing. Publish signatures to Rekor. Add "
                "verification step in deployment pipeline."
            ),
            framework_ref="Sigstore (cosign); Rekor transparency log",
        ),
        "remediation_agent": PersonaTranslation(
            consequence=(
                "Add a signing step to the release workflow. Verify with "
                "`cosign verify-blob` against the published signature."
            ),
            action=(
                "Task: add `sigstore/cosign-installer@v3` + `cosign "
                "sign-blob --yes <artifact>` to `.github/workflows/"
                "release.yml`. Verification: `cosign verify-blob "
                "--certificate <cert> --signature <sig> <artifact>` "
                "exits 0."
            ),
            framework_ref="Sigstore; cosign; SLSA L2",
        ),
    },
    # =====================================================================
    # D3.4 — Dependency-update automation
    # =====================================================================
    "D3.4": {
        "vc_diligence": PersonaTranslation(
            consequence=(
                "Manual dependency updates indicate engineering toil "
                "absorbing time that should go to product velocity. "
                "Long-term predictor of feature-shipping cadence under "
                "scale."
            ),
            action=(
                "Founder follow-up: ask about Dependabot adoption + how "
                "the team will maintain dep currency at 10× scale. Tie to "
                "engineering-headcount projection in the plan."
            ),
            framework_ref="OpenSSF Scorecard Dependency-Update-Tool probe",
        ),
        "acquisition_diligence": PersonaTranslation(
            consequence=(
                "Manual updates = inherited maintenance toil. Compounds "
                "post-close with every CVE that doesn't auto-PR — adds "
                "engineer-hours that scale linearly with dep count."
            ),
            action=(
                "Day-30: enable Dependabot security + version updates "
                "across all repos. Cost: ~1 engineer-day per repo for "
                "config + initial PR triage."
            ),
            framework_ref="OpenSSF Scorecard Dependency-Update-Tool",
        ),
        "engineering_triage": PersonaTranslation(
            consequence=(
                "Manual dep updates is engineer-time-tax that scales with "
                "dependency count. Quiet failure mode: deps drift past "
                "EOL, security backports stop arriving."
            ),
            action=(
                "This sprint: enable `.github/dependabot.yml` covering all "
                "package ecosystems; configure weekly schedule; set up "
                "auto-merge for green minor + patch updates."
            ),
            framework_ref="OpenSSF Scorecard Dependency-Update-Tool",
        ),
        "remediation_agent": PersonaTranslation(
            consequence=(
                "Single config-file addition; high leverage; low risk."
            ),
            action=(
                "Task: create `.github/dependabot.yml` enabling all "
                "ecosystems (pip / npm / cargo / etc. as detected in "
                "lockfiles). Verification: `cat .github/dependabot.yml | "
                "yq '.updates | length'` returns ≥1."
            ),
            framework_ref="OpenSSF Scorecard Dependency-Update-Tool",
        ),
    },
    # =====================================================================
    # D5.4 — Release cadence and tagging
    # =====================================================================
    "D5.4": {
        "vc_diligence": PersonaTranslation(
            consequence=(
                "Irregular releases without automation suggest the team "
                "ships from main rather than from controlled cuts. Tracks "
                "with low-DORA-tier delivery performance — a Series A risk "
                "factor."
            ),
            action=(
                "Founder Q&A: deployment-frequency baseline + plan for "
                "release-please / semantic-release adoption. Use as a "
                "DORA-credibility signal."
            ),
            framework_ref=(
                "DORA Core Model; OpenSSF Scorecard Signed-Releases probe"
            ),
        ),
        "acquisition_diligence": PersonaTranslation(
            consequence=(
                "Without release automation, every customer-side release "
                "note + change-summary is manual labor. Acquirer inherits "
                "that toil unless tooling is added pre-close."
            ),
            action=(
                "Day-60: adopt release-please or semantic-release; tie to "
                "the acquirer's release-engineering standard. Cost: ~1 "
                "engineer-week including audit of existing tag history."
            ),
            framework_ref="DORA; OpenSSF Scorecard Signed-Releases",
        ),
        "engineering_triage": PersonaTranslation(
            consequence=(
                "No release automation means every release is a "
                "human-authored event. Quality varies; release notes drift; "
                "downstream integration tests are slower to identify "
                "regressions to specific cuts."
            ),
            action=(
                "Adopt release-please (`googleapis/release-please-action@v4`) "
                "for SemVer-compliant tagging + automated CHANGELOG + "
                "release-PR workflow. Pair with Conventional Commits."
            ),
            framework_ref="DORA Core Model; OpenSSF Scorecard",
        ),
        "remediation_agent": PersonaTranslation(
            consequence=(
                "Single workflow addition; standard pattern; high adoption "
                "rate in the OSS community."
            ),
            action=(
                "Task: add `googleapis/release-please-action@v4` to "
                "`.github/workflows/release.yml`. Verification: subsequent "
                "Conventional-Commit merge to main produces a release-PR; "
                "merging that PR cuts a tag."
            ),
            framework_ref=(
                "DORA Core Model; semantic-release / release-please "
                "convention; SLSA v1.0 build track"
            ),
        ),
    },
    # =====================================================================
    # D6.1 — README and onboarding
    # =====================================================================
    "D6.1": {
        "vc_diligence": PersonaTranslation(
            consequence=(
                "Stub README signals founder under-investment in "
                "external-facing documentation. Predictor of customer-"
                "support burden as the team scales."
            ),
            action=(
                "Low-cost remediation; founder ask. If the README is "
                "stub-grade across multiple repos, that's a culture signal "
                "to weigh in execution-maturity rating."
            ),
            framework_ref="OpenSSF Best Practices Badge — passing criteria",
        ),
        "acquisition_diligence": PersonaTranslation(
            consequence=(
                "Stub README means longer onboarding for the acquirer's "
                "engineers post-close. Direct cost: ~2 engineer-weeks of "
                "tribal-knowledge transfer per integrated module."
            ),
            action=(
                "Pre-close: seller commits to producing a README that lets "
                "a new engineer clone, build, run, and test within 1 hour. "
                "Verify on intake."
            ),
            framework_ref="OpenSSF Best Practices Badge",
        ),
        "engineering_triage": PersonaTranslation(
            consequence=(
                "Onboarding tax. New hires pay it; cross-team contributors "
                "pay it; the lead pays it whenever they answer a "
                "what-is-this question in Slack."
            ),
            action=(
                "This sprint: README must answer: what is this, why does "
                "it exist, how do I run it, how do I test it, how do I "
                "deploy it. Add ADRs for non-obvious architecture choices."
            ),
            framework_ref="OpenSSF Best Practices Badge passing/silver",
        ),
        "remediation_agent": PersonaTranslation(
            consequence=(
                "README is content that needs human authoring. Agent can "
                "scaffold; human reviews."
            ),
            action=(
                "Task: scaffold a README from inventory + `pyproject.toml` "
                "/ `package.json`; mark TODO sections for human prose; "
                "open a PR for review. Do not merge without human approval."
            ),
            framework_ref="OpenSSF Best Practices Badge",
        ),
    },
    # =====================================================================
    # D6.2 — License clarity
    # =====================================================================
    "D6.2": {
        "vc_diligence": PersonaTranslation(
            consequence=(
                "Missing or unclear LICENSE is a deal-blocker for "
                "commercial customers + a legal-review tax in any "
                "downstream M&A. Cheap to fix, costly to ignore."
            ),
            action=(
                "Founder ask: confirm LICENSE choice + ensure SPDX "
                "identifier is set. Tie to the customer-contract redline "
                "review pipeline if the company has any enterprise sales."
            ),
            framework_ref=(
                "OpenSSF Scorecard License probe; SPDX; OpenChain "
                "(ISO/IEC 5230)"
            ),
        ),
        "acquisition_diligence": PersonaTranslation(
            consequence=(
                "License clarity is a baseline acquisition diligence item. "
                "Missing LICENSE blocks contribution-of-IP at close + "
                "creates downstream redistribution exposure if any "
                "third-party deps have copyleft terms."
            ),
            action=(
                "Pre-close: SPDX identifier present in LICENSE + "
                "package metadata. License-compatibility audit against "
                "third-party deps. Required for IP transfer."
            ),
            framework_ref="OpenChain (ISO/IEC 5230); SPDX",
        ),
        "engineering_triage": PersonaTranslation(
            consequence=(
                "If LICENSE is missing or non-SPDX, all-rights-reserved is "
                "the default — nobody can use the code legally. Most "
                "internal teams overlook this until customer contracts "
                "surface it."
            ),
            action=(
                "Add LICENSE with SPDX identifier (e.g., `MIT` / `Apache-2.0`). "
                "Add `SPDX-License-Identifier` headers to all source files. "
                "Add `[tool.setuptools] license-files` for distribution."
            ),
            framework_ref="SPDX; OpenSSF Scorecard License probe",
        ),
        "remediation_agent": PersonaTranslation(
            consequence=(
                "License choice requires human judgment; agent can scaffold "
                "the LICENSE file once a license is named."
            ),
            action=(
                "Task: ask user for license preference; once provided, "
                "create LICENSE file from SPDX template; add "
                "`SPDX-License-Identifier` headers to source files. "
                "Verification: `licensee detect` returns a recognized "
                "license."
            ),
            framework_ref="SPDX; ISO/IEC 5230 OpenChain",
        ),
    },
    # =====================================================================
    # D6.3 — Security policy & disclosure
    # =====================================================================
    "D6.3": {
        "vc_diligence": PersonaTranslation(
            consequence=(
                "Vague or missing SECURITY.md signals lack of vulnerability-"
                "response maturity. Translates to longer mean-time-to-"
                "disclosure when a real vuln lands — affects both customer "
                "retention and any responsible-disclosure researcher "
                "interactions."
            ),
            action=(
                "Founder ask: vulnerability-response process + named contact "
                "+ disclosure SLA. Tie to enterprise-customer security "
                "questionnaire readiness."
            ),
            framework_ref="OpenSSF Scorecard Security-Policy probe",
        ),
        "acquisition_diligence": PersonaTranslation(
            consequence=(
                "Missing SECURITY.md is a vendor-questionnaire failure. "
                "Customers + auditors expect to see a published disclosure "
                "process and SLA — its absence raises diligence-cost "
                "downstream."
            ),
            action=(
                "Pre-close: named contact + disclosure process documented. "
                "Tie SLA to the acquirer's existing vuln-response SLA."
            ),
            framework_ref=(
                "OpenSSF Scorecard Security-Policy; ISO 27001 A.5.5 / A.5.7"
            ),
        ),
        "engineering_triage": PersonaTranslation(
            consequence=(
                "Without a published policy, security researchers will "
                "report vulns through random channels (or publish them). "
                "The team owns the variance."
            ),
            action=(
                "SECURITY.md must include: contact (security@... or "
                "GitHub security advisories), disclosure timeline (e.g., "
                "90-day default), supported versions, scope. Pair with "
                "GitHub Private Vulnerability Reporting."
            ),
            framework_ref=(
                "OpenSSF Scorecard Security-Policy; ISO 29147 (vulnerability "
                "disclosure)"
            ),
        ),
        "remediation_agent": PersonaTranslation(
            consequence=(
                "SECURITY.md is template-able; agent can scaffold from a "
                "standard template."
            ),
            action=(
                "Task: create SECURITY.md from a published template "
                "(disroot.org / GitHub). Include contact, supported "
                "versions, disclosure timeline. Verification: file present "
                "+ contains `@` + `report` + `disclosure` keywords."
            ),
            framework_ref="ISO 29147; OpenSSF Scorecard",
        ),
    },
    # =====================================================================
    # D6.4 — Contribution guidance & governance
    # =====================================================================
    "D6.4": {
        "vc_diligence": PersonaTranslation(
            consequence=(
                "Just a CONTRIBUTING.md without governance signals a "
                "founder-first model. May be fine for early-stage; becomes "
                "a hire-and-scale risk as team grows beyond ~10 engineers."
            ),
            action=(
                "Diligence question: governance plan as team scales. Tie "
                "to the hire-pipeline portion of the deck."
            ),
            framework_ref=(
                "OpenSSF Best Practices Badge — silver/gold criteria"
            ),
        ),
        "acquisition_diligence": PersonaTranslation(
            consequence=(
                "Lack of governance = post-close decision-rights ambiguity. "
                "Who approves architectural changes? Who triages issues? "
                "Without GOVERNANCE.md, the acquirer creates that doc."
            ),
            action=(
                "Day-30: produce GOVERNANCE.md identifying maintainers, "
                "approval flow, RFC process. Align with acquirer's "
                "engineering org structure."
            ),
            framework_ref="OpenSSF Best Practices Badge — silver",
        ),
        "engineering_triage": PersonaTranslation(
            consequence=(
                "CONTRIBUTING.md alone tells contributors HOW to submit; "
                "GOVERNANCE.md tells them WHO decides. Without the latter, "
                "PRs from outside the core team stall in review."
            ),
            action=(
                "Add CODE_OF_CONDUCT.md (Contributor Covenant) + "
                "GOVERNANCE.md naming maintainers + decision process. Add "
                "RFC template for non-trivial changes."
            ),
            framework_ref="OpenSSF Best Practices Badge",
        ),
        "remediation_agent": PersonaTranslation(
            consequence=(
                "Templated docs; scaffolding only — content requires human "
                "decisions about decision-rights."
            ),
            action=(
                "Task: scaffold CODE_OF_CONDUCT.md from Contributor Covenant; "
                "scaffold GOVERNANCE.md skeleton with TODO sections for "
                "human decisions (named maintainers, approval flow, RFC "
                "process). Open PR; do not merge without human approval."
            ),
            framework_ref="OpenSSF Best Practices Badge",
        ),
    },
    # =====================================================================
    # D7.1 — Bus factor / knowledge concentration
    # =====================================================================
    "D7.1": {
        "vc_diligence": PersonaTranslation(
            consequence=(
                "High knowledge concentration is a key-person dependency. "
                "Common at seed; concerning at Series A and later. Tracks "
                "with execution-risk + valuation discount."
            ),
            action=(
                "Diligence ask: hire-and-onboarding plan; key-person "
                "insurance discussion; CODEOWNERS adoption. Tie to "
                "post-funding hire-pipeline."
            ),
            framework_ref="CodeScene-style hotspot analysis (community)",
        ),
        "acquisition_diligence": PersonaTranslation(
            consequence=(
                "Knowledge concentration is an inherited risk: if the lead "
                "author leaves post-close, productivity collapses. Direct "
                "cost: 6–12 months of slower velocity."
            ),
            action=(
                "Pre-close: key-employee retention package (typically 18–24 "
                "month vesting). Day-30: pair-programming + CODEOWNERS "
                "adoption forcing dual-review on critical paths."
            ),
            framework_ref="CodeScene; community-practice succession-planning",
        ),
        "engineering_triage": PersonaTranslation(
            consequence=(
                "Bus factor of 1 means one person hit by a bus stops the "
                "project. Known critical-paths-with-single-owner are "
                "tomorrow's emergency."
            ),
            action=(
                "Adopt CODEOWNERS requiring two reviewers on any path "
                "owned by a single contributor. Pair-programming sessions "
                "for tribal-knowledge transfer. Onboarding doc for each "
                "critical module."
            ),
            framework_ref=(
                "CodeScene hotspot analysis; OpenSSF Scorecard Code-Review"
            ),
        ),
        "remediation_agent": PersonaTranslation(
            consequence=(
                "Not directly actionable by the agent — requires human "
                "decisions about ownership."
            ),
            action=(
                "Flag for human review: list paths with single primary "
                "author > 80% share. Suggest CODEOWNERS additions; do not "
                "merge unilaterally."
            ),
            framework_ref="CodeScene; OpenSSF Scorecard",
        ),
    },
    # =====================================================================
    # D7.2 — Activity (sustained, not spiky)
    # =====================================================================
    "D7.2": {
        "vc_diligence": PersonaTranslation(
            consequence=(
                "Sustained activity is a positive credibility signal — "
                "founder is shipping, not pitching. Spiky activity (e.g., "
                "burst before fundraise, then quiet) is a yellow flag."
            ),
            action=(
                "Cross-check the activity pattern against the fundraise "
                "narrative. Sustained = thesis credibility ↑; spiky around "
                "fundraises = founder-time-allocation question."
            ),
            framework_ref="OpenSSF Scorecard Maintained probe",
        ),
        "acquisition_diligence": PersonaTranslation(
            consequence=(
                "Activity cadence indicates whether the asset is alive or "
                "abandoned. Quiet repos pre-acquisition often re-quiet "
                "post-acquisition unless retention packages bind the team."
            ),
            action=(
                "Ask the seller to commit to a 12-month maintenance window "
                "via earn-out or retention package; assess whether the team "
                "is actually still engaged."
            ),
            framework_ref="OpenSSF Scorecard Maintained",
        ),
        "engineering_triage": PersonaTranslation(
            consequence=(
                "Sustained activity tracks with healthy iteration. Spiky "
                "activity (release-then-quiet) indicates either "
                "abandonment OR over-reliance on a single push, both bad."
            ),
            action=(
                "Set up status-page-style commit-cadence dashboard; flag "
                "any > 2-week quiet window for review."
            ),
            framework_ref="OpenSSF Scorecard Maintained; SPACE Activity",
        ),
        "remediation_agent": PersonaTranslation(
            consequence=(
                "Activity is observed, not actioned. No agent task here."
            ),
            action=(
                "No-op for the agent. Surface the cadence metric to "
                "human reviewers."
            ),
            framework_ref="OpenSSF Scorecard Maintained",
        ),
    },
    # =====================================================================
    # D7.4 — Maintainer continuity
    # =====================================================================
    "D7.4": {
        "vc_diligence": PersonaTranslation(
            consequence=(
                "No documented succession = founder-flight risk. Material "
                "issue at any stage; especially material at Series A+ when "
                "the team is supposed to be a moat."
            ),
            action=(
                "Diligence ask: succession plan + named co-maintainers. "
                "Tie to founder-equity vesting structure."
            ),
            framework_ref="Community practice; OpenSSF Best Practices Badge",
        ),
        "acquisition_diligence": PersonaTranslation(
            consequence=(
                "Founder-only maintainership creates inheritance risk. "
                "Without succession, maintenance falls to the acquirer "
                "from day one — an unbudgeted line item."
            ),
            action=(
                "Pre-close: identify co-maintainers + binding retention. "
                "Day-30: GOVERNANCE.md with named maintainers + decision "
                "rights."
            ),
            framework_ref="Community practice; ISO 27001 A.5.2 (Information "
                "security roles and responsibilities)",
        ),
        "engineering_triage": PersonaTranslation(
            consequence=(
                "Single-maintainer projects die when the maintainer leaves. "
                "If the asset matters, succession is a Q-this-quarter item."
            ),
            action=(
                "Identify a co-maintainer; document succession in "
                "GOVERNANCE.md; introduce both to the on-call rotation. "
                "Foundation sponsorship (CNCF / Apache / etc.) is the "
                "long-term answer for OSS."
            ),
            framework_ref="OpenSSF Best Practices Badge",
        ),
        "remediation_agent": PersonaTranslation(
            consequence=(
                "Requires human decisions about succession — not "
                "agent-actionable."
            ),
            action=(
                "Flag for human review: surface single-maintainer warning + "
                "links to common foundation-sponsorship guides (CNCF, "
                "Apache Incubator, OpenSSF)."
            ),
            framework_ref="OpenSSF Best Practices Badge",
        ),
    },
}


def translation_for(criterion_id: str, use_case: str) -> PersonaTranslation | None:
    """Return the persona translation for ``(criterion_id, use_case)`` if known.

    ``criterion_id`` uses the RSF v1.0 identifier scheme (e.g. ``"D2.2"``).
    ``use_case`` uses the legacy use_case naming (e.g. ``"vc_diligence"``).
    Returns None if no custom translation is registered; callers should
    fall back to a generic translation built from the criterion's own
    level-anchor text.
    """
    persona_map = _TRANSLATIONS.get(criterion_id)
    if persona_map is None:
        return None
    return persona_map.get(use_case)


def covered_criteria() -> set[str]:
    """RSF criterion IDs that have at least one persona translation."""
    return set(_TRANSLATIONS.keys())


__all__ = ["PersonaTranslation", "covered_criteria", "translation_for"]
