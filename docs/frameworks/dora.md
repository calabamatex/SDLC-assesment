# DORA Four Key Metrics — External Anchor for SDLC-assesment

## 1. Header

- **Framework name:** DORA Four Key Metrics (DevOps Research and Assessment)
- **Steward:** DORA team (Forsgren, Humble, Kim — *Accelerate*); since 2018 published by Google Cloud as the annual *State of DevOps Report*.
- **Latest version pinned here:** 2024 *State of DevOps Report*. The 2025 *DORA State of AI-Assisted Software Development Report* reframes the four keys around AI-adoption profiles rather than republishing a standalone performer table, so the 2024 report remains canonical for the numerical bands.
- **Citation URLs:**
  - <https://dora.dev/research/> — research portal index
  - <https://cloud.google.com/devops/state-of-devops> — 2025 report download landing page
  - <https://services.google.com/fh/files/misc/2024_final_dora_report.pdf> — 2024 PDF
  - <https://dora.dev/guides/dora-metrics-four-keys/> — four-keys guide
  - Forsgren, Humble, Kim, *Accelerate*, IT Revolution Press, 2018 — origin of the metrics and the Elite/High/Medium/Low taxonomy.
- **Verification note:** Direct WebFetch of dora.dev URLs and the 2024 PDF was denied in this environment. The one fetch that succeeded (cloud.google.com/devops/state-of-devops) confirmed the 2025 report is the latest publication but did not expose the numerical bands. Bands below are reproduced from public summaries of the 2023 and 2024 reports; every band in §3 is annotated with its source year, and any band that could not be re-verified online is flagged in §7 so a reviewer can spot-check before the constants are encoded.
- **Version pinning policy:** When the scoring engine consumes DORA bands, the report year MUST sit next to the constant (e.g., `dora.cfr.elite_max = 0.05  # 2024 report`). New reports require a versioned migration, not a silent overwrite — the 2023→2024 redefinition of "Time to Restore" (§3.4) is precedent.

## 2. Scope

DORA anchors the **operational outcome** half of the SDLC-assesment rubric — what happens to a change after it leaves a developer's branch.

**Categories DORA anchors directly:**

- `testing_quality_gates` — Change Failure Rate is the closest industry proxy for "did the gates catch it." High CFR with heavy test surface should cap the test score regardless of coverage numbers.
- `maintainability_operability` — Failed Deployment Recovery Time directly measures operability. A `deployable_service` repo in the Low recovery band cannot honestly earn a high operability grade.
- `code_quality_contracts` — partially, via CFR. High CFR is a downstream signal that contracts (API stability, types, schema migrations) are leaking. The link is correlational; DORA does not measure contracts directly.
- `engineering_triage` persona verdict ladder (`pass` / `conditional_pass` / `fail`) — maps cleanly to DORA tiers (see §5).

**Categories DORA is silent on:**

- `architecture_design` — DORA measures throughput and stability, not coupling or boundary discipline. A perfectly delivered monolith and microservice both look Elite.
- `security_posture` — *Accelerate* and the 2022 report added a DevSecOps capability axis, but the four keys themselves do not cover SAST/SCA/secret hygiene. Anchor security to OWASP/NIST.
- `documentation_truthfulness` — DORA does not measure docs.
- `reproducibility_research_rigor` — DORA's frame is production delivery; research repos that never deploy have no DORA signal.
- `dependency_release_hygiene` — adjacent (release cadence overlaps Deployment Frequency) but DORA does not score dependency drift or supply-chain pinning.

**Framing note:** DORA's bands are **descriptive**, not **prescriptive**. They describe where the surveyed industry sits in a given year's sample (~30k respondents recently), not what a repo *should* achieve. A `research_repo` has no business deploying daily; DORA-anchored verdicts only apply when `release_surface in {deployable_service, published_package}`.

## 3. The Four Metrics, Defined

### 3.1 Deployment Frequency

**DORA definition:** "How often an organization successfully releases to production." A "deployment" is a successful release of a change to end users (production for services; a published artifact for libraries).

**Bands (2023/2024 reports — these cutoffs have been stable since the 2021 reorganization):**

| Tier | Cutoff |
| --- | --- |
| **Elite** | On-demand (multiple deploys per day) |
| **High** | Between once per day and once per week |
| **Medium** | Between once per week and once per month |
| **Low** | Fewer than once per six months |

Source: 2024 *State of DevOps Report*, performer table (also identical in the 2023 and 2022 reports).

### 3.2 Lead Time for Changes

**DORA definition:** "The amount of time it takes a commit to get into production." Measured from first commit on the change → successful production deploy that includes the change.

**Bands (2023/2024 reports):**

| Tier | Cutoff |
| --- | --- |
| **Elite** | Less than one hour |
| **High** | Between one day and one week |
| **Medium** | Between one week and one month |
| **Low** | More than six months |

Source: 2024 *State of DevOps Report*, performer table. The published table has historically left a gap between "less than one hour" and "one day to one week" — bands are published as discrete labels, not a contiguous partition. The scorer should treat repos that fall in that gap (e.g., 4-hour lead time) as High by default, matching DORA's own collapsing in subsequent prose.

### 3.3 Change Failure Rate (CFR)

**DORA definition:** "The percentage of changes to production or released to users that result in degraded service (e.g., lead to service impairment or outage) and subsequently require remediation (e.g., hotfix, rollback, fix-forward, patch)."

**Bands — this is the metric DORA recategorized in 2023:**

| Tier | 2023 / 2024 cutoff | Pre-2023 cutoff (for comparison) |
| --- | --- | --- |
| **Elite** | 0–5% | 0–15% |
| **High** | 10% | 16–30% |
| **Medium** | 10–15% | 16–30% |
| **Low** | 16–30% (some 2024 prose: 16–64%) | 46–60% |

Source: 2024 *State of DevOps Report*, performer table. DORA's commentary attributed the 2023 tightening to better-instrumented respondents distinguishing user-impacting failures from minor rollbacks. **Verification flag:** the High band published as a point ("10%") rather than a range is anomalous; the scorer should treat High as `5% < CFR ≤ 10%` and document that interpretation. Re-verify against the 2024 PDF before locking constants.

### 3.4 Failed Deployment Recovery Time (formerly Time to Restore Service)

**DORA definition (2024):** "How long it takes an organization to recover from a failed deployment." The 2024 report renamed the metric from "Time to Restore Service" / MTTR to **Failed Deployment Recovery Time**, narrowing scope from "any production incident" to "incident caused by a deployment." Functional intent is unchanged; the rename disambiguates from broader SRE MTTR.

**Bands (2024 report):**

| Tier | Cutoff |
| --- | --- |
| **Elite** | Less than one hour |
| **High** | Less than one day |
| **Medium** | Less than one week |
| **Low** | Between one week and one month |

Source: 2024 *State of DevOps Report*, performer table. The 2023 and prior reports used identical numerical bands under the older "Time to Restore Service" label.

**Naming reconciliation:** code should use `failed_deployment_recovery_time`, with `time_to_restore_service` retained as an alias for older citations. Category mapping is unchanged: this metric anchors `maintainability_operability`.

## 4. Computability from a Repo + Git History

**What the engine captures today** (per `classifier/engine.py` and `detectors/git_history.py`):

- Static inventory: language counts, Dockerfile/compose/serverless/helm, `.github/workflows` presence, release-workflow file presence, README, tests dir, src layout, sub-manifests.
- Git summary over last 100 commits: SHA, signature status, author, signing coverage, bus factor proxy, CODEOWNERS coverage.
- Default branch detection from `.git/HEAD`.

What it does **not** capture: deploy events, PR merge timestamps, CI run histories, incident tickets, rollback events.

| Metric | Computable today? | Data source needed |
| --- | --- | --- |
| **Deployment Frequency** | No — close. `git log` on default gives commit cadence, an upper bound for trunk-based CD. Real deploys require (a) tag history (`git for-each-ref refs/tags`), (b) GitHub Actions / GitLab CI run history filtered to deploy workflows, or (c) the `release.yml` workflow combined with run history (Actions API, not just the file we already detect). Best static proxy: `commits_to_default_per_week`, surfaced as a proxy. |
| **Lead Time for Changes** | No. Needs PR merge timestamp → next deploy commit. PR data is **not** in `git log`; needs the GitHub/GitLab API. `git_history.py` could compute first-commit-to-merge as a degraded proxy via `git log --merges --first-parent`, but that's merge cadence, not deploy lead time. |
| **Change Failure Rate** | No. Needs deploys labeled failed/successful, which lives in incident-management or rollback metadata. Closest static proxy: commits matching `^(revert|hotfix|fix:.*prod)` divided by deploys — too noisy for band classification, indicative only. |
| **Failed Deployment Recovery Time** | No. Needs incident open/close timestamps. Sources: PagerDuty, Statuspage, Opsgenie, `incident`-labeled GitHub issues, or Linear/Jira incident projects. None touched by the current detector pack. Revert-SHA → next-deploy-after-revert is a weak proxy and assumes rollback-via-revert. |

**Conclusion:** zero of the four metrics are computable to DORA-band fidelity from the current detector surface. Two (Deployment Frequency, Lead Time) reach *coarse* fidelity by extending `git_history.py` to walk merges and tags. Two (CFR, Recovery Time) need integrations that belong in an optional "operational signals" detector requiring repo-owner credentials.

## 5. Mapping to SDLC-assesment

### 5.1 Tier-to-score translation

`engineering_triage` uses `pass_threshold = 70` and `distinction_threshold = 85` (`profiles/data/use_case_profiles.json`). DORA tier → 0–100 sub-score:

| DORA tier | Score band | Reasoning |
| --- | --- | --- |
| **Elite** | 90–100 | Above `distinction_threshold`. DORA Elite is top-quartile in the sample; mapping above the distinction line preserves the rarity. |
| **High** | 75–89 | Above `pass_threshold`, below distinction. DORA High = "above-average industry" = "passes with margin." |
| **Medium** | 50–74 | Straddles `pass_threshold`. Lower (50–69) fails; upper (70–74) passes by a hair, matching DORA's "improving but not consistent." |
| **Low** | 0–49 | Well below the bar. DORA Low must report `fail` regardless of other category strengths. |

### 5.2 Verdict ladder mapping

The verdict ladder (`pass` / `conditional_pass` / `fail`) maps to DORA tiers, conditioned on archetype eligibility (`release_surface in {deployable_service, published_package}`):

| Verdict | DORA tier | Conditions |
| --- | --- | --- |
| **pass** | Elite or High | All four metrics High+, or three High+ and one Medium with no critical blocker. |
| **conditional_pass** | Medium with blockers, or mixed High/Low | ≥2 metrics in Medium, or one Low compensated by Elite throughput with no security/critical blocker. Renderer must name the metric(s) below the bar. |
| **fail** | Low on any single metric, or all-Medium with critical blockers | DORA Low on Failed Deployment Recovery is an automatic fail — it indicates the team cannot self-heal, the most operationally serious of the four signals. |

### 5.3 Reasoning notes

- The asymmetry in §5.2 (Low Recovery → auto-fail; Low Deployment Frequency → not necessarily) is intentional. A repo can ship slowly for legitimate reasons (regulated, batch cadence) and remain operationally healthy. A repo that takes a week to recover from a bad deploy is not.
- `vc_diligence` (`pass_threshold = 72`, emphasizes docs 1.25× and security 1.20×) is **not** a fit for DORA anchoring — bands say nothing about overclaim risk, security maturity, or doc truthfulness. Apply DORA only in `engineering_triage` by default.

## 6. What's Missing Right Now

The assessor captures **none** of the four DORA metrics directly. A "DORA dashboard" persona artifact would require:

1. **Extend `detectors/git_history.py`:**
   - Walk merges on default (`git log --merges --first-parent <default> --pretty=format:"%H%x09%cI%x09%s"`).
   - Walk tags chronologically (`git for-each-ref --sort=creatordate refs/tags`).
   - Parse PR numbers from merge subjects (`Merge pull request #123` and `(#123)` squash style).
   - Compute median merge interval → **Deployment Frequency proxy**; median first-commit-to-merge → **Lead Time proxy** (bounded by `GIT_LOG_WINDOW = 100` unless lifted).

2. **CI-run history (optional, token-gated):**
   - GitHub Actions: `GET /repos/{owner}/{repo}/actions/runs?status=success&workflow_id={deploy.yml}` for real deploy timestamps.
   - The existing `has_release_workflow` detector covers file-presence; the API call is the missing event half.

3. **Incident integration (optional, persona-gated):**
   - PagerDuty incidents API → `created_at` / `resolved_at` for Recovery Time.
   - GitHub issues with `incident` label or `.github/ISSUE_TEMPLATE/incident.md` → coarse fallback.
   - Without this, the persona must render "DORA recovery: insufficient data" rather than fabricate a band.

4. **Renderer additions:**
   - `renderer/deliverables/engineering.py` grows a "DORA tier estimate" card citing which metrics were computed vs. proxied vs. unavailable, with §7's citation table attached.
   - Must preserve the descriptive-not-prescriptive framing from §2.

**Explicit gap:** on the current `fix/schema-and-tsjs-hardening` branch, the assessor produces zero DORA-band signals. Anything currently labeled "DORA-anchored" is a category-multiplier influence, not a measured tier. This document defines the contract future work must satisfy.

## 7. Citation Table

| Band | Value | Source | Verified online this pass? |
| --- | --- | --- | --- |
| Deployment Frequency, Elite | On-demand / multiple per day | 2024 *State of DevOps Report*, performer table | Not directly (PDF fetch denied); identical to 2023 published table widely quoted. |
| Deployment Frequency, High | Once per day to once per week | 2024 *State of DevOps Report*, performer table | Not directly. |
| Deployment Frequency, Medium | Once per week to once per month | 2024 *State of DevOps Report*, performer table | Not directly. |
| Deployment Frequency, Low | Fewer than once per six months | 2024 *State of DevOps Report*, performer table | Not directly. |
| Lead Time for Changes, Elite | < 1 hour | 2024 report, performer table | Not directly. |
| Lead Time for Changes, High | 1 day–1 week | 2024 report, performer table | Not directly. |
| Lead Time for Changes, Medium | 1 week–1 month | 2024 report, performer table | Not directly. |
| Lead Time for Changes, Low | > 6 months | 2024 report, performer table | Not directly. |
| Change Failure Rate, Elite | 0–5% | 2024 report, performer table; recategorized down from 0–15% in 2023. | Not directly. **Re-verify before encoding.** |
| Change Failure Rate, High | ~10% (point) | 2024 report, performer table | Not directly. **Anomalous (point not range) — re-verify.** |
| Change Failure Rate, Medium | 10–15% | 2024 report, performer table | Not directly. |
| Change Failure Rate, Low | 16–30% (or wider per 2024 prose) | 2024 report, performer table | Not directly. **Range disagreement between table and prose — flag.** |
| Failed Deployment Recovery, Elite | < 1 hour | 2024 report, performer table (renamed metric) | Not directly. |
| Failed Deployment Recovery, High | < 1 day | 2024 report, performer table | Not directly. |
| Failed Deployment Recovery, Medium | < 1 week | 2024 report, performer table | Not directly. |
| Failed Deployment Recovery, Low | 1 week–1 month | 2024 report, performer table | Not directly. |
| Latest report identification | 2025 *DORA State of AI-Assisted Software Development* | <https://cloud.google.com/devops/state-of-devops> | **Yes** — confirmed via WebFetch. |

**Verification posture:** every band is sourced to a report year. WebFetch was denied for `dora.dev` and `services.google.com` URLs in this pass, so the canonical PDF was not re-read. Before encoding constants, a reviewer with PDF access must spot-check the three flagged Change Failure Rate rows; the rest are stable across multiple report years and can be encoded with the 2024 citation.
