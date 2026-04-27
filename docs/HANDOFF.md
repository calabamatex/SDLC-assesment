# Handoff: SDLC-assesment / `feat/v0.10.0-persona-deliverables` branch

You are picking up an in-progress repository-scoring tool. The user is frustrated with the prior session's pattern of half-measures and surface-level work. This document is the unfiltered state-of-play. Read it end-to-end before writing any code.

---

## 1. Who the user is and what they want

The user is `calabamatex` (Ethan Allen). They are building a **diligence-grade repository assessor** — a CLI tool that ingests a Git repo and produces persona-aware reports for VC, M&A, engineering, CISO, procurement, and other consumer roles.

The user's stated v1 bar is **industry-quality (sellable / open-source-shippable as a serious tool)**. They have been explicit that:

- Every numeric scoring constant must be anchored to a published industry framework, not invented.
- Reports must read as defensible diligence documents — not "engineering bug lists."
- Persona-specific output means *different content*, not the same engineering analysis with relabeled sections.
- "Half measures" — adding new while keeping legacy in place — are a primary failure mode.

The user has caught the prior session in this pattern repeatedly. **They will catch you too if you repeat it.** The "Failure patterns" section below names the specific traps.

---

## 2. Branch + commit state (read this before changing anything)

```
Branch:  feat/v0.10.0-persona-deliverables
Latest:  33bffd8 fix(rsf): use the rich evidence already in git_summary for D5.4 / D7.1 / D7.2 / D7.4
```

Recent commits (newest first):

| SHA | Title |
|---|---|
| `33bffd8` | fix(rsf): real differentiation from git_summary signals |
| `b803e7a` | refactor(deliverables): rip out legacy made-up rubric |
| `e065581` | feat(rsf): per-criterion scorers + CLI wiring + HTML render |
| `559fce4` | feat(rsf): codify RSF v1.0 as the canonical scoring framework |
| `8f11d0f` | docs(frameworks): CWE Top 25 + DORA anchor research |
| `a7e6b55` | feat(deliverables): provenance header |
| `6a0d081` | fix(deliverables): commit lost _vocab.py + matrix.py |
| `f5972cc` | test(deliverables): integration tests + persona-distinct exec summaries |
| `07ee506` | feat(renderer): surface depth-pass content in HTML |

**The branch is not yet merged to `main`.** PR/release work is pending; do not cut a release until the work below is honestly done.

---

## 3. What the assessor *does* (objectively)

The CLI is `python -m sdlc_assessor.cli`. The pipeline:

1. **Classify** the repo (`sdlc_assessor/classifier/engine.py`) — picks an archetype, maturity, network exposure. Confidence is often low (0.6 for AgentSentry, 0.9 for sdlc-assessor itself).
2. **Collect evidence** (`sdlc_assessor/collector/engine.py` + `sdlc_assessor/detectors/*`) — runs detectors, emits findings.
3. **Score** (`sdlc_assessor/scorer/engine.py`) — *legacy 0–100 scoring engine, kept for back-compat.* Outputs `scoring.overall_score` and `scoring.verdict`. **The deliverable layer no longer reads from this for primary scoring** (see RSF below); legacy fields remain for any downstream consumer that hasn't migrated.
4. **RSF v1.0 assessment** (`sdlc_assessor/rsf/`) — *new canonical scoring*. Reads scored payload + repo path, produces `RSFAssessment` with per-dimension scores (0–5), per-persona weighted totals (0–100%), and confidence flagging. Attached to `scored.json` as `scored["rsf"]`.
5. **Remediation plan** (`sdlc_assessor/remediation/planner.py`) — generates fix tasks; output attached to `scored["remediation_plan"]`.
6. **Render** (`sdlc_assessor/renderer/deliverable_html.py` + `sdlc_assessor/renderer/deliverables/`) — produces persona-distinct HTML reports for one of four use-cases.

**Markdown rendering and the legacy v0.9.0 HTML renderer (`sdlc_assessor/renderer/html.py`) still exist** but are no longer the primary output path. The depth-pass HTML renderer `deliverable_html.py` is.

---

## 4. The RSF v1.0 framework — central to the current work

The user provided **Repository Scoring Framework (RSF) v1.0** as the canonical industry-anchored framework. It is at `docs/frameworks/rsf_v1.0.md`, **verbatim** from their attachment. The doc is the source of truth for every scoring decision.

Structure:

- **8 dimensions** (D1–D8): Code Quality, App Security, Supply Chain, Delivery, Engineering Discipline, Documentation, Sustainability, Compliance.
- **31 sub-criteria** (D1.1–D8.4), each with 6 level anchors (0=Absent, 1=Ad hoc, 2=Developing, 3=Defined, 4=Managed, 5=Optimizing). Anchor text is reproduced verbatim in `sdlc_assessor/rsf/criteria.py` — **do not paraphrase those anchors; they are the spec**.
- **8 personas** (VC, PE/M&A, CTO/VP Eng, Eng Mgr, CISO, Procurement, OSS user, C-level non-tech), each with a row of weights summing to 100. Codified in `sdlc_assessor/rsf/personas.py`.
- **Aggregation** (`sdlc_assessor/rsf/aggregate.py`):
  - `D_i = mean(s_ij)` for sub-criteria `j` in dimension `i` (excluding N/A)
  - `T = Σ D_i × w_i` for persona's weights — 0–500 scale
  - `T_% = T / 500 × 100` — 0–100% executive view
- **Special values** (RSF §1):
  - `?` = evidence not collected — treated as 0 in math but flagged separately
  - `N/A` = does not apply — excluded from dimension's denominator; persona weights for N/A dimensions are proportionally redistributed
- **Confidence flag** (RSF §4): any dim with ≥1 `?` is flagged; if >25% of persona's weight maps to flagged dims, report shows "limited confidence"

The published-framework anchors per criterion (RSF §11):

| RSF id | Primary framework | URL |
|---|---|---|
| D1.1, D1.2, D2.4, D3.4, D5.1, D5.2, D5.4, D6.2, D6.3, D6.4, D7.2 | OpenSSF Scorecard | https://github.com/ossf/scorecard/blob/main/docs/checks.md |
| D2.1 | NIST SP 800-218 SSDF + OSV | https://csrc.nist.gov/projects/ssdf |
| D2.2, D2.3 | OWASP ASVS, OWASP Top 10 | https://owasp.org/www-project-application-security-verification-standard/ ; https://owasp.org/www-project-top-ten/ |
| D3.1 | CycloneDX (ECMA-424) ; SPDX (ISO/IEC 5962:2021) | https://cyclonedx.org/ ; https://spdx.dev/ |
| D3.2 | Sigstore | https://sigstore.dev/ |
| D3.3 | SLSA v1.0 | https://slsa.dev/spec/v1.0/levels |
| D4.1–D4.4 | DORA Core Model | https://dora.dev/guides/dora-metrics/ |
| D5.1, D7.3 | OpenSSF Scorecard + SPACE | https://queue.acm.org/detail.cfm?id=3454124 |
| D6.1, D6.4 | OpenSSF Best Practices Badge | https://www.bestpractices.dev/ |
| D7.1, D7.4 | community practice (CodeScene-style hotspots) | — |
| D8.1 | NIST SSDF + OWASP SAMM | https://owaspsamm.org/ |
| D8.2 | ISO/IEC 27001:2022 + AICPA SOC 2 | https://www.iso.org/standard/27001 ; https://www.aicpa-cima.com/topic/audit-assurance/audit-and-assurance-greater-than-soc-2 |
| D8.3 | EU AI Act / HIPAA / PCI DSS / FedRAMP / CMMC / FDA SaMD | (multiple — see RSF §11) |
| D8.4 | CSA CAIQ v4 | https://cloudsecurityalliance.org/research/topics/caiq |

**If you ever need a value from one of these frameworks (e.g., a CWE ID, a SLSA level definition, a DORA band cutoff), do NOT default to your training memory.** Either WebFetch from the URL or ask the user for the canonical text. The user has flagged this directly: *"Never just default to what you have in memory for the standard."*

---

## 5. What is *actually measured* vs unverified — the brutal honesty

After the RSF cutover and the four scorer fixes in commit `33bffd8`, the assessor scores **14 of 31 RSF sub-criteria** against real anchors. The other 17 return `?` (RSF-correct disclosure that evidence wasn't collected).

### Real-anchor scorers (14 of 31)

| RSF id | Title | What we check | Bug risk |
|---|---|---|---|
| D2.2 | Secrets in source / git history | Findings with subcategory `probable_secrets` / `committed_credential` + presence of `.gitleaks.toml` or secret-scan workflow | Regex-only; doesn't analyze rotation status, blast radius, or vault adoption |
| D2.3 | ASVS / Top 10 conformance | Findings with subcategory in `_TOP_TEN_PATTERN_SUBCATS` | Pattern-only, not actual ASVS audit. Score 0 fires only on visible patterns; absence of patterns ≠ ASVS Level 1+ |
| D3.1 | SBOM availability | File named `sbom.json` / `sbom.cdx.json` / etc. OR workflow mentioning syft/cyclonedx/anchore/sbom-action | Doesn't generate or validate SBOM; only checks for file presence |
| D3.2 | Artifact signing | Workflow mentioning cosign/sigstore/in-toto/slsa-framework | Doesn't verify signatures or check Rekor; just keyword match |
| D3.4 | Dependency-update automation | `.github/dependabot.yml` or `renovate.json` presence | Doesn't inspect config scope (security-only vs minor vs major) |
| D5.4 | Release cadence and tagging | `git tag --list` count + workflow mentions of release-please/semantic-release/changesets/slsa | Doesn't verify SemVer compliance, release-note structure, or attestation depth |
| D6.1 | README and onboarding | README presence + non-empty line count ≥5 | No content analysis (no detection of architecture / ADRs / runbooks / threat model) |
| D6.2 | License clarity | LICENSE file present + SPDX-hint string match | No SBOM cross-check; no license-compatibility analysis |
| D6.3 | Security policy & disclosure | SECURITY.md presence + line count + contact-language regex (`@`/`email`/`report`/`disclosure`/`contact`) | No content analysis; no SLA / CVE-numbering-authority / bug-bounty detection |
| D6.4 | Contribution guidance & governance | CONTRIBUTING.md / CODE_OF_CONDUCT.md / GOVERNANCE.md presence | No content analysis; no roadmap / open-governance verification |
| D7.1 | Bus factor / knowledge concentration | `git_summary.top_authors[0].share` (precise) + bus_factor + CODEOWNERS presence | Right anchor logic now; depends on git collector window (last 95 commits by default) |
| D7.2 | Activity (sustained, not spiky) | `commits_last_30_days` / 90 / 180 / 365 from git collector | Right anchor logic now; doesn't detect "long quiet windows" within the period |
| D7.4 | Maintainer continuity | `len(git_summary.top_authors)` + GOVERNANCE.md / CODEOWNERS presence | Doesn't verify succession docs / foundation sponsorship / governance rotation |
| D5.4 (above) — listed for reference |  |  |  |

### Unverified (`?`) — what's NOT measured (17 of 31)

| RSF id | Title | What would be needed |
|---|---|---|
| D1.1 | Automated test coverage | Real coverage % from `coverage.py` / `nyc` / etc. — file count ≠ coverage |
| D1.2 | Static analysis & lint discipline | SAST findings ingested into RSF (the SAST adapters exist but their findings don't reach this scorer) |
| D1.3 | Code complexity / hotspot management | Behavioral code analysis (CodeScene / radon / lizard) |
| D2.1 | Known vulnerabilities (CVE/OSV) | OSV-Scanner or pip-audit / npm audit / `osv-scanner` adapter |
| D2.4 | Branch protection & code review enforcement | GitHub Settings API |
| D3.3 | SLSA build track level | Build attestation inspection (Rekor lookups, in-toto provenance verification) |
| D4.1 | Deployment frequency | DORA history walk: deploy events from CI runs or release tags |
| D4.2 | Change lead time | PR-merge-to-deploy time from GitHub API |
| D4.3 | Change failure rate | Rollback-commit detection, incident-management integration |
| D4.4 | Failed-deployment recovery time | Incident-management integration (PagerDuty/Statuspage) |
| D5.1 | PR review depth | GitHub PR API for review counts, comment density |
| D5.2 | CI health (green rate, time, flakiness) | Workflow-run history from GitHub Actions API |
| D5.3 | Branch hygiene | Git log analysis for trunk-based vs long-lived branches, conventional commits |
| D7.3 | Issue and PR responsiveness | GitHub Issues + PR API for triage time, cycle time, abandonment |
| D8.1 | Secure SDLC framework conformance | Org-scoped: SSDF attestation / SAMM gap assessment evidence |
| D8.2 | Audit attestation (ISO 27001 / SOC 2) | Org-scoped: audit certificates |
| D8.3 | Sectoral regulatory conformance | Org-scoped: HIPAA / PCI / FedRAMP / CMMC / FDA / EU AI Act attestations |
| D8.4 | Vendor-risk readiness | Org-scoped: CSA CAIQ / Trust Center artifacts |

### What this means in practice

When you run the assessor on a real codebase, the persona-weighted totals will be in the **3–10% range** for most repos — not because the repo is bad, but because the assessor only collects ~45% of the evidence the RSF requires. The math obeys RSF §1 ("`?` treated as 0") but the result is **uninformative as a diligence document**. Two materially different repos will look similar because most of the scoring is dominated by `?`.

**This is the core unsolved problem of the project.** The user is rightly furious about it. The fix is not in the scoring engine; it's in the detector pipeline. See "Immediate next work" below.

---

## 6. The user's working style and red lines

### Hard requirements

- **Every numeric anchor must trace to a published source.** RSF v1.0 → `docs/frameworks/rsf_v1.0.md`. CWE → MITRE. CVSS → FIRST. DORA → State of DevOps Reports. SSDF → NIST SP 800-218. Do not invent.
- **Removals before additions.** When the user directs a substrate change, audit existing references first, list them, remove them, then add the replacement. Adding without removing produces self-contradicting reports.
- **Grep-before-done.** After committing, re-render and grep the output to prove the directive landed. Paste the count in chat.
- **Audit visible in chat before code.** When the user asks for a substrate change, paste the grep results showing every legacy reference (file:line) before writing new code. The user can verify the removal scope.
- **Mid-flight state named explicitly.** Do not commit partial work as if it's complete. Say "this commit is part 1 of N; here's what's still broken until parts 2..N land."

### Communication patterns

- **Stop asking for permission.** The user said this directly: when given a directive, execute. Don't ask "should I proceed?" — proceed and show the result.
- **Concise direct acknowledgement when called out.** Don't be defensive. Don't promise "I'll be different." Show different behavior.
- **Surface critique honestly even when uncomfortable.** If the analysis is thin, say so. The user will catch it anyway.

### What the user has flagged as failure modes (with verbatim quotes)

| Failure | User's words |
|---|---|
| Inventing values when standards exist | *"Appears you have made up your own scoring matrix, with nothing other than 'trust me bro' to back up your claims."* |
| Defaulting to memory for standard values | *"Never just default to what you have in memory for the standard, btw."* |
| Half-measures (add without remove) | *"You changed the engine for assessment but left the actual reporting in the same state … Why do you continue to do 1/2 measures?"* |
| Surface-level analysis posing as depth | *"reads like a bug list, not an actual buiness based perspective with recommendations"* |
| Missing the persona translation | *"You have shown your inability to think beyond Engineering and make the information persona specific."* |
| Ignoring directives | *"WHY DO YOU CONTINUE TO MAKE CHOICES THAT ARE COUTNER TO THE DIRECTIVES?"* |
| Skipping spec items quietly | *"There is no SAST. No OSV/CVE scan. No actual SBOM generation. … WHY DID YOU SKIP ALL THIS? THIS IS PART OF THE SPEC?"* |
| Calling polish a v1 release | *"How in the FUCK do you consider this to be a V1? This is at a 0.0.10 level."* |
| Misattributing decisions to the user | *"I did not name the acquisition memo as the canonical example. You decided that on context."* |
| Asking trust questions when behavior should answer | *"How can I turst that you have the discipline to follow through?"* |

### Feedback memories saved (read these)

Located at `/Users/ethanallen/.claude/projects/-Users-ethanallen-SDLC-assesment/memory/`:

- `feedback_attribution.md` — distinguish my context inferences from user directives
- `feedback_persona_voice.md` — persona means contextualized analysis, not relabeled scaffolding
- `feedback_version_naming.md` — don't call polish releases v1
- `feedback_provenance.md` — reports must name their subject (project + URL + commit SHA + scan timestamp)
- `feedback_directive_drift.md` — treat directives as contracts, not phrases
- `feedback_no_memory_for_standards.md` — never default to memory for industry-standard values
- `feedback_no_half_measures.md` — when swapping a substrate, remove the old; don't add alongside
- `feedback_audit_before_add.md` — directive-driven work is removal-then-add, with grep audit visible in chat
- `feedback_trust_through_behavior.md` — paste audit, commit removals before additions, grep output before claiming done

The index is at `MEMORY.md` in the same directory. **Read these before writing code.**

---

## 7. The plan file

Located at `/Users/ethanallen/.claude/plans/users-ethanallen-downloads-sdlcasses-ac-vivid-shamir.md`. The plan has been overwritten multiple times as scope evolved. The current relevant content:

- The **RSF cutover verification run** (top of file) describes the AgentSentry verification that already happened.
- The **framework-anchoring plan + provenance + persona artifacts (parallel)** section below describes the remaining workstreams.
- **Workstream A (Provenance)** is DONE.
- **Workstream B (Framework anchoring)** is partially done: RSF codified ✓, criteria + personas + aggregation done ✓, scorers done for 14/31 ✗ for 17/31. The detector-pipeline expansion that would close the 17 `?`s is not started.
- **Workstream C (Per-persona artifacts)** is NOT started. The current persona builders use the same engineering content with vocabulary swaps — not the persona-distinct artifacts the plan describes (license-compliance matrix for acquisition, claim ingestion for VC, DORA dashboard for engineering, JSON manifest for remediation).

---

## 8. Immediate next work — in priority order

The user's last unresolved question was: *"Want me to plan that work now (it's multi-day) or land what's in flight first?"* — they didn't answer. **Default to landing what's in flight, then ask before starting multi-day workstreams.**

### Before anything else: confirm the working tree state

```bash
git status
git log --oneline -10
.venv-sdlc/bin/pytest -q
```

Expected: clean working tree, head at `33bffd8`, 388+ tests passing.

### Priority 1 — Persona-contextual translation (in flight per the todo list)

The todo currently in_progress is *"Persona-contextual translation of RSF top-5 findings: VC reads investment language; C-level reads liability; eng reads sprint; agent reads imperative."*

What's needed: when the RSF block surfaces a top-5 lowest-scored sub-criterion (e.g., D2.2 = 0 "Active secrets discoverable"), the persona body should translate it into the persona's frame:

- **VC**: "Active secrets in source code → pre-term-sheet founder Q&A; valuation-discount candidate; falls under OWASP ASVS V2 / NIST SSDF PS.5"
- **Acquisition (PE/M&A)**: "Inherited secrets exposure → escrow condition or seller-funded rotation; inherited GDPR Art. 32 / CCPA liability"
- **Engineering**: "Phase-1 sprint must-ship: rotate secrets + deploy gitleaks pre-commit hook + add `.github/secret_scanning.yml`"
- **Remediation agent**: "Task: rotate exposed credentials; verify with `git filter-repo --invert-paths`; idempotency check `git grep -nE 'AKIA|sk_live'`"

Implementation: extend `sdlc_assessor/renderer/deliverables/{acquisition,vc,engineering,remediation}.py` with a `_persona_translation_section(scored, deliverable)` that pulls top-5 from `scored["rsf"]["dimensions"][*]["criteria"][*]` (where value is int, sorted ascending) and emits persona-specific consequence text per criterion. Render the section in the deliverable HTML between the RSF block and the existing chart sections.

### Priority 2 — Detector-pipeline expansion (the substantive gap)

Each of these closes 1–4 `?` slots:

1. **OSV-Scanner adapter** (`sdlc_assessor/detectors/sast/osv_adapter.py`). Reads `package-lock.json` / `poetry.lock` / `Cargo.lock` / etc.; runs `osv-scanner --format=json` if installed; emits findings with CVE IDs. Closes D2.1 (CVE) and feeds D3.4 (dep-update with reachability).
2. **Wire SAST findings into D1.2 / D2.3 scoring.** The 5 SAST adapters at `sdlc_assessor/detectors/sast/{semgrep,bandit,eslint,ruff,cargo_audit}_adapter.py` already emit findings into the legacy `findings` array. The RSF D1.2 / D2.3 scorers don't currently inspect those findings — they only check for workflow YAML mentions. Update `score_d1_2` / `score_d2_3` in `sdlc_assessor/rsf/scorers.py` to count SAST findings by severity and map to RSF level anchors.
3. **GitHub API adapter** (NEW `sdlc_assessor/detectors/github/`). Read-only API calls for: branch protection rules (closes D2.4), PR review history (closes D5.1), issue/PR responsiveness (closes D7.3). Requires `GITHUB_TOKEN` env var; gate gracefully when absent. Use the `gh` CLI shelled-out if available, or `requests` with PAT.
4. **DORA history walk** (extend `sdlc_assessor/detectors/git_history.py`). Walk merge commits + tags + GitHub deployment events to compute deployment frequency, lead time. Some metrics need CI run history (GitHub Actions API). Closes D4.1, D4.2, partially D4.3.
5. **SBOM generation** (NEW `sdlc_assessor/detectors/sbom_adapter.py`). Shell out to `syft` / `cyclonedx-py` if installed; generate CycloneDX JSON; emit as detector output. Closes D3.1 above the file-presence check.
6. **Real coverage analysis** (NEW). Read `coverage.xml` / `coverage.json` / `lcov.info` if present; extract line + branch coverage. Closes D1.1 above level 1.

Each item is 1–3 days of work. **Wire each into the RSF scorer and add a test that asserts the new evidence flows through to the right RSF level**, otherwise you'll hit the same trap I did (SAST built but not wired to RSF).

### Priority 3 — Persona-distinct artifacts (not just vocabulary)

The plan calls these out:

- **Acquisition**: license-compliance matrix (SPDX scan via `scancode-toolkit` or `licensee`); CODEOWNERS bus-factor analysis; integration-cost ladder against named house stacks; CVE register with CVSS scores.
- **VC**: pitch-claims ingestion (`sdlc claims add ./pitch.md` CLI); claim × evidence substantiation table replacing auto-derived placeholders; founder shipping cadence visualization.
- **Engineering**: DORA dashboard (depends on Priority 2 #4); CWE Top 25 coverage map (depends on Priority 2 #1); on-call delta per finding.
- **Remediation**: machine-readable JSON manifest as primary artifact; per-task patch anchors + idempotency checks.

Each persona is 3–5 days. The plan file lays out the file ownership.

### Priority 4 — Calibration corpus + outcome data

The user picked "industry-quality v1" which requires:

- A real outcome-linked corpus (≥50 entries, ideally) of real codebases with known M&A / VC / engineering outcomes — for backtesting the recommendation engine. **You cannot build this; the user must source it.**
- Persona-user research interviews (≥6 per persona × 4 personas, minimum) — for validating the persona body shapes against what real reviewers want. **Same — user-action gated.**
- Methodology peer review (≥2 external reviewers) — for the framework writeup. **User-action gated.**

These are explicitly in the plan file as user-action items. **Don't try to fake them.**

---

## 9. Things you should NOT do

- **Do not invent numeric values.** If the RSF says level 3 anchor is "Line coverage 50–70%", that's the spec. Do not make up a different threshold because it's convenient.
- **Do not add a section without removing what it replaces.** Grep first.
- **Do not call polish releases v1.** v1 has a calibration corpus + persona research + peer review backing it. We don't have those.
- **Do not skip user-action items.** When the plan calls out external dependencies (corpus partnerships, peer reviewers), name them explicitly and ask the user before assuming they're done.
- **Do not minimize the gap.** When the assessor scores 5% across all personas, that means the assessor isn't measuring enough. Don't dress up low scores with persona-flavored prose.
- **Do not pretend the SAST adapters give the report a real SAST integration.** They run if the tool is installed, but their findings don't currently reach the RSF scorers. Until you wire them, the assessor doesn't actually do SAST in any way that affects the score.
- **Do not write a feedback memory in lieu of doing the work.** The memory documents the failure; the work fixes it. Memories without behavior changes compound the problem.

---

## 10. Verification commands

```bash
# Working tree state
git status
git log --oneline -10
.venv-sdlc/bin/pytest -q  # expect 388+ passed

# Render against this repo
rm -rf /tmp/self_handoff
.venv-sdlc/bin/python -m sdlc_assessor.cli run . --use-case acquisition_diligence --format html --out-dir /tmp/self_handoff
.venv-sdlc/bin/python -c "
import json
s = json.load(open('/tmp/self_handoff/scored.json'))
print('overall_score (legacy):', s['scoring']['overall_score'])
print('rsf framework_version:', s['rsf']['framework_version'])
print('rsf personas:', [(p['persona_label'], round(p['total_pct'], 1)) for p in s['rsf']['personas']])
print('rsf real-scored:', sum(1 for d in s['rsf']['dimensions'] for c in d['criteria'] if isinstance(c['value'], int)), 'of 31')
"

# Render against AgentSentry (cloned to /tmp/AgentSentry already; refresh if stale)
test -d /tmp/AgentSentry || git clone --depth 50 https://github.com/calabamatex/AgentSentry /tmp/AgentSentry
.venv-sdlc/bin/python -m sdlc_assessor.cli run /tmp/AgentSentry --use-case vc_diligence --format html --out-dir /tmp/sentry_handoff

# Trust-mechanism: confirm legacy substrate is gone
for phrase in \
  "pass_threshold" \
  "diligence bar" \
  "use_case_profiles.json" \
  "SEVERITY_WEIGHTS" \
  "score-decomposition" \
  "gap-analysis"; do
  count=$(grep -c "$phrase" /tmp/self_handoff/report.html /tmp/sentry_handoff/report.html 2>/dev/null | awk -F: '{s+=$NF} END {print s}')
  echo "  [$count] $phrase"
done
# Expect: all zeros.
```

---

## 11. Useful file map

```
sdlc_assessor/
├── classifier/engine.py                 # Archetype/maturity/network detection
├── collector/engine.py                  # Top-level evidence collection
├── detectors/
│   ├── common.py                        # Shared file-walking helpers
│   ├── git_history.py                   # git_summary collector (recently extended)
│   ├── python_pack.py                   # AST-based Python detectors
│   ├── tsjs_pack.py                     # TS/JS detectors
│   ├── treesitter/                      # Multi-language AST via tree-sitter
│   ├── registry.py                      # Detector dispatch (line 52: SAST runs here)
│   └── sast/                            # SAST adapters (NOT wired to RSF yet)
│       ├── semgrep_adapter.py
│       ├── bandit_adapter.py
│       ├── ruff_adapter.py
│       ├── eslint_adapter.py
│       ├── cargo_audit_adapter.py
│       └── framework.py                 # Adapter registry
├── normalizer/
│   ├── findings.py                      # Finding normalization + fixture tagging
│   └── dedupe.py                        # Cross-detector dedupe
├── scorer/
│   ├── engine.py                        # LEGACY scoring engine (still runs for back-compat)
│   ├── blockers.py                      # Hard-blocker detection
│   └── precedence.py                    # Profile merge order
├── rsf/                                 # *** RSF v1.0 ***
│   ├── __init__.py
│   ├── criteria.py                      # 31 sub-criteria, 8 dimensions (verbatim from doc)
│   ├── personas.py                      # 8 personas + weight matrix (verbatim)
│   ├── aggregate.py                     # D_i / T / T_% formulas + confidence flagging
│   ├── scorers.py                       # 31 per-criterion scorers (14 real, 17 ?)
│   └── score.py                         # Top-level assess_repository entry
├── remediation/
│   ├── planner.py                       # Generates remediation tasks
│   └── markdown.py                      # Renders remediation as Markdown
├── renderer/
│   ├── markdown.py                      # Legacy Markdown report
│   ├── html.py                          # Legacy v0.9.0 HTML (still callable)
│   ├── deliverable_html.py              # *** Current HTML renderer ***
│   ├── persona.py                       # Persona narrative-block dispatch
│   ├── narrative_blocks.py              # Per-emphasis block builders
│   └── deliverables/                    # *** Persona-distinct deliverable framework ***
│       ├── base.py                      # Deliverable + supporting dataclasses
│       ├── acquisition.py
│       ├── vc.py
│       ├── engineering.py
│       ├── remediation.py
│       ├── _vocab.py                    # Per-persona axis labels / chart labels
│       ├── _provenance.py               # ProvenanceHeader collector
│       ├── _exec_summary.py             # RSF-grounded executive summary
│       ├── _methodology.py              # Methodology box + glossary registry
│       ├── _citations.py                # CitationRegistry for footnote markers
│       ├── _integrate.py                # apply_depth_pass() — glue layer
│       ├── charts/                      # Pure-Python SVG chart primitives
│       └── (legacy: _decomposition.py, _gap.py — no longer rendered)
├── profiles/data/
│   ├── use_case_profiles.json           # 4 use_case profiles (still uses legacy fields)
│   ├── maturity_profiles.json
│   └── repo_type_profiles.json
└── cli.py                               # `sdlc` CLI entry

docs/
├── frameworks/
│   ├── rsf_v1.0.md                      # *** CANONICAL FRAMEWORK ***
│   ├── cwe_cvss.md                      # Background research (committed earlier)
│   └── dora.md                          # Background research (committed earlier)
├── ANALYSIS.md                          # Original gap analysis
├── ACTION_PLAN.md                       # Original SDLC-001..035 plan
├── SDLC_Framework_v2_Spec.md            # Original spec
├── scoring_engine_spec.md               # Legacy scoring engine spec
├── calibration_targets.md
└── HANDOFF.md                           # *** This file ***

tests/
├── unit/
│   ├── test_rsf_framework.py            # RSF framework integrity (21 tests)
│   ├── test_rsf_scorers.py              # Per-criterion scorer tests (44 tests)
│   ├── test_methodology.py              # Methodology box + glossary
│   ├── test_deliverable_depth.py        # Integration: render + grep
│   ├── test_charts.py                   # SVG chart primitives
│   └── (~20 other test files for legacy + classifier + detectors + scorer)
├── golden/
│   └── test_report_render.py            # Markdown rendering golden tests
└── fixtures/                            # Test fixtures by archetype
```

---

## 12. Pending todos at handoff

```
[completed] Fix sticky-banner transparency
[completed] Fix duplicate persona-paragraph bug
[completed] Rip out legacy threshold language across renderer + builders
[completed] Run RSF assessor on /tmp/AgentSentry; grep for legacy phrases
[in_progress] Persona-contextual translation of RSF top-5 findings
[pending] Bump version + CHANGELOG + PR + CI + merge + tag
```

The "persona-contextual translation" todo is the next user-visible deliverable and the user asked for it explicitly. Do not skip to release until that lands AND the user has reviewed.

---

## 13. One-paragraph summary

This is a repository-scoring tool that recently underwent a substrate cutover from a self-authored 0–100 rubric to the user-provided **RSF v1.0** industry-anchored framework. The framework is correctly codified; the per-criterion scorers are correctly written for 14 of 31 sub-criteria. The remaining 17 return `?` because the detector pipeline doesn't collect the evidence those criteria need. Persona-distinct rendering exists at the cover/exec-summary layer; persona-distinct *body* artifacts (license matrices, pitch ingestion, DORA dashboards, JSON manifests) do not. The user's next-priority ask is persona-contextual translation of RSF top-5 findings into each reader's lens. The substantive gap is detector-pipeline expansion (OSV scanner, GitHub API integration, DORA history walker, SBOM generation, real coverage analysis) — multi-day work each, gated on the user's priority decision. Trust has been damaged in this branch; rebuild it by showing audit-before-code, removals-before-additions, and grep-before-claiming-done. The user is paying attention; they will catch shortcuts. Read `docs/frameworks/rsf_v1.0.md` and the feedback-memory files in `~/.claude/projects/-Users-ethanallen-SDLC-assesment/memory/` before writing code.

---

**End of handoff.**
