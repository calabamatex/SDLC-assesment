# Repository Scoring Framework (RSF) v1.0

A generalizable, evidence-based scoring framework for assessing any GitHub (or Git-hosted) repository against the industry standards verified in the previous deliverable.

**Design constraints.**
- Every criterion derives from a primary-source framework verified at https://dora.dev/, https://scorecard.dev/, https://owaspsamm.org/, https://owasp.org/www-project-application-security-verification-standard/, https://owasp.org/www-project-top-ten/, https://csrc.nist.gov/projects/ssdf, https://www.nist.gov/cyberframework, https://slsa.dev/, https://cyclonedx.org/, https://spdx.dev/, https://sigstore.dev/, https://in-toto.io/, https://attack.mitre.org/, https://cwe.mitre.org/, https://www.iso.org/standard/27001, https://www.aicpa-cima.com/topic/audit-assurance/audit-and-assurance-greater-than-soc-2, https://cloudsecurityalliance.org/research/topics/caiq.
- Repo-observable signals are separated from org-scoped evidence. The framework runs on a repo alone, and degrades gracefully when org evidence is unavailable.
- Same evidence base, different consumers: persona weights produce different totals from the same per-criterion scores.

---

## 1. Schema

**Identifier format.** `v1.0-D<dimension>.<subcriterion>` — e.g., `v1.0-D2.3` is dimension 2, sub-criterion 3. Use the version prefix in any external reference; criteria may be added or refined in later versions.

**Dimensions.**

| ID | Dimension | Scope |
|---|---|---|
| D1 | Code Quality & Maintainability | Repo |
| D2 | Application Security Posture | Repo |
| D3 | Supply Chain Integrity | Repo |
| D4 | Delivery Performance | Repo (history-derived) |
| D5 | Engineering Discipline | Repo |
| D6 | Documentation & Transparency | Repo |
| D7 | Sustainability & Team Health | Repo (history + community) |
| D8 | Compliance & Governance Posture | Org-scoped |

**Per-criterion scoring scale.**

| Score | Label | Meaning |
|---|---|---|
| 0 | Absent | No evidence of the practice. Critical gap. |
| 1 | Ad hoc | Practice exists in pockets; no enforcement; not repeatable. |
| 2 | Developing | Practice attempted at scale; gaps remain; no automation. |
| 3 | Defined | Practice documented and consistently applied; partially automated. |
| 4 | Managed | Practice automated, measured, and gates merges/releases. |
| 5 | Optimizing | Practice continuously improved against evidence; benchmarked against peers. |

**Special values.**
- `N/A` — criterion does not apply (e.g., D8.1 PCI-DSS for a repo that handles no card data). Excluded from aggregation; the dimension's denominator shrinks accordingly.
- `?` — assessor could not collect evidence. Treated as 0 for scoring but flagged separately so the report distinguishes "absent" from "unverified."

---

## 2. Scoring rubrics (D1–D8)

### D1. Code Quality & Maintainability

Derived from: OpenSSF Scorecard CI-Tests / SAST / Code-Review probes (https://github.com/ossf/scorecard/blob/main/docs/checks.md), OWASP ASVS v5.0 (https://owasp.org/www-project-application-security-verification-standard/).

**D1.1 Automated test coverage**
- 0: No automated tests in the repo.
- 1: Tests exist; not run in CI; coverage unmeasured.
- 2: Tests run in CI; line coverage <50% or suite has known flaky tests.
- 3: Line coverage 50–70%; CI gates merges on test pass; flakiness tracked.
- 4: Line coverage >70%; branch coverage measured; CI gates merges; flakiness <2%.
- 5: Line coverage >85%; mutation or property-based testing in continuous use; flakiness <0.5%.

**D1.2 Static analysis & lint discipline**
- 0: No SAST or linter in CI.
- 1: Linter or SAST configured but findings ignored.
- 2: Linter blocking; SAST advisory only.
- 3: Both linter and SAST configured; new findings block merge.
- 4: SAST tuned to project (custom rules), CodeQL or Semgrep policies versioned.
- 5: Continuous SAST + IaC + container scanning; findings tracked to closure with SLA.

**D1.3 Code complexity / hotspot management**
- 0: No complexity tracking.
- 1: Complexity measurable but unaddressed; known hotspots accumulating.
- 2: Hotspots identified; refactor backlog exists.
- 3: Hotspot reduction part of every release.
- 4: Behavioral code analysis (e.g., CodeScene-style) tracked in dashboards.
- 5: Hotspot remediation tied to feature work; knowledge-concentration data informs onboarding.

### D2. Application Security Posture

Derived from: OWASP Top 10 (https://owasp.org/www-project-top-ten/), OWASP ASVS (https://owasp.org/www-project-application-security-verification-standard/), MITRE CWE (https://cwe.mitre.org/), NIST SSDF (https://csrc.nist.gov/projects/ssdf).

**D2.1 Known vulnerabilities in dependencies (CVE/OSV)**
- 0: ≥1 critical CVE open >30 days; no scanning.
- 1: Scanning in place; critical findings >7 days unresolved.
- 2: Critical resolved <7 days; high findings tracked but unbounded.
- 3: All severity tiers have SLAs and are tracked to closure.
- 4: Automated dependency updates (Dependabot/Renovate) plus reachability analysis.
- 5: VEX statements published for unfixed findings to disambiguate exposure.

**D2.2 Secrets in source / git history**
- 0: Active secrets discoverable; no scanning.
- 1: Secret scanning configured; historical secrets present and unrotated.
- 2: Pre-commit secret scanning; historical findings rotated and removed via filter-repo.
- 3: All secrets in vault (e.g., HashiCorp, AWS Secrets Manager); CI uses short-lived tokens.
- 4: OIDC / workload-identity for all CI secrets; no long-lived tokens.
- 5: Above + automated rotation cadence; periodic key-pair attestations.

**D2.3 ASVS / Top 10 conformance**
- 0: No declared ASVS level; common Top 10 patterns visible (hardcoded creds, raw SQL).
- 1: Top 10 awareness documented; informal review.
- 2: ASVS Level 1 targeted; partial pass.
- 3: ASVS Level 1 fully met; Level 2 partial.
- 4: ASVS Level 2 fully met for the application's risk profile.
- 5: ASVS Level 3 met; threat model reviewed quarterly.

**D2.4 Branch protection & code review enforcement**
- 0: Direct push to default branch allowed.
- 1: Default branch protected; admins can bypass.
- 2: Branch protection on default; required reviewers for protected branches.
- 3: CODEOWNERS in place; required reviewers cannot be self-approved; signed commits encouraged.
- 4: Above + signed commits required; rulesets enforce checks for all contributors including admins.
- 5: Above + required reviews from independent owners (e.g., security review for security-relevant paths).

### D3. Supply Chain Integrity

Derived from: SLSA (https://slsa.dev/spec/v1.0/levels), CycloneDX (https://cyclonedx.org/), SPDX (https://spdx.dev/), Sigstore (https://sigstore.dev/), in-toto (https://in-toto.io/), OpenSSF Scorecard (https://scorecard.dev/).

**D3.1 SBOM availability**
- 0: No SBOM produced.
- 1: SBOM generated ad hoc, not published.
- 2: SBOM generated per release in CycloneDX or SPDX format; published with releases.
- 3: SBOM generated per build; consumable via documented URL or registry.
- 4: SBOM signed and verifiable; ingested by downstream consumers.
- 5: SBOM + VEX statements published; SBOM diffing tracked release-over-release.

**D3.2 Artifact signing**
- 0: No artifact signing.
- 1: Artifacts signed with long-lived keys; manual rotation.
- 2: Sigstore / cosign signing on releases; signatures published.
- 3: Sigstore keyless signing tied to OIDC identity; recorded in Rekor.
- 4: Signed in-toto attestations for build provenance accompany every release.
- 5: Above + admission control / verification policy in deployment pipeline rejects unsigned artifacts.

**D3.3 SLSA build track level**
- 0: SLSA L0 — builds on developer machines.
- 1: SLSA L1 — provenance generated, may be unsigned.
- 2: SLSA L1 + provenance distributed with artifacts.
- 3: SLSA L2 — hosted build platform (GitHub Actions, GitLab CI) signs provenance.
- 4: SLSA L3 — hardened build platform; tamper-resistant provenance generation.
- 5: SLSA L3 + reproducible builds verified by independent rebuilders.

**D3.4 Dependency-update automation**
- 0: Dependencies pinned and never updated.
- 1: Manual updates only; no automation; updates >90 days behind.
- 2: Dependabot/Renovate configured for security updates only.
- 3: Automated updates for security and minor versions; merge automation for green builds.
- 4: Automated updates including major version review; renovate config versioned.
- 5: Above + reachability-aware prioritization; lockfile diffing reviewed in PR.

### D4. Delivery Performance

Derived from: DORA Core Model (https://dora.dev/guides/dora-metrics/). DORA performance levels (Elite / High / Medium / Low) are mapped to RSF 2/3/4/5; sub-Low maps to 0–1.

**D4.1 Deployment frequency**
- 0: <1 deploy/quarter.
- 1: 1–4 deploys/quarter (Low).
- 2: Monthly (Low/Medium boundary).
- 3: Weekly (Medium).
- 4: Daily (High).
- 5: On-demand, multiple per day (Elite).

**D4.2 Change lead time (commit to production)**
- 0: >6 months.
- 1: 1–6 months (Low).
- 2: 1 week to 1 month (Medium).
- 3: 1 day to 1 week (High lower bound).
- 4: <1 day (High).
- 5: <1 hour (Elite).

**D4.3 Change failure rate**
- 0: >60%.
- 1: 30–60% (Low).
- 2: 16–30% (Medium).
- 3: 11–15% (High lower bound).
- 4: 5–10%.
- 5: 0–5% (Elite).

**D4.4 Failed-deployment recovery time**
- 0: >1 month.
- 1: 1 week to 1 month (Low).
- 2: 1 day to 1 week (Medium).
- 3: <1 day (High).
- 4: <1 hour (Elite lower bound).
- 5: <15 minutes (Elite).

### D5. Engineering Discipline

Derived from: OpenSSF Scorecard Code-Review / Branch-Protection / CI-Tests probes, SPACE Activity dimension (https://queue.acm.org/detail.cfm?id=3454124).

**D5.1 PR review depth**
- 0: PRs merged without review.
- 1: Reviews requested but often skipped or rubber-stamped.
- 2: Required reviewer count enforced; review depth uneven.
- 3: CODEOWNERS routes reviews; review comments substantive on >50% of PRs.
- 4: Review SLAs measured; pickup time tracked.
- 5: Review depth, comment density, and rework metrics tracked dimension-by-dimension.

**D5.2 CI health (green rate, time, flakiness)**
- 0: No CI or CI broken on default branch.
- 1: CI configured; default-branch green rate <80%.
- 2: Green rate 80–90%; build times >30 min.
- 3: Green rate >90%; build times <30 min.
- 4: Green rate >95%; build times <15 min; flakiness <2%.
- 5: Green rate >98%; build times <10 min; test impact analysis in use.

**D5.3 Branch hygiene**
- 0: Long-lived feature branches; ad hoc merges.
- 1: Trunk-based intent; long-lived branches still common.
- 2: Trunk-based with short-lived branches; some history mess.
- 3: Linear history enforced; squash or rebase merges only.
- 4: Above + conventional commits / structured commit messages.
- 5: Above + automated changelog generation tied to commit conventions.

**D5.4 Release cadence and tagging**
- 0: No releases or untagged releases.
- 1: Releases tagged but irregular; no notes.
- 2: SemVer tagging; release notes manual.
- 3: SemVer + automated release notes; release branches as needed.
- 4: Release-please / changesets / semantic-release automation.
- 5: Above + release attestations (SLSA provenance attached).

### D6. Documentation & Transparency

Derived from: OpenSSF Best Practices Badge passing/silver/gold criteria (https://www.bestpractices.dev/), OpenSSF Scorecard, OWASP SAMM Education & Guidance practice (https://owaspsamm.org/).

**D6.1 README and onboarding**
- 0: No README or stub README.
- 1: README describes purpose; setup instructions incomplete.
- 2: New contributor can clone and run locally within 1 hour.
- 3: Above + architecture overview, key abstractions documented.
- 4: Above + ADRs (architectural decision records) published.
- 5: Above + runbook for production operations + threat model summary.

**D6.2 License clarity**
- 0: No LICENSE file.
- 1: License declared in README only.
- 2: LICENSE file matches an SPDX identifier.
- 3: SPDX identifier in every source file or top-level declaration; third-party licenses tracked.
- 4: Above + license-compatibility CI check; SBOM includes license fields.
- 5: Above + Developer Certificate of Origin or CLA enforced; license attestation per release.

**D6.3 Security policy & disclosure**
- 0: No SECURITY.md.
- 1: SECURITY.md present but vague.
- 2: SECURITY.md names a contact; vulnerability disclosure process defined.
- 3: Above + named SLA for triage and disclosure.
- 4: Above + CVE-numbering authority assignment or coordinated-disclosure agreement.
- 5: Above + bug bounty or VDP program with public scope and history.

**D6.4 Contribution guidance & governance**
- 0: No CONTRIBUTING.md, no governance.
- 1: CONTRIBUTING.md present.
- 2: Above + Code of Conduct.
- 3: Above + GOVERNANCE.md or named maintainers; review SLAs published.
- 4: Above + roadmap or release planning visible.
- 5: Above + open governance with public meetings or recorded decisions.

### D7. Sustainability & Team Health

Derived from: SPACE Satisfaction & Performance dimensions, OpenSSF Scorecard Maintained probe, CHAOSS metrics (https://chaoss.community/ — not independently verified during this build; flag for review).

**D7.1 Bus factor / knowledge concentration**
- 0: Single contributor authored >80% of code; no co-maintainers.
- 1: 2 contributors share most work; high concentration in critical paths.
- 2: 3+ active contributors; some critical paths still single-owner.
- 3: 5+ active contributors; CODEOWNERS includes ≥2 reviewers per critical path.
- 4: Above + onboarding pipeline producing new committers annually.
- 5: Above + governance prevents single-point-of-failure ownership at any layer.

**D7.2 Activity (sustained, not spiky)**
- 0: No commits in 6+ months.
- 1: Commits clustered; long quiet periods.
- 2: Commits roughly weekly.
- 3: Commits multiple times per week with trailing-90-day stability.
- 4: Sustained 12-month activity; no >2-week quiet windows.
- 5: Sustained activity with diverse contributor base across geographies/orgs.

**D7.3 Issue and PR responsiveness**
- 0: Issues / PRs accumulate untriaged for months.
- 1: Median triage time >7 days.
- 2: Median triage time 2–7 days.
- 3: Median triage time <48 hours; PR pickup time <24 hours.
- 4: Median PR cycle time <3 days; abandonment rate <10%.
- 5: Above + responsiveness tracked as an explicit team metric.

**D7.4 Maintainer continuity**
- 0: Original creator inactive; no successor.
- 1: Original creator only active maintainer; no succession plan.
- 2: ≥2 active maintainers; succession informal.
- 3: ≥2 active maintainers; written succession or sponsorship.
- 4: Project sponsored by foundation or company with continuity commitment.
- 5: Above + governance with rotation, term limits, or independent steering committee.

### D8. Compliance & Governance Posture (org-scoped)

Derived from: NIST CSF 2.0 (https://www.nist.gov/cyberframework), NIST SSDF (https://csrc.nist.gov/projects/ssdf), ISO/IEC 27001:2022 (https://www.iso.org/standard/27001), AICPA SOC 2 / Trust Services Criteria (https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022), CSA CAIQ v4 (https://cloudsecurityalliance.org/research/topics/caiq), regulatory frameworks per sector.

**Score `N/A` for any sub-criterion that does not apply to the repo's risk profile.**

**D8.1 Secure SDLC framework conformance (NIST SSDF / OWASP SAMM)**
- 0: No documented secure SDLC.
- 1: Practices exist informally.
- 2: NIST SSDF or SAMM gap assessment completed; remediation plan in progress.
- 3: SSDF attestation submitted (per EO 14028) or SAMM Level 1 met across practices.
- 4: SAMM Level 2 met across practices; or BSIMM benchmarking completed.
- 5: SAMM Level 3 in target practices; continuous improvement evidence.

**D8.2 Audit attestation (ISO 27001 / SOC 2)**
- 0: No audits.
- 1: Internal audit only.
- 2: SOC 2 Type I or ISO 27001 readiness assessment completed.
- 3: SOC 2 Type II or ISO 27001 certification covering current period.
- 4: Both SOC 2 Type II and ISO 27001:2022 in good standing.
- 5: Above + alignment to NIST CSF 2.0 with annual reassessment.

**D8.3 Sectoral regulatory conformance (when applicable)**
- 0: Required attestation absent or expired.
- 1: Gap assessment underway.
- 2: Initial attestation in progress.
- 3: Current attestation valid (HIPAA, PCI DSS, FedRAMP, CMMC, FDA SaMD, EU AI Act high-risk conformity, etc.).
- 4: Current attestation + automated continuous-monitoring evidence.
- 5: Above + cross-framework mapping (e.g., CSA CAIQ used to satisfy multiple).

**D8.4 Vendor-risk readiness**
- 0: No standardized vendor questionnaire response.
- 1: Ad hoc questionnaire responses.
- 2: CSA CAIQ-Lite completed.
- 3: CSA CAIQ v4 completed and posted to STAR Registry (or equivalent).
- 4: Above + Trust Center page with downloadable evidence.
- 5: Above + automated trust-portal updates from underlying control state.

---

## 3. Persona weight matrix

Each row sums to 100. Apply per-persona to per-dimension scores. `N/A` dimensions (typically D8 for many internal contexts) redistribute proportionally across remaining weights.

| Dimension | VC | PE/M&A | CTO/VP Eng | Eng Mgr | CISO | Procurement | OSS user | C-level non-tech |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D1 Code Quality | 15 | 15 | 10 | 15 | 5 | 5 | 10 | 5 |
| D2 Security | 20 | 20 | 15 | 10 | 30 | 25 | 15 | 15 |
| D3 Supply Chain | 10 | 15 | 10 | 5 | 20 | 20 | 25 | 5 |
| D4 Delivery | 15 | 10 | 25 | 25 | 5 | 5 | 5 | 15 |
| D5 Engineering Discipline | 15 | 10 | 20 | 25 | 10 | 10 | 15 | 10 |
| D6 Documentation | 10 | 5 | 5 | 10 | 5 | 10 | 15 | 5 |
| D7 Sustainability | 10 | 5 | 5 | 10 | 5 | 5 | 15 | 10 |
| D8 Compliance | 5 | 20 | 10 | 0 | 20 | 20 | 0 | 35 |
| **Sum** | **100** | **100** | **100** | **100** | **100** | **100** | **100** | **100** |

**Rationale anchors.**
- VC weights security, code quality, and discipline highest because cost-to-cure dominates valuation impact; compliance is light because most VC targets are pre-regulatory.
- PE/M&A shifts weight from raw delivery to compliance and supply chain: the buyer inherits regulatory risk.
- CTO/VP Eng weights delivery and discipline highest; this is the operational lens.
- Eng Mgr concentrates on D4/D5/D1 (the daily flow); compliance is org's problem.
- CISO weights security, supply chain, and compliance highest.
- Procurement mirrors CISO but with stronger compliance emphasis (vendor onboarding gating).
- OSS user weights supply chain, sustainability, and documentation; this consumer cannot influence delivery cadence and rarely has compliance interest.
- C-level non-tech weights compliance highest because liability and audit posture dominate their lens; balanced across delivery and security as risk inputs.

---

## 4. Aggregation

**Per-dimension score (D<i>):**
$$D_i = \frac{\sum_{j} s_{ij}}{n_i \cdot 5} \times 5$$
where $s_{ij}$ is the score for sub-criterion *j* of dimension *i*, and $n_i$ is the count of sub-criteria scored (excluding `N/A`). $D_i$ is therefore on the same 0–5 scale as its inputs.

**Persona-weighted total (T):**
$$T = \sum_{i=1}^{8} D_i \cdot w_i$$
where $w_i$ is the persona weight for dimension *i*. The total $T$ is on a 0–500 scale (5 × 100).

**Normalized presentation:**
$$T_{\%} = \frac{T}{500} \times 100$$
giving a 0–100% score for executive reporting.

**Confidence flag.** Any dimension with ≥1 `?` (unverified) sub-criterion is reported with a confidence flag. If >25% of total weight maps to flagged dimensions, the report header carries a "limited confidence" warning.

---

## 5. Calibration & inter-rater reliability

**Calibration set.** Score against three reference points before assessing a target:
1. A widely-used OSS project that publishes Scorecard, SLSA, and SAMM evidence (e.g., `ossf/scorecard` itself, `kubernetes/kubernetes`, `sigstore/cosign`). Expected RSF total: 4.0+.
2. A typical mid-stage SaaS company repo (private comparable). Expected: 2.5–3.5.
3. A neglected internal repo with no CI/CD discipline. Expected: 0.5–1.5.

**Inter-rater protocol.** Two assessors score independently against the rubric. Disagreements >1 point per sub-criterion trigger evidence review. If disagreement persists, the lower score is recorded and the gap is logged. Track inter-rater agreement over time as a quality signal on the framework itself.

**Anti-gaming.** Several sub-criteria (D1.1 coverage thresholds, D4 deployment frequency, D7.2 activity) are easily inflated by superficial means. The rubric requires evidence (CI logs, release tags, commit history) not self-attestation. In any tie, prefer the score supported by primary-source artifacts.

---

## 6. Operating procedure

**Step 1 — Set persona and scope.** Pick the consumer (or run multiple). Decide whether D8 is in scope; if not, mark all D8 sub-criteria `N/A`.

**Step 2 — Run automated collectors.**
- OpenSSF Scorecard (`scorecard --repo=github.com/owner/repo`)
- Dependency vulnerability scan (Dependabot, OSV-Scanner, or equivalent)
- SAST (CodeQL, Semgrep)
- Secret scanning (Gitleaks, GitHub secret scanning)
- DORA metrics (LinearB / Jellyfish / Swarmia / GitHub Insights / Apache DevLake)
- SBOM generation (Syft → CycloneDX/SPDX)
- Activity / contributor analytics (`git shortlog`, GitHub API, CHAOSS)

**Step 3 — Score each sub-criterion.** Use the 0–5 anchors. Record evidence path (URL, file path, log excerpt) for every score. No score without evidence.

**Step 4 — Collect org evidence (D8 only).** Request: most recent SOC 2 / ISO certificate, CSA CAIQ if cloud, regulatory attestations as applicable. If unavailable, mark `?` and flag.

**Step 5 — Aggregate and report.**
- Per-dimension scores $D_1 … D_8$
- Per-persona weighted totals $T$ for every persona of interest
- Top 5 lowest sub-criterion scores with remediation references
- Confidence flag if applicable
- Changelog from prior assessment if this is a re-score

**Cadence.** Quarterly for actively developed repos. Annual minimum. After any architectural change, security incident, or audit cycle.

---

## 7. Output template

```
Repository: <owner/repo>
Commit assessed: <SHA>
Date: <YYYY-MM-DD>
Framework version: RSF v1.0
Assessor(s): <name(s)>

Per-dimension scores (0–5):
  D1 Code Quality:           3.3
  D2 Application Security:   4.0
  D3 Supply Chain:           3.5
  D4 Delivery Performance:   3.0
  D5 Engineering Discipline: 4.0
  D6 Documentation:          3.5
  D7 Sustainability:         2.5
  D8 Compliance:             N/A (out of scope)

Persona-weighted totals (0–100%):
  VC:               68%
  PE/M&A:           65% [confidence: limited — D8 N/A]
  CTO/VP Eng:       72%
  Engineering Mgr:  74%
  CISO:             67%
  Procurement:      63% [confidence: limited — D8 N/A]
  OSS user:         70%
  C-level non-tech: 60% [confidence: limited — D8 N/A]

Top 5 remediation priorities (lowest sub-scores, weighted by persona of record):
  1. D7.1 Bus factor (1) — single-owner critical paths in <module>; add CODEOWNERS reviewer
  2. D3.3 SLSA level (2) — currently L1; move to L2 by adopting hosted-builder signed provenance
  3. D7.4 Maintainer continuity (2) — no documented succession; publish GOVERNANCE.md
  4. D4.1 Deployment frequency (2) — monthly; target weekly via release-please automation
  5. D2.1 Vulnerability SLA (3) — define and publish SLA tiers

Evidence log: <path or attached>
```

---

## 8. Worked example

**Target.** Mid-stage SaaS, ~50 services, 30-engineer team, no public-sector customers, B2B SaaS sold to enterprise.

**Per-dimension scoring (illustrative).**

| Dim | D<i>.1 | .2 | .3 | .4 | Mean |
|---|---:|---:|---:|---:|---:|
| D1 | 3 | 4 | 3 | — | 3.3 |
| D2 | 4 | 4 | 3 | 5 | 4.0 |
| D3 | 4 | 3 | 3 | 4 | 3.5 |
| D4 | 4 | 4 | 2 | 2 | 3.0 |
| D5 | 4 | 4 | 3 | 5 | 4.0 |
| D6 | 4 | 4 | 2 | 4 | 3.5 |
| D7 | 1 | 3 | 3 | 3 | 2.5 |
| D8 | 4 | 3 | 3 | 4 | 3.5 |

**Persona-weighted totals (T_%).**

| Persona | Computation | Total |
|---|---|---:|
| VC | (3.3·15 + 4.0·20 + 3.5·10 + 3.0·15 + 4.0·15 + 3.5·10 + 2.5·10 + 3.5·5) / 500 | **70%** |
| PE/M&A | (3.3·15 + 4.0·20 + 3.5·15 + 3.0·10 + 4.0·10 + 3.5·5 + 2.5·5 + 3.5·20) / 500 | **70%** |
| CTO/VP Eng | (3.3·10 + 4.0·15 + 3.5·10 + 3.0·25 + 4.0·20 + 3.5·5 + 2.5·5 + 3.5·10) / 500 | **70%** |
| Eng Mgr | (3.3·15 + 4.0·10 + 3.5·5 + 3.0·25 + 4.0·25 + 3.5·10 + 2.5·10 + 3.5·0) / 500 | **70%** |
| CISO | (3.3·5 + 4.0·30 + 3.5·20 + 3.0·5 + 4.0·10 + 3.5·5 + 2.5·5 + 3.5·20) / 500 | **72%** |
| Procurement | (3.3·5 + 4.0·25 + 3.5·20 + 3.0·5 + 4.0·10 + 3.5·10 + 2.5·5 + 3.5·20) / 500 | **72%** |
| OSS user | (3.3·10 + 4.0·15 + 3.5·25 + 3.0·5 + 4.0·15 + 3.5·15 + 2.5·15 + 3.5·0) / 500 | **70%** |
| C-level non-tech | (3.3·5 + 4.0·15 + 3.5·5 + 3.0·15 + 4.0·10 + 3.5·5 + 2.5·10 + 3.5·35) / 500 | **70%** |

The illustrative scores cluster tightly near 70%. This is a feature, not a bug — a balanced repo profile produces consistent results across personas, while an imbalanced one (e.g., elite delivery, weak compliance) shows divergence the framework is designed to surface.

**Diverging case (same repo, hypothetical: D8 dropped to 1.0 due to expired SOC 2):**

| Persona | Total |
|---|---:|
| VC | 68% (−2) |
| PE/M&A | 60% (−10) |
| CISO | 62% (−10) |
| Procurement | 62% (−10) |
| C-level non-tech | 53% (−17) |
| OSS user | 70% (unchanged) |
| CTO/VP Eng | 65% (−5) |
| Eng Mgr | 70% (unchanged) |

This is what the framework is for: same repo, different consumers, consequential differences in how a single weakness lands.

---

## 9. Versioning & extensibility

- **Framework version** is included in every assessment output (`RSF v1.0`). Re-scoring against a newer version requires explicit re-assessment, not score conversion.
- **Adding criteria** is allowed in minor versions (v1.1, v1.2). Adjusting weights or rubric anchors triggers a major version (v2.0).
- **Custom dimensions** are permitted with the prefix `X-` (e.g., `v1.0-XAI.1` for an AI-specific dimension). They do not contribute to the standard total unless declared in the report header.
- **Mappings to other frameworks** (e.g., RSF → ISO 27001 controls, RSF → NIST SSDF practices) should be maintained as a separate artifact, versioned in lockstep.

---

## 10. Known limitations

1. **D8 requires off-repo evidence.** Unavoidable for compliance dimensions. Mitigated by the `N/A` and `?` conventions.
2. **DORA metrics assume CD pipelines.** For monorepo or library-only projects without continuous deployment, D4.1 and D4.4 may be `N/A`. Compensate by reweighting D4 to remaining sub-criteria.
3. **Sustainability metrics are noisy on small repos.** A 1-person repo may score `0` on D7.1 indefinitely. The framework is not designed to be charitable to single-maintainer projects; it scores what is observable.
4. **No reproducibility check on rubric calibration across orgs.** Inter-rater reliability data should be collected and published once enough assessments accumulate.
5. **Tooling vendor lock.** Several signals (LinearB, Swarmia, Jellyfish for DORA; Snyk, Black Duck for SCA) are easier to capture with commercial tools. Open-source equivalents exist (Apache DevLake for DORA, OSV-Scanner + Syft for SCA + SBOM) and produce equivalent scores; the framework is tool-neutral by design.
6. **CHAOSS metrics URL not independently verified during this build.** D7 references CHAOSS directionally; if formal CHAOSS metric IDs are added in v1.1, verify the URL.

---

## 11. Appendix: framework-to-criterion mapping

| RSF criterion | Primary framework | Verified URL |
|---|---|---|
| D1.1 Test coverage | OpenSSF Scorecard CI-Tests | https://github.com/ossf/scorecard/blob/main/docs/checks.md |
| D1.2 Static analysis | OpenSSF Scorecard SAST | https://github.com/ossf/scorecard/blob/main/docs/checks.md |
| D1.3 Complexity | (no single primary; behavioral analysis literature) | — |
| D2.1 Vulns | NIST SSDF RV.1; OSV | https://csrc.nist.gov/projects/ssdf |
| D2.2 Secrets | OWASP ASVS V2 | https://owasp.org/www-project-application-security-verification-standard/ |
| D2.3 ASVS / Top 10 | OWASP ASVS, OWASP Top 10 | https://owasp.org/www-project-application-security-verification-standard/ ; https://owasp.org/www-project-top-ten/ |
| D2.4 Branch protection | OpenSSF Scorecard Branch-Protection / Code-Review | https://github.com/ossf/scorecard/blob/main/docs/checks.md |
| D3.1 SBOM | CycloneDX (ECMA-424); SPDX (ISO/IEC 5962:2021) | https://cyclonedx.org/ ; https://spdx.dev/ |
| D3.2 Signing | Sigstore | https://sigstore.dev/ |
| D3.3 SLSA | SLSA v1.0 build track | https://slsa.dev/spec/v1.0/levels |
| D3.4 Dep updates | OpenSSF Scorecard Dependency-Update-Tool | https://github.com/ossf/scorecard/blob/main/docs/checks.md |
| D4.1–D4.4 | DORA Core Model | https://dora.dev/guides/dora-metrics/ |
| D5.1 Reviews | OpenSSF Scorecard Code-Review; SPACE Activity | https://github.com/ossf/scorecard/blob/main/docs/checks.md ; https://queue.acm.org/detail.cfm?id=3454124 |
| D5.2 CI health | OpenSSF Scorecard CI-Tests | https://github.com/ossf/scorecard/blob/main/docs/checks.md |
| D5.3 Branch hygiene | (community practice) | — |
| D5.4 Releases | OpenSSF Scorecard Signed-Releases | https://github.com/ossf/scorecard/blob/main/docs/checks.md |
| D6.1 README | OpenSSF Best Practices Badge passing criteria | https://www.bestpractices.dev/ |
| D6.2 License | OpenSSF Scorecard License; SPDX | https://github.com/ossf/scorecard/blob/main/docs/checks.md ; https://spdx.dev/ |
| D6.3 Security policy | OpenSSF Scorecard Security-Policy | https://github.com/ossf/scorecard/blob/main/docs/checks.md |
| D6.4 Contribution & governance | OpenSSF Best Practices Badge | https://www.bestpractices.dev/ |
| D7.1 Bus factor | (community practice; CodeScene-style hotspot) | — |
| D7.2 Activity | OpenSSF Scorecard Maintained | https://github.com/ossf/scorecard/blob/main/docs/checks.md |
| D7.3 Responsiveness | SPACE Performance dimension | https://queue.acm.org/detail.cfm?id=3454124 |
| D7.4 Maintainer continuity | (community practice) | — |
| D8.1 Secure SDLC | NIST SSDF; OWASP SAMM | https://csrc.nist.gov/projects/ssdf ; https://owaspsamm.org/ |
| D8.2 Audit attestation | ISO/IEC 27001:2022; AICPA SOC 2 | https://www.iso.org/standard/27001 ; https://www.aicpa-cima.com/topic/audit-assurance/audit-and-assurance-greater-than-soc-2 |
| D8.3 Sectoral | EU AI Act; HIPAA; PCI DSS; FedRAMP; CMMC; FDA SaMD | https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng ; https://www.hhs.gov/hipaa/for-professionals/security/index.html ; https://www.pcisecuritystandards.org/ ; https://www.fedramp.gov/ ; https://dodcio.defense.gov/CMMC/ ; https://www.fda.gov/medical-devices/digital-health-center-excellence/cybersecurity |
| D8.4 Vendor risk | CSA CAIQ v4 | https://cloudsecurityalliance.org/research/topics/caiq |

---

**End of RSF v1.0.**
