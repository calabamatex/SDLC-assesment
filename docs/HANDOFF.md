# Handoff: SDLC-assesment / `feat/v0.10.0-persona-deliverables` branch

You are picking up an in-progress repository-scoring tool. The user (Ethan Allen / GitHub `calabamatex`) is frustrated with the prior session's pattern of half-measures and surface-level work. **This document is the unfiltered state-of-play.** Read it end-to-end before writing any code. It is long because the project state is genuinely complex and the user has explicitly asked for comprehensive, exhaustive, honest, objective.

> **Critical paths to read first, in order:**
> 1. `docs/frameworks/rsf_v1.0.md` — canonical scoring framework (user-provided)
> 2. `~/.claude/projects/-Users-ethanallen-SDLC-assesment/memory/MEMORY.md` and the 9 feedback-memory files it indexes
> 3. `~/.claude/plans/users-ethanallen-downloads-sdlcasses-ac-vivid-shamir.md` — current plan file (overwritten multiple times this session)
> 4. This document
> 5. `docs/ANALYSIS.md` and `docs/ACTION_PLAN.md` — the *original* spec the user supplied at session start (now partially superseded by RSF; see §16)

---

## 0. Table of contents

1. [Who the user is and what they want](#1-who-the-user-is-and-what-they-want)
2. [Project state at handoff](#2-project-state-at-handoff)
3. [Session chronology — how we got here](#3-session-chronology--how-we-got-here)
4. [What the assessor *does* (objectively)](#4-what-the-assessor-does-objectively)
5. [The pipeline data flow + every artifact emitted](#5-the-pipeline-data-flow--every-artifact-emitted)
6. [CLI subcommand reference](#6-cli-subcommand-reference)
7. [The RSF v1.0 framework](#7-the-rsf-v10-framework)
8. [What is *actually measured* vs unverified](#8-what-is-actually-measured-vs-unverified)
9. [Detector inventory](#9-detector-inventory)
10. [Subcategory taxonomy](#10-subcategory-taxonomy)
11. [Profile system](#11-profile-system-use_case--maturity--repo_type-merge)
12. [Profile signing infrastructure](#12-profile-signing-infrastructure)
13. [LLM narrator + dual-narrator flag](#13-llm-narrator--dual-narrator-flag)
14. [Compare mode](#14-compare-mode)
15. [Test fixtures](#15-test-fixtures)
16. [Stale code / spec-doc staleness](#16-stale-code--spec-doc-staleness)
17. [Speculative values still in code](#17-speculative-values-still-in-code)
18. [External tool dependencies + version pins](#18-external-tool-dependencies--version-pins)
19. [Background-agent state from this session](#19-background-agent-state-from-this-session)
20. [User's working style and red lines](#20-users-working-style-and-red-lines)
21. [The 9 feedback memories](#21-the-9-feedback-memories-saved-this-session)
22. [The plan file](#22-the-plan-file)
23. [Immediate next work in priority order](#23-immediate-next-work-in-priority-order)
24. [Things you should NOT do](#24-things-you-should-not-do)
25. [Verification commands](#25-verification-commands)
26. [Code conventions used in the project](#26-code-conventions-used-in-the-project)
27. [File map](#27-file-map)
28. [Glossary of project-specific terms](#28-glossary-of-project-specific-terms)
29. [Pending todos at handoff](#29-pending-todos-at-handoff)
30. [One-paragraph summary](#30-one-paragraph-summary)

---

## 1. Who the user is and what they want

**Identity**: Ethan Allen, GitHub handle `calabamatex`. License/copyright holder for the project. Email is the user-context email — they want their public name on the project, not a generic placeholder.

**What they're building**: A diligence-grade repository assessor — a CLI tool that ingests a Git repo and produces persona-aware reports for VC, M&A, engineering, CISO, procurement, and other consumer roles.

**Stated v1 bar**: **Industry-quality (sellable / open-source-shippable as a serious tool).** The user explicitly chose this bar after rejecting "personal-quality" and "firm-quality" alternatives mid-session.

**Hard requirements** the user has stated:

- Every numeric scoring constant must be anchored to a published industry framework, not invented.
- Reports must read as defensible diligence documents — not "engineering bug lists."
- Persona-specific output means *different content*, not the same engineering analysis with relabeled sections.
- "Half measures" — adding new while keeping legacy in place — are a primary failure mode.
- The user provided the **Repository Scoring Framework v1.0** as the canonical scoring rubric. It supersedes the original self-authored rubric in `ACTION_PLAN.md` / `scoring_engine_spec.md`.

**The user has caught the prior session in failure patterns multiple times**. They will catch you too if you repeat them. §20 names the patterns.

---

## 2. Project state at handoff

### Branch + commits

```
Branch:   feat/v0.10.0-persona-deliverables
Latest:   d34ac7c docs(handoff): comprehensive handoff document for next session
HEAD~1:   33bffd8 fix(rsf): use the rich evidence already in git_summary
```

The branch is **NOT yet merged to `main`**. Do not cut a release until the work in §23 is honestly done and the user has reviewed.

### Recent commits (newest first, this session's work)

| SHA | Title |
|---|---|
| `d34ac7c` | docs(handoff): comprehensive handoff document |
| `33bffd8` | fix(rsf): use rich evidence in git_summary for D5.4/D7.1/D7.2/D7.4 |
| `b803e7a` | refactor(deliverables): rip out legacy made-up rubric |
| `e065581` | feat(rsf): per-criterion scorers + CLI wiring + HTML render |
| `559fce4` | feat(rsf): codify RSF v1.0 as canonical scoring framework |
| `8f11d0f` | docs(frameworks): CWE Top 25 + DORA anchor research |
| `a7e6b55` | feat(deliverables): provenance header |
| `6a0d081` | fix(deliverables): commit lost _vocab.py + matrix.py |
| `f5972cc` | test(deliverables): integration tests + persona-distinct exec summaries |
| `07ee506` | feat(renderer): surface depth-pass content in HTML |
| `c31d84f` | feat(deliverables): wire depth pass into 4 builders |
| `4ee76a2` | feat(deliverables): citation registry for footnotes |
| `7690224` | feat(deliverables): grounded methodology + glossary registry |
| `94c54a7` | feat(deliverables): real score-decomposition builder |
| `d67c22f` | feat(deliverables): extend Deliverable for 0.11.0 depth pass |
| `4cb6512` | feat(renderer): persona-distinct deliverable framework + 4 builders |
| `9157358` | feat(renderer): SVG chart primitives |

### Version + python

- `__version__` = `"0.9.0"` (in `sdlc_assessor/__init__.py` and `pyproject.toml`).
- The branch name says `v0.10.0` but the version field has not been bumped. **The 0.11.0 RSF cutover work is also unbumped.**
- Python 3.12 (per `pyproject.toml`).
- Virtualenv: `.venv-sdlc/` at the repo root. `.venv-sdlc/bin/pytest` is what the user expects.

### Test status

`387 passed, 1 skipped` as of the last full-suite run before the handoff doc was written. Includes RSF framework integrity tests (21), per-criterion scorer tests (44), methodology + glossary tests, integration tests against a fixture, and the legacy v0.8/0.9 tests.

---

## 3. Session chronology — how we got here

This is the most important context for understanding *why* the codebase looks the way it does. The session went through several distinct phases driven by user critiques. Each phase produced commits; some were later partially undone or reframed.

### Phase 1: v0.2.0 → v0.9.0 — original spec execution

Session opened with the user pointing at `docs/ACTION_PLAN.md` and `docs/ANALYSIS.md` as the spec. That document defined SDLC-001 through SDLC-035 across Phases 1–7, with Phase 8 listed as "post-v1 backlog" (real SAST integration, OSV scanning, SBOM generation, language packs for Go/Rust/Java/C#/Kotlin, etc.). User scope decision: Phase 1–7 only; Phase 8 stays in backlog.

This phase shipped versions 0.2.0 → 0.9.0 via tag-pushes. The 0.9.0 release notes (in `CHANGELOG.md`) describe persona-aware reports + fixture-finding segregation under SDLC-067..070. User explicitly approved each minor version.

Mid-phase, user said *"SAST intergation -- proceed"* — that's how the 5 SAST adapters at `sdlc_assessor/detectors/sast/` got built. Critical caveat: those adapters were built but **never wired into the new RSF scorers**. Their findings flow into the legacy `findings` array; the RSF D1.2 / D2.3 scorers don't read them.

The user also said *"LAngauge oacks are important as it differentiteas the repo"* and approved adding Go, Rust, Java, C#, Kotlin tree-sitter packs. Those are at `sdlc_assessor/detectors/treesitter/`.

### Phase 2: v0.9.0 → v0.10.0 (current branch) — persona deliverables

User reviewed the v0.9.0 HTML report and rejected it as engineering-flavored and visually weak: *"why in the FUCK are there TODO in the code? There were explcit directives never to have placehodlers."* (the user found `# TODO` comments left in code). Then on review of the persona handling: *"reads like a bug list, not an actual buiness based perspective with recommendations."*

This kicked off a comprehensive rebuild of the deliverable layer:

- **Chart primitives** (SDLC-072): 5 SVG chart functions (gauge, radar, risk matrix, effort×impact, score-lift trajectory). Pure Python, no external deps. Tests: `tests/unit/test_charts.py`.
- **Persona-distinct framework** (SDLC-073): `sdlc_assessor/renderer/deliverables/base.py` with `Deliverable`, `CoverPage`, `Section`, `Recommendation` dataclasses + dispatcher.
- **Four persona builders** (SDLC-074..077): `acquisition.py` (memo), `vc.py` (thesis evaluation), `engineering.py` (health report), `remediation.py` (action plan).
- **Modern HTML layout** (SDLC-079): `deliverable_html.py` with cover sheet, recommendation pill, body sections, recommendation block, engineering appendix.
- **Persona vocabulary** (later): `_vocab.py` with per-persona axis labels, category labels, quadrant labels, chart titles. This was the persona-flavored-vocabulary pass user later rejected as "1 or 2 paragraphs of relabeling."

User then critiqued the depth: *"You just reused the same exact info, with the same exact analysis, and just wrapped each report with a persona perspective in 1 or 2 paragraphs."* This led to the **0.11.0 depth pass**: methodology box, glossary, citations, score decomposition, gap analysis, executive summary as prose. User said this was "1/2 measures" — adding new without removing legacy.

User then escalated: *"How in the FUCK do you consider this to be a V1?"* The session paused, plan-mode was re-entered, and the v1.0 bar was renegotiated to "industry-quality."

### Phase 3: Industry-quality v1 framing → RSF cutover

User pointed out that every scoring constant is invented: *"Appears you have made up your own scoring matrix, with nothing other than 'trust me bro' to back up your claims."* Plan-mode session produced a 6-option framework analysis (NIST SSDF + DORA + CWE/CVSS + SLSA + ISO 25010 + CHAOSS, etc.). User chose **Hybrid (Option D)**.

Mid-research-agent runs (NIST SSDF / DORA / CWE-CVSS), the user provided the **Repository Scoring Framework v1.0** as their own canonical framework. This superseded the Option-D hybrid choice. RSF v1.0 was saved verbatim to `docs/frameworks/rsf_v1.0.md` and codified into `sdlc_assessor/rsf/`:

- 8 dimensions, 31 sub-criteria, 6 level anchors per criterion (verbatim from doc).
- 8 personas with weight matrix (verbatim).
- Aggregation per RSF §4 (D_i mean, T = Σ D_i × w_i, T_% = T/500 × 100).
- 31 per-criterion scorers — 14 score against real anchors, 17 return `?` (RSF-correct disclosure of unverified evidence).

### Phase 4: User reviewed RSF reports → flagged half-measures

User reviewed the AgentSentry RSF report and called out:
- Sticky-banner transparency (text bleeding through when scrolling)
- Duplicate "Documentation track-record is solid" paragraph
- Legacy `pass_threshold 72` language still in cover rationale despite the RSF cutover

The fix landed in commit `b803e7a` (refactor: rip out legacy substrate; grep proof shows 0/9 legacy phrases in rendered output).

### Phase 5: User asked "how can the scores be the same?" → detector pipeline gap

User compared scores between AgentSentry and this repo and saw nearly-identical totals. Investigation revealed:
- 11/31 sub-criteria scored against real anchors; 20/31 `?` (treated as 0 in math)
- The 11 real anchors fired identically because both repos genuinely have the same observable deficits
- 3 detector bugs were under-scoring this repo: D7.1 ignored `top_authors` share (94% vs 47%), D7.2 ignored `commits_last_*_days` (real cadence signal), D5.4 ignored `tag_count` entirely

Fix landed in commit `33bffd8`. Real differentiation now visible: AgentSentry persona totals 24-38% relatively higher.

User then pointed at the deeper problem: *"There is no SAST. No OSV/CVE scan. No actual SBOM generation. No call graph. No complexity analysis. No dead-code detection..."* and asked **"WHY DID YOU SKIP ALL THIS? THIS IS PART OF THE SPEC?"** Honest answer: the original `ACTION_PLAN.md` put those in Phase 8 backlog and user signed off on Phase 1-7 scope, but when scope shifted to "industry-quality v1" mid-session, those backlog items should have been re-promoted and weren't.

User then asked *"How can I trust that you have the discipline to follow through?"* — leading to the **trust-mechanism** discipline (audit before code, removals before additions, grep before claiming done).

### Phase 6: Handoff requested

User asked for a comprehensive, exhaustive, honest, objective handoff. First version was insufficient. This document is the second.

---

## 4. What the assessor *does* (objectively)

The CLI is `python -m sdlc_assessor.cli` (or `sdlc` after `pip install -e .`). The pipeline:

1. **Classify** the repo (`sdlc_assessor/classifier/engine.py`): walks files, picks an archetype (`service` / `monorepo` / `library` / `cli` / `internal_tool` / `research_repo` / `infrastructure` / `unknown`), maturity (`production` / `prototype` / `research` / `unknown`), network exposure, deployment surface, release surface, classification confidence (0.0–1.0).
2. **Collect evidence** (`sdlc_assessor/collector/engine.py` + `sdlc_assessor/detectors/*`): runs all detectors, normalizes findings, dedupes via cross-detector family map, segregates fixture findings.
3. **Score** (`sdlc_assessor/scorer/engine.py`) — **legacy 0–100 scoring engine**, kept for back-compat. Outputs `scoring.overall_score` and `scoring.verdict`. The deliverable layer no longer reads this for primary scoring.
4. **RSF v1.0 assessment** (`sdlc_assessor/rsf/`) — **new canonical scoring**. Reads scored payload + repo path, produces `RSFAssessment` with per-dimension scores (0–5), per-persona weighted totals (0–100%), and confidence flagging. Attached to `scored.json` as `scored["rsf"]`.
5. **Remediation plan** (`sdlc_assessor/remediation/planner.py`): generates fix tasks; output attached to `scored["remediation_plan"]` and rendered to `remediation.md`.
6. **Render** (`sdlc_assessor/renderer/deliverable_html.py` + `sdlc_assessor/renderer/deliverables/`): produces persona-distinct HTML reports for one of four use-cases.

Markdown rendering and the legacy v0.9.0 HTML renderer (`sdlc_assessor/renderer/html.py`) still exist and are still callable but are no longer the primary output path. See §16 for the cleanup status.

---

## 5. The pipeline data flow + every artifact emitted

`sdlc run <repo_target>` writes the following files to `--out-dir` (default `./.sdlc/`):

| File | Producer | Contents |
|---|---|---|
| `classification.json` | classifier/engine.py | `{classification: {...}, repo_meta: {git_summary, ...}}` |
| `evidence.json` | collector/engine.py | `{classification, repo_meta, inventory, findings[]}` |
| `scored.json` | scorer/engine.py + rsf/score.py + planner.py | All of evidence + `{scoring, hard_blockers, remediation_plan, rsf}` |
| `report.md` | renderer/markdown.py | Legacy Markdown report (still rendered) |
| `report.html` | renderer/deliverable_html.py | RSF-grounded persona-distinct HTML (the primary deliverable) |
| `remediation.md` | remediation/markdown.py | Markdown remediation plan |

Schema for `scored.json` (top-level keys after the full pipeline):

```
{
  "repo_meta": {
    "name": str,
    "default_branch": str,
    "git_summary": {
      "commits_analyzed": int,
      "signed_commit_count": int,
      "signing_coverage": float,
      "bus_factor": int,
      "top_authors": [{"name": str, "commit_count": int, "share": float}],
      "codeowners_present": bool,
      "codeowners_coverage": float,
      "tag_count": int,                  # added in 33bffd8
      "commits_last_30_days": int,       # added in 33bffd8
      "commits_last_90_days": int,       # added in 33bffd8
      "commits_last_180_days": int,      # added in 33bffd8
      "commits_last_365_days": int       # added in 33bffd8
    }
  },
  "classification": {
    "repo_archetype": str,
    "maturity_profile": str,
    "deployment_surface": str,
    "network_exposure": bool,
    "release_surface": str,
    "classification_confidence": float,
    "rationale": [str, ...]              # signal trail
  },
  "inventory": {
    "source_files": int, "source_loc": int,
    "test_files": int, "estimated_test_cases": int,
    "test_to_source_ratio": float,
    "workflow_files": int, "workflow_jobs": int,
    "runtime_dependencies": int, "dev_dependencies": int,
    "commit_count": int, "tag_count": int, "release_count": int
  },
  "findings": [
    {
      "id": "F-NNNN",
      "category": str,                   # one of 8 BASE_WEIGHTS keys
      "subcategory": str,                 # see §10
      "severity": "info"|"low"|"medium"|"high"|"critical",
      "confidence": "low"|"medium"|"high",
      "statement": str,
      "evidence": [{"path", "line_start", "line_end", "snippet", "match_type", "count"}],
      "score_impact": {"direction": "negative"|"positive", "magnitude": int (0..10), "rationale": str},
      "tags": ["source:test_fixture"|"source:vendor"|...]   # path-class tags from SDLC-067
    }
  ],
  "scoring": {                            # LEGACY scoring engine output
    "effective_profile": {"use_case", "maturity", "repo_type"},
    "base_weights": {category: int},
    "applied_weights": {category: float},
    "category_scores": [{category, applicable, score, max_score, summary, key_findings}],
    "overall_score": int,
    "overall_score_precise": float,
    "verdict": "pass_with_distinction"|"pass"|"conditional_pass"|"fail",
    "score_confidence": "low"|"medium"|"high",
    "blocker_impact": {"critical_count", "high_count"},
    "flat_penalty_applied": int
  },
  "hard_blockers": [{"severity", "title", "reason", "closure_requirements", "linked_finding_ids"}],
  "remediation_plan": {
    "tasks": [{
      "id", "phase", "subcategory", "title",
      "change_type": [str, ...],
      "target_paths": [str, ...],
      "anchor_guidance": str,
      "implementation_steps": [str, ...],
      "verification_commands": [str, ...],
      "effort": "S"|"M"|"L"|"XL",
      "expected_score_delta": float,
      "linked_finding_ids": [str]
    }]
  },
  "rsf": {                                 # NEW canonical scoring (RSF v1.0)
    "framework_version": "v1.0",
    "dimensions": [{
      "dimension_id": "D1".."D8",
      "title": str,
      "mean": float|null,                  # null if every sub-criterion is N/A
      "n_scored": int,
      "n_unverified": int,
      "n_total": int,
      "confidence_flagged": bool,
      "criteria": [{
        "criterion_id": "Dx.y",
        "value": int (0..5) | "N/A" | "?",
        "evidence": [str, ...],
        "rationale": str
      }]
    }],
    "personas": [{
      "persona_id": "vc"|"pe_ma"|"cto_vp_eng"|"eng_mgr"|"ciso"|"procurement"|"oss_user"|"c_level_non_tech",
      "persona_label": str,
      "weights_used": {dim_id: int},        # may differ from base if N/A redistributed
      "total": float,                        # 0..500
      "total_pct": float,                    # 0..100
      "confidence_flagged": bool,
      "limited_confidence_warning": bool     # >25% weight on flagged dims
    }],
    "na_dimensions": [str],
    "flagged_dimensions": [str]
  }
}
```

---

## 6. CLI subcommand reference

All subcommands run through `python -m sdlc_assessor.cli <subcommand>`.

### `classify <repo_target>`
Outputs `classification.json`. No scoring.

### `collect <repo_target> --classification <path>`
Outputs `evidence.json`. Runs detectors against the repo, takes the classification JSON as input.

### `score <evidence_path> --use-case <name> [--maturity X] [--repo-type Y] [--narrate-with-llm]`
Reads evidence, runs the legacy scorer + remediation planner. **Does NOT currently run the RSF scorer** — RSF only runs in the `run` subcommand. (This is a gap; the next session may want to wire RSF into `score` as well.)

### `render <scored_path> [--format markdown|html|both]`
Renders a single report from a scored.json. Calls the legacy renderer or the new deliverable HTML renderer based on format. Same gap: doesn't run RSF if scored.json doesn't already have `rsf`.

### `remediate <scored_path> [--out path]`
Generates `remediation.md` from a scored.json.

### `run <repo_target> --use-case <name> [flags]` ★ primary entrypoint
Full pipeline: classify → collect → score → remediation → RSF → render. Writes all artifacts to `--out-dir`.

Flags (all on `run`):
- `--use-case` (required): one of `acquisition_diligence`, `vc_diligence`, `engineering_triage`, `remediation_agent`. **These are the legacy 4 use_case profiles. The 8 RSF personas (`vc`, `pe_ma`, `cto_vp_eng`, `eng_mgr`, `ciso`, `procurement`, `oss_user`, `c_level_non_tech`) are computed from the matrix in `rsf/personas.py` regardless of which use_case is selected — every report shows all 8 RSF persona totals.**
- `--maturity`, `--repo-type`: optional overrides for classifier output.
- `--policy`: optional policy JSON path.
- `--out-dir`: default `./.sdlc/`.
- `--format`: `markdown` | `html` | `both` (default `markdown`).
- `--narrator`: `deterministic` (default) | `llm` | `both`. See §13.
- `--narrate-with-llm`: legacy boolean (replaces deterministic per-category summaries with LLM narration; predates the `--narrator` flag).
- `--llm-model`: Anthropic model id (default `claude-haiku-4-5-20251001`).
- `--repo-name`, `--repo-url`: provenance overrides for the report banner.
- `--d8-not-applicable`: marks RSF D8 (compliance) sub-criteria as `N/A` instead of `?`. Use when the asset is genuinely out of compliance scope.

### `compare <repo_a> <repo_b> --use-case <name>`
Two-repo comparison. Runs the pipeline against each, then emits a Markdown delta report at `<out-dir>/comparison.md` and a JSON artifact at `<out-dir>/comparison.json`. See §14.

---

## 7. The RSF v1.0 framework

The user provided **Repository Scoring Framework (RSF) v1.0** as the canonical industry-anchored framework. Verbatim copy at `docs/frameworks/rsf_v1.0.md`. Source of truth for every scoring decision.

**8 dimensions** (D1–D8): Code Quality, App Security, Supply Chain, Delivery, Engineering Discipline, Documentation, Sustainability, Compliance.

**31 sub-criteria** (D1.1–D8.4), each with 6 level anchors (0–5):

| Score | Label | Meaning |
|---|---|---|
| 0 | Absent | No evidence of the practice. Critical gap. |
| 1 | Ad hoc | Practice exists in pockets; no enforcement; not repeatable. |
| 2 | Developing | Practice attempted at scale; gaps remain; no automation. |
| 3 | Defined | Practice documented and consistently applied; partially automated. |
| 4 | Managed | Practice automated, measured, and gates merges/releases. |
| 5 | Optimizing | Practice continuously improved against evidence; benchmarked against peers. |

**8 personas** with weights summing to 100 each (codified verbatim in `sdlc_assessor/rsf/personas.py`):

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

**Aggregation** (`sdlc_assessor/rsf/aggregate.py`):
- `D_i = mean(s_ij)` for sub-criteria `j` in dimension `i` (excluding N/A) — RSF §4
- `T = Σ D_i × w_i` for the persona's weights — 0–500 scale
- `T_% = T / 500 × 100` — 0–100% executive view

**Special values** (RSF §1):
- `?` = evidence not collected — treated as 0 in math but flagged separately
- `N/A` = does not apply — excluded from dimension's denominator; persona weights for N/A dimensions are proportionally redistributed

**Confidence flag** (RSF §4): any dim with ≥1 `?` is flagged; if >25% of persona's weight maps to flagged dims, the report shows "limited confidence."

**Per-criterion published-framework anchors** (RSF §11) — the full citation table is in `docs/frameworks/rsf_v1.0.md`.

**If you ever need a value from one of these frameworks** (CWE ID, SLSA level definition, DORA band cutoff, ASVS verification level, NIST SSDF task id, ISO clause, etc.) **do NOT default to your training memory.** WebFetch from the URL or ask the user. The user has flagged this directly: *"Never just default to what you have in memory for the standard."*

---

## 8. What is *actually measured* vs unverified

After the RSF cutover and the four scorer fixes in commit `33bffd8`, **14 of 31 RSF sub-criteria are scored against real anchors**. The other 17 return `?`.

### Real-anchor scorers (14 of 31)

| RSF id | Title | What we check | Weakness |
|---|---|---|---|
| D2.2 | Secrets in source / git history | Findings with `probable_secrets` / `committed_credential` subcategory + `.gitleaks.toml` or secret-scan workflow | Regex-only; doesn't analyze rotation status, blast radius, vault adoption |
| D2.3 | ASVS / Top 10 conformance | Findings with subcategory in `_TOP_TEN_PATTERN_SUBCATS` | Pattern-only, not actual ASVS audit. Score 0 fires only on visible patterns; absence ≠ ASVS Level 1+ |
| D3.1 | SBOM availability | File named `sbom.json` etc. OR workflow mentioning syft/cyclonedx/anchore/sbom-action | Doesn't generate or validate SBOM; only checks for file presence |
| D3.2 | Artifact signing | Workflow mentioning cosign/sigstore/in-toto/slsa-framework | Doesn't verify signatures or check Rekor; just keyword match |
| D3.4 | Dependency-update automation | `.github/dependabot.yml` or `renovate.json` presence | Doesn't inspect config scope (security-only vs minor vs major) |
| D5.4 | Release cadence and tagging | `tag_count > 0` → 1; release-please/changesets workflow → 4; SLSA workflow → 5 | Doesn't verify SemVer compliance, release-note structure, attestation depth |
| D6.1 | README and onboarding | README present + ≥5 non-empty lines | No content analysis (no detection of architecture / ADRs / runbooks / threat model) |
| D6.2 | License clarity | LICENSE file present + SPDX-hint string match | No SBOM cross-check; no license-compatibility analysis |
| D6.3 | Security policy & disclosure | SECURITY.md presence + line count + contact-language regex (`@`/`email`/`report`/`disclosure`/`contact`) | No SLA / CVE-numbering-authority / bug-bounty detection |
| D6.4 | Contribution guidance & governance | CONTRIBUTING.md / CODE_OF_CONDUCT.md / GOVERNANCE.md presence | No content analysis; no roadmap / open-governance verification |
| D7.1 | Bus factor | `top_authors[0].share > 0.8` → 0 (RSF anchor verbatim); fallback to bus_factor | Depends on git collector window (last 95 commits by default) |
| D7.2 | Activity (sustained, not spiky) | `commits_last_30/90/180/365_days` from git collector mapped to RSF level anchors | Doesn't detect "long quiet windows" within the period |
| D7.4 | Maintainer continuity | `len(top_authors)` + GOVERNANCE.md / CODEOWNERS presence | Doesn't verify succession docs / foundation sponsorship / governance rotation |

### Unverified (`?`) — what's NOT measured (17 of 31)

| RSF id | Title | What would be needed |
|---|---|---|
| D1.1 | Automated test coverage | Real coverage % from `coverage.py` / `nyc` / `lcov`. File count ≠ coverage. |
| D1.2 | Static analysis & lint discipline | **The 5 SAST adapters at `detectors/sast/` exist** but their findings don't reach this scorer. Wire them. |
| D1.3 | Code complexity / hotspot management | Behavioral code analysis (CodeScene / radon / lizard) |
| D2.1 | Known vulnerabilities (CVE/OSV) | OSV-Scanner / pip-audit / npm audit adapter |
| D2.4 | Branch protection & code review enforcement | GitHub Settings API |
| D3.3 | SLSA build track level | Build attestation inspection (Rekor lookups, in-toto verification) |
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
| D8.3 | Sectoral regulatory conformance | Org-scoped: HIPAA / PCI / FedRAMP / CMMC / FDA / EU AI Act |
| D8.4 | Vendor-risk readiness | Org-scoped: CSA CAIQ / Trust Center artifacts |

**Bottom line**: with detectors covering ~14 of 31 sub-criteria, real-world repos score in the **3–10% range** on persona-weighted totals. The math is faithful to RSF; the detector pipeline is the gap. **This is the substantive unsolved problem.**

---

## 9. Detector inventory

### Core detectors (`sdlc_assessor/detectors/`)

| File | Emits | Notes |
|---|---|---|
| `common.py` | `_walk_repo_files` helper, secrets scanner, large-file/committed-artifact recorders | Hardcoded ignore list (`.git`, `.venv`, `node_modules`, etc.) + `.gitignore` respect via `pathspec` |
| `python_pack.py` | AST-based Python detectors: `bare_except`, `broad_except_exception`, `subprocess_shell_true`, `print_usage`, `any_usage`, `type_ignore`, `eval_or_exec`, `pickle_load_untrusted`, `os_system_call`, `requests_verify_false`, `unsafe_sql_string`, `mutable_default_argument`, `module_level_assert` | Uses Python `ast` module; per-file `count` aggregation |
| `tsjs_pack.py` | TS/JS detectors via tree-sitter and regex: `exec_call`, `execsync`, `empty_catch`, `console_usage`, `as_any`, `json_parse`, `missing_strict_mode` | Requires `tree-sitter-language-pack==1.6.2` (1.6.3 has a Linux import regression) |
| `git_history.py` | `git_summary` payload (commits, signing, bus factor, top_authors, codeowners, tag_count, commits-per-window) + findings: `unsigned_commits`, `single_author`, `codeowners_missing` | Shells out to `git`; defensive timeouts; falls back gracefully when git isn't available |
| `dependency_hygiene.py` | Findings about lockfile presence, dep version pinning, manifest health | |
| `registry.py` | Top-level dispatcher; runs all detectors + SAST adapters | Line 52: `findings.extend(run_sast_adapters(path))` |

### Tree-sitter language packs (`sdlc_assessor/detectors/treesitter/`)

| File | Language | Subcategories |
|---|---|---|
| `csharp_pack.py` | C# | `csharp_console_writeline`, `csharp_dynamic_type`, `csharp_empty_catch`, `csharp_process_start`, `csharp_todo_or_fixme`, `csharp_unsafe_method` |
| `go_pack.py` | Go | `go_exec_command_shell`, `go_fmt_println`, `go_init_with_side_effects`, `go_panic_call`, `go_recover_without_repanic`, `go_todo_or_fixme`, `go_unsafe_pointer` |
| `java_pack.py` | Java | `java_class_forname`, `java_empty_catch`, others |
| `kotlin_pack.py` | Kotlin | similar set |
| `rust_pack.py` | Rust | `rust_unsafe_block`, `rust_unwrap`, `rust_mem_transmute`, others |
| `tsjs_pack.py` (treesitter) | TS/JS deeper rules | `tsjs_*` subcategories |

### SAST adapters (`sdlc_assessor/detectors/sast/`) — **built but not wired to RSF**

| File | Tool | Status |
|---|---|---|
| `semgrep_adapter.py` | Semgrep | Runs if `semgrep` is on PATH; emits findings into the legacy array. **Findings do NOT feed RSF D1.2 / D2.3 scorers.** |
| `bandit_adapter.py` | Bandit (Python SAST) | Same caveat |
| `eslint_adapter.py` | ESLint (JS lint) | Same caveat |
| `ruff_adapter.py` | Ruff (Python lint) | Same caveat |
| `cargo_audit_adapter.py` | cargo-audit (Rust deps) | Same caveat |
| `framework.py` | Adapter registry | All adapters register here; `run_sast_adapters(path)` dispatches |

**The wiring gap is one of the highest-leverage fixes for the next session.** See §23.

---

## 10. Subcategory taxonomy

Findings carry `category` (one of 8 RSF-aligned high-level buckets) and `subcategory` (specific pattern). Known subcategories include:

**Security**: `probable_secrets`, `committed_credential`, `subprocess_shell_true`, `exec_call`, `execsync`, `eval_or_exec`, `pickle_load_untrusted`, `os_system_call`, `requests_verify_false`, `unsafe_sql_string`, `unsigned_commits`

**Code quality**: `bare_except`, `broad_except_exception`, `empty_catch`, `console_usage`, `print_usage`, `any_usage`, `as_any`, `type_ignore`, `mutable_default_argument`, `module_level_assert`, `json_parse`, `missing_strict_mode`

**Documentation/CI**: `missing_readme`, `missing_security_md`, `missing_ci`, `missing_tests`

**Supply chain**: `committed_artifacts`, `large_files`

**Per-language**: `go_*`, `java_*`, `csharp_*`, `kotlin_*`, `rust_*`, `tsjs_*` (as enumerated in §9)

**Sustainability**: `single_author`, `codeowners_missing`

The mapping from subcategory to RSF criterion is implicit in the scorer logic (e.g., `_TOP_TEN_PATTERN_SUBCATS` in `rsf/scorers.py` for D2.3). There is no formal taxonomy doc; building one is a candidate cleanup task.

---

## 11. Profile system (use_case × maturity × repo_type merge)

Three JSON profile files at `sdlc_assessor/profiles/data/`:

- `use_case_profiles.json` — 4 use_cases (`acquisition_diligence`, `vc_diligence`, `engineering_triage`, `remediation_agent`). Each has `category_multipliers`, `narrative_emphasis`, `pass_threshold`, `distinction_threshold`, `remediation_depth`. **The threshold fields are LEGACY** — superseded by RSF persona weights but still in the JSON for back-compat.
- `maturity_profiles.json` — `production` / `prototype` / `research`. Each has `severity_multiplier`, `category_applicability`, `missing_ci_is_blocker`, `missing_tests_and_missing_ci_can_trigger_blocker`.
- `repo_type_profiles.json` — 8 archetypes. Each has `applicability_overrides`, archetype-specific finding rules.

Merge order (`sdlc_assessor/scorer/precedence.py`): `use_case` → `maturity` → `repo_type`. Later profiles override earlier ones for shared keys.

**Loader functions** (`sdlc_assessor/profiles/loader.py`):
- `load_use_case_profiles()`, `load_maturity_profiles()`, `load_repo_type_profiles()`
- `build_effective_profile(use_case, maturity, repo_type, policy_overrides=None)` — produces the merged profile

---

## 12. Profile signing infrastructure

`sdlc_assessor/profiles/packs.py` implements signed profile packs (HMAC-SHA256 v1 trust model). Key functions:

- `compute_signature(manifest, secret_hex)` — HMAC-SHA256 over canonical JSON of manifest
- `verify_pack(manifest, signature, trust)` — verifies against a trust dict (key_id → secret_hex)
- `load_signed_pack(pack_path, trust=None)` — loads + verifies a `.zip`-packed profile
- `build_pack(...)` — packs a profile directory into a signed `.zip`

Trust file location: `~/.config/sdlc_assessor/trust.json` (per `trust_path()`).

The roadmap in `CHANGELOG.md` calls for **ed25519 asymmetric signing** to replace HMAC v1 — a future enhancement.

There is one known flaky test: `tests/unit/test_profile_packs.py::test_load_signed_pack_rejects_tampered_signature` — passes in isolation, occasionally fails when tests run in a specific order. State-leak issue, not a real regression.

---

## 13. LLM narrator + dual-narrator flag

Two flags exist and both are wired:

- `--narrate-with-llm` (legacy boolean): when set, replaces the deterministic per-category summary with LLM-generated narrative via the Anthropic API. Implemented in `sdlc_assessor/scorer/llm_narrator.py`. Default model: `claude-haiku-4-5-20251001`. Falls back to deterministic on any gate failure (no API key, network error, etc.).

- `--narrator deterministic|llm|both` (newer): designed for body narrative blocks, not just category summaries. **Not yet fully wired** — the flag is parsed and passed through to the renderer but the LLM-narrator integration with the persona narrative blocks isn't complete. The renderer accepts the param and embeds it in the rendered footer; building the dual-render side-by-side mode is a deferred workstream.

Activation gates: requires `ANTHROPIC_API_KEY` env var; degrades to deterministic if absent. The `[llm]` extra in `pyproject.toml` lists Anthropic SDK dependency.

---

## 14. Compare mode

`sdlc compare repo_a repo_b --use-case <name>` runs the full pipeline against both repos (each into `<out-dir>/repo_a/` and `<out-dir>/repo_b/`), then emits:

- `comparison.md` (Markdown delta report)
- `comparison.json` (structured comparison artifact)

Implementation: `sdlc_assessor/compare/engine.py` + `sdlc_assessor/compare/markdown.py`. The comparison surfaces score deltas, finding deltas (added/removed), and inventory deltas.

**Compare mode does not yet integrate RSF.** It uses the legacy scoring engine. Wiring RSF into compare-mode is a candidate followup.

---

## 15. Test fixtures

26 fixtures at `tests/fixtures/`:

| Fixture | Purpose |
|---|---|
| `fixture_committed_credential` | Has a credential committed to source — exercises D2.2 |
| `fixture_csharp_basic`, `_unsafe` | C# tree-sitter pack |
| `fixture_empty_repo` | Empty repo edge-case |
| `fixture_go_basic`, `_panics` | Go tree-sitter pack |
| `fixture_infrastructure_archetype` | IaC / Terraform-shaped |
| `fixture_internal_tool_archetype` | Internal-tool archetype |
| `fixture_java_basic`, `_unsafe` | Java tree-sitter pack |
| `fixture_javascript_basic` | JS-only repo |
| `fixture_kotlin_basic`, `_unsafe` | Kotlin tree-sitter pack |
| `fixture_library_archetype` | Library archetype |
| `fixture_monorepo_archetype` | Monorepo archetype |
| `fixture_no_ci` | Production repo without CI workflows |
| `fixture_probable_secret` | Secret-scanning detector regression |
| `fixture_python_basic` | Standard Python repo |
| `fixture_research_repo` | Notebook-dominant research repo |
| `fixture_rust_basic`, `_unsafe`, `_with_lockfile` | Rust tree-sitter pack |
| `fixture_service_archetype` | Service archetype |
| `fixture_tsx_only` | TSX-only repo |
| `fixture_typescript_basic` | Standard TS repo |
| `fixture_vendored_node_modules` | Vendored deps — should NOT be scanned |

Test directory: `tests/unit/` (28 files), `tests/golden/` (1 file with golden Markdown + HTML).

---

## 16. Stale code / spec-doc staleness

### Stale code that's still present but no longer reached

| Path | Status | Why kept |
|---|---|---|
| `sdlc_assessor/renderer/deliverables/_decomposition.py` | Module no longer called by `_integrate.py` | Kept on disk for back-compat; `apply_depth_pass()` sets `deliverable.score_decomposition = None` |
| `sdlc_assessor/renderer/deliverables/_gap.py` | Module no longer called by `_integrate.py` | Same as above; `deliverable.gap = None` |
| `sdlc_assessor/renderer/html.py` | Legacy v0.9.0 HTML renderer | Still callable via `render_html_report` from this module if a caller imports it directly; the new `deliverable_html.py` is the default |
| `sdlc_assessor/renderer/markdown.py` | Markdown renderer | Used by `--format markdown`; legacy substrate; not yet RSF-grounded |
| `_render_score_decomposition` and `_render_gap_analysis` in `deliverable_html.py` | Functions still defined but no longer called by the layout assembly | Removed from the `<main class="doc">` HTML template; functions remain |
| Legacy `pass_threshold` / `distinction_threshold` keys in `use_case_profiles.json` | Still in JSON | Removing them would break legacy scorer; deferred until legacy scorer is also retired |

**Cleanup pass to consider before release**: remove the unreachable `_decomposition.py`, `_gap.py`, the unused render functions, and the legacy threshold JSON keys. Each removal is small individually; doing them as one commit would be cleaner.

### Spec-doc staleness

`docs/ANALYSIS.md` and `docs/ACTION_PLAN.md` were the user's original spec at session start. They describe a **self-authored 0–100 rubric** that the user later replaced with RSF v1.0. **Those docs have NOT been updated** to reflect the RSF substrate switch. The next session should either:

1. Update those docs to point at RSF as the canonical framework, OR
2. Add a banner at the top of each saying "superseded by `docs/frameworks/rsf_v1.0.md` for scoring; original spec retained for historical context."

`docs/SDLC_Framework_v2_Spec.md` and `docs/scoring_engine_spec.md` are similarly stale relative to RSF.

`docs/calibration_targets.md` references the legacy fixture-based calibration. RSF §5 prescribes a 3-point calibration set against published-evidence OSS projects; the targets file does NOT reflect that.

---

## 17. Speculative values still in code

The user's strongest critique was that values are invented. Even after the RSF cutover, some speculative values remain:

| File:Line | Constant | Risk |
|---|---|---|
| `renderer/deliverables/vc.py:54-63` | `_VC_BASELINE = {"architecture_design": 0.6, ...}` | A made-up "typical investable VC baseline" polygon used in the radar chart. Not anchored to any published reference. The user has not yet flagged this specifically but it falls under the trust-me-bro pattern. |
| `renderer/deliverables/engineering.py:46` | `_EFFORT_VALUE = {"XS": 0.1, "S": 0.3, "M": 0.55, "L": 0.8, "XL": 0.95}` | Effort label → matrix-position mapping. Speculative. |
| `remediation/planner.py:183-203` | `SEVERITY_BASE_DELTA`, `CONFIDENCE_FACTOR`, `MATURITY_FACTOR`, and the `(0.6 + 0.4 * mag)` formula | Used for `expected_score_delta` per remediation task. Not anchored. |
| `scorer/engine.py` | `BASE_WEIGHTS`, `SEVERITY_WEIGHTS`, `CONFIDENCE_MULTIPLIERS`, `PRODUCTION_FLAT_PENALTIES` | Legacy scoring engine; still runs for back-compat but no longer drives the primary report. |
| `renderer/deliverables/base.py` (Recommendation logic) | `derive_recommendation()` 4-way verdict (`proceed` / `proceed_with_conditions` / `defer` / `decline`) | Maps score + blocker counts to a verdict. Not anchored to RSF — RSF doesn't define a single pass threshold. The cover-page rationales currently use this. |

The next session should decide which of these to anchor (some have framework analogs — e.g., effort labels could be anchored to NIST SSDF task complexity; recommendation verdicts could map to RSF persona-total bands) and which to clearly mark as editorial / not-yet-grounded.

---

## 18. External tool dependencies + version pins

### Required at runtime (in `[project]` deps)

- Python 3.12
- `pathspec >= 0.12` (gitignore matching)
- `pyyaml >= 6.0` (workflow YAML parsing)
- `jsonschema >= 4.20` (schema validation when `SDLC_STRICT=1`)

### Dev / test (`[project.optional-dependencies].dev`)

- `pytest >= 8.0`
- `mypy >= 1.10`
- `ruff >= 0.5`
- `tree-sitter-language-pack == 1.6.2` — **PINNED**. Version `1.6.3` has a Linux import regression (`librt`, `python-discovery` transitive deps fail). Don't unpin without verifying.

### Optional at runtime (gated on tool availability)

| Tool | Used by | Behavior if missing |
|---|---|---|
| `git` | `git_history.py`, provenance collector | Returns None / falls back to "no git origin" |
| `semgrep` | `sast/semgrep_adapter.py` | Adapter returns empty findings list |
| `bandit` | `sast/bandit_adapter.py` | Same |
| `eslint` | `sast/eslint_adapter.py` | Same |
| `ruff` | `sast/ruff_adapter.py` | Same — but ruff is also a dev dep so usually present |
| `cargo-audit` | `sast/cargo_audit_adapter.py` | Same |
| Anthropic SDK | LLM narrator | Falls back to deterministic narrator |

### Future workstreams require

- `osv-scanner` or `pip-audit` (D2.1 anchor)
- `syft` or `cyclonedx-py` (D3.1 SBOM generation)
- `gh` CLI or GitHub PAT (D2.4, D5.1, D5.2, D7.3)
- `coverage`/`nyc`/`lcov` parsers (D1.1)
- `weasyprint` or `playwright` for PDF rendering (deferred 0.13.0 work)

---

## 19. Background-agent state from this session

During the framework-anchoring research phase, three research agents were launched in the background:

| Agent | Status | Output |
|---|---|---|
| NIST SSDF research | **Refused** to proceed — WebFetch denied, agent correctly didn't fall back to memory | No doc produced |
| DORA bands research | Completed | `docs/frameworks/dora.md` (committed in 8f11d0f) |
| CWE Top 25 + CVSS v3.1 research | Completed (proceeded from verified-stable knowledge with spot-check disclosure) | `docs/frameworks/cwe_cvss.md` (committed in 8f11d0f) |

**Three frameworks were never researched** (would have been launched if the session continued in research mode):
- SLSA v1.0
- ISO/IEC 25010 / CISQ
- CHAOSS Common Metrics

The user superseded the framework-research workstream by providing **RSF v1.0** directly. The two completed framework docs (`dora.md`, `cwe_cvss.md`) are now reference material; the RSF doc is the canonical scoring spec.

---

## 20. User's working style and red lines

### Hard requirements

- **Every numeric anchor must trace to a published source.** RSF v1.0 → `docs/frameworks/rsf_v1.0.md`. CWE → MITRE. CVSS → FIRST. DORA → State of DevOps Reports. SSDF → NIST SP 800-218. **Do not invent.**
- **Removals before additions.** When the user directs a substrate change, audit existing references first, list them in chat, remove them, then add the replacement.
- **Grep-before-done.** After committing, re-render and grep the output to prove the directive landed. Paste the count in chat.
- **Audit visible in chat before code.** When the user asks for a substrate change, paste the grep results showing every legacy reference (file:line) before writing new code.
- **Mid-flight state named explicitly.** Do not commit partial work as if it's complete. Say "this commit is part 1 of N; here's what's still broken until parts 2..N land."

### Communication patterns

- **Stop asking for permission.** When given a directive, execute. Don't ask "should I proceed?" — proceed and show the result.
- **Concise direct acknowledgement when called out.** Don't be defensive. Don't promise "I'll be different." Show different behavior.
- **Surface critique honestly even when uncomfortable.** If the analysis is thin, say so. The user will catch it anyway.

### Verbatim escalation quotes (recognize these patterns)

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
| Surface-level handoff | *"You consider that handoff comprehensive and exhaustive?"* |

When the user uses ALL CAPS or repeated `WHY` / `WTF`, you have crossed a line. The right response is to **stop, concede, name the specific failure, fix it visibly, and move forward**. Defending the prior work compounds the trust failure.

---

## 21. The 9 feedback memories saved this session

Located at `/Users/ethanallen/.claude/projects/-Users-ethanallen-SDLC-assesment/memory/`:

| File | Theme |
|---|---|
| `feedback_attribution.md` | Distinguish my context inferences from user directives; don't put my decisions in the user's mouth |
| `feedback_persona_voice.md` | Persona means contextualized analysis, not relabeled scaffolding — every chart label, category, caption, and metric in the persona's frame |
| `feedback_version_naming.md` | Don't call polish releases v1; v1 of a product requires real substrate (corpus, interviews, peer review, outcome data) |
| `feedback_provenance.md` | Reports must name their subject — every report needs project name + repo URL + commit SHA + scan timestamp + classifier output, pinned at top |
| `feedback_directive_drift.md` | Treat directives as contracts, not phrases — when user says "industry standards" every numeric constant must cite a published reference |
| `feedback_no_memory_for_standards.md` | Never default to memory for industry-standard values; published-framework values must come from the spec or a user attachment |
| `feedback_no_half_measures.md` | When swapping a substrate, the new section is not a fix on its own; the old section that contradicts it must be removed or rewritten |
| `feedback_audit_before_add.md` | Directive-driven work is removal-then-add; grep the codebase for legacy references first, list them as removal targets, don't ship new code until they're gone |
| `feedback_trust_through_behavior.md` | When discipline is in question, paste audit before code, commit removals before additions, re-render and grep output before claiming done, name mid-flight state explicitly |

The index is at `MEMORY.md` in the same directory. **Read these before writing code.** They are the distilled record of the failure patterns the prior session exhibited; they are the user's explicit instructions for the next session.

---

## 22. The plan file

Located at `/Users/ethanallen/.claude/plans/users-ethanallen-downloads-sdlcasses-ac-vivid-shamir.md`. Has been overwritten multiple times as scope evolved. Current top-of-file describes the **RSF cutover verification run on AgentSentry** (already executed). Below that is the older multi-week roadmap (provenance + framework anchoring + persona artifacts in parallel) — partially superseded by RSF but still useful as a workstream map.

**Key roadmap items still relevant:**

- **Workstream A (Provenance)**: DONE.
- **Workstream B (Framework anchoring)**: Partial. RSF codified; per-criterion scorers done for 14/31. Detector-pipeline expansion to close the 17 `?`s is the substantive remaining work.
- **Workstream C (Per-persona artifacts)**: Not started. Cover/exec-summary layer is persona-distinct; body sections still use the same engineering content with vocabulary swaps.

**Multi-month items gated on user-action** (cannot fake; user must source):
- Real outcome-linked corpus (≥50 entries) for backtesting recommendations
- Persona-user research interviews (≥6 per persona × 4+ personas)
- Methodology peer review (≥2 external reviewers)
- Calibration set per RSF §5 (a published-evidence OSS reference + a typical mid-stage SaaS + a neglected internal repo)

---

## 23. Immediate next work in priority order

The user's last unresolved question was: *"Want me to plan that work now (it's multi-day) or land what's in flight first?"* — they didn't answer. **Default to landing what's in flight, then ask before starting multi-day workstreams.**

### Before anything else: confirm the working tree state

```bash
git status
git log --oneline -10
.venv-sdlc/bin/pytest -q
```

Expected: clean working tree, head at `d34ac7c`, 388+ tests passing.

### Priority 1 — Persona-contextual translation (in flight per the todo list)

The current in-progress todo: *"Persona-contextual translation of RSF top-5 findings: VC reads investment language; C-level reads liability; eng reads sprint; agent reads imperative."*

Implementation: extend each of `acquisition.py` / `vc.py` / `engineering.py` / `remediation.py` with a `_persona_translation_section(scored, deliverable)` method. Pull the top-5 lowest-scored sub-criteria from `scored["rsf"]["dimensions"][*]["criteria"][*]` (where value is int, sorted ascending). Per criterion, emit persona-specific consequence text:

- **VC reading D2.2 = 0**: "Active secrets in source code → pre-term-sheet founder Q&A; valuation-discount candidate; falls under OWASP ASVS V2 / NIST SSDF PS.5"
- **Acquisition (PE/M&A) reading D2.2 = 0**: "Inherited secrets exposure → escrow condition or seller-funded rotation; inherited GDPR Art. 32 / CCPA liability"
- **Engineering reading D2.2 = 0**: "Phase-1 sprint must-ship: rotate secrets + deploy gitleaks pre-commit hook + add `.github/secret_scanning.yml`"
- **Remediation agent reading D2.2 = 0**: "Task: rotate exposed credentials; verify with `git filter-repo --invert-paths`; idempotency check `git grep -nE 'AKIA|sk_live'`"

Render the section in the deliverable HTML between the RSF block and the existing chart sections.

### Priority 2 — Detector-pipeline expansion (the substantive gap, multi-day each)

Each of these closes 1–4 `?` slots. Order by leverage:

1. **Wire SAST adapters into RSF D1.2 / D2.3 scoring** (1 day). The 5 adapters at `sdlc_assessor/detectors/sast/` already emit findings into the legacy `findings` array. Update `score_d1_2` / `score_d2_3` in `sdlc_assessor/rsf/scorers.py` to count SAST findings by severity and map to RSF level anchors. **This is the highest-leverage fix** because the work is mostly done — just unwired.
2. **OSV-Scanner adapter** (`sdlc_assessor/detectors/sast/osv_adapter.py`) (2 days). Reads `package-lock.json` / `poetry.lock` / `Cargo.lock` / etc.; runs `osv-scanner --format=json` if installed; emits findings with CVE IDs. Closes D2.1 (CVE) and feeds D3.4.
3. **GitHub API adapter** (NEW `sdlc_assessor/detectors/github/`) (3 days). Read-only API calls for branch protection rules (D2.4), PR review history (D5.1), workflow run history (D5.2), issue/PR responsiveness (D7.3). Requires `GITHUB_TOKEN` env var; gate gracefully when absent.
4. **DORA history walk** (extend `sdlc_assessor/detectors/git_history.py`) (3 days). Walk merge commits + tags + GitHub deployment events. Closes D4.1, D4.2, partially D4.3.
5. **SBOM generation** (NEW `sdlc_assessor/detectors/sbom_adapter.py`) (1 day). Shell out to `syft` / `cyclonedx-py`; generate CycloneDX JSON; emit as detector output. Closes D3.1 above the file-presence check.
6. **Real coverage analysis** (NEW) (1 day). Read `coverage.xml` / `coverage.json` / `lcov.info` if present; extract line + branch coverage. Closes D1.1.

For each item, **wire into the RSF scorer AND add a test** that asserts the new evidence flows through to the right RSF level. Otherwise you'll repeat the SAST-built-but-not-wired trap.

### Priority 3 — Persona-distinct artifacts (not just vocabulary)

- **Acquisition**: license-compliance matrix (SPDX scan via `scancode-toolkit` or `licensee`); CODEOWNERS bus-factor; integration-cost ladder; CVE register with CVSS scores (depends on Priority 2 #2).
- **VC**: pitch-claims ingestion (`sdlc claims add ./pitch.md` CLI); claim × evidence substantiation table; founder shipping cadence visualization.
- **Engineering**: DORA dashboard (depends on Priority 2 #4); CWE Top 25 coverage map (depends on Priority 2 #1); on-call delta per finding.
- **Remediation**: machine-readable JSON manifest as primary artifact; per-task patch anchors + idempotency checks.

Each persona is 3–5 days. The plan file lays out the file ownership.

### Priority 4 — Stale-code + speculative-value cleanup

- Remove `_decomposition.py` and `_gap.py` modules (unreachable).
- Remove `_render_score_decomposition` and `_render_gap_analysis` functions.
- Decide: anchor `_VC_BASELINE`, `_EFFORT_VALUE`, planner constants — or mark explicitly as editorial/unsourced.
- Anchor or strip the 4-way verdict in `derive_recommendation()`.
- Update `docs/ANALYSIS.md` / `docs/ACTION_PLAN.md` / `docs/SDLC_Framework_v2_Spec.md` / `docs/scoring_engine_spec.md` to point at RSF as canonical, or banner them as historical.

### Priority 5 — Calibration corpus + persona research + peer review

User-action gated. **Cannot fake.** Required for industry-quality v1:
- Real outcome-linked corpus (≥50 entries).
- Persona-user interviews (≥6 per persona).
- Methodology peer review (≥2 external reviewers).

These are explicitly named in the plan file. **Don't try to fake them.** Instead, build the *infrastructure* for ingesting them (corpus schema, interview-coding tool, reviewer harness) so when the user sources the data, the assessor can use it.

### Priority 6 — Version bump + release

When the work above is honestly done and the user has signed off:
1. Bump `__version__` in `sdlc_assessor/__init__.py` and `pyproject.toml`.
2. Update `CHANGELOG.md` with the v0.10.0 / v0.11.0 / etc. release notes.
3. Open the PR.
4. Wait for CI green.
5. Tag-push triggers the release workflow.

**Do not bump version mid-stream.** Release should be a clean cut, not a marker of partial progress.

---

## 24. Things you should NOT do

- **Do not invent numeric values.** If RSF says level 3 anchor is "Line coverage 50–70%", that's the spec. Do not make up a different threshold.
- **Do not add a section without removing what it replaces.** Grep first.
- **Do not call polish releases v1.** v1 has a calibration corpus + persona research + peer review backing it.
- **Do not skip user-action items.** Name them explicitly.
- **Do not minimize the gap.** When the assessor scores 5% across all personas, that's the assessor not measuring enough. Don't dress up low scores with persona-flavored prose.
- **Do not pretend the SAST adapters give the report a real SAST integration.** Until you wire them, the assessor doesn't actually do SAST in any way that affects the RSF score.
- **Do not write a feedback memory in lieu of doing the work.** The memory documents the failure; the work fixes it.
- **Do not silently drop user-direction items.** If the user said "do X" and X turns out to be more work than one turn, name that explicitly and ask whether to land partial-X or hold.
- **Do not produce a thin handoff** (this section exists because the prior version was thin and the user called it out).

---

## 25. Verification commands

```bash
# Working tree state
git status
git log --oneline -10
.venv-sdlc/bin/pytest -q  # expect 388+ passed

# Render against this repo
rm -rf /tmp/self_handoff
.venv-sdlc/bin/python -m sdlc_assessor.cli run . --use-case acquisition_diligence \
  --format html --out-dir /tmp/self_handoff

# Render against AgentSentry (clone if missing)
test -d /tmp/AgentSentry || git clone --depth 50 https://github.com/calabamatex/AgentSentry /tmp/AgentSentry
rm -rf /tmp/sentry_handoff
.venv-sdlc/bin/python -m sdlc_assessor.cli run /tmp/AgentSentry --use-case vc_diligence \
  --format html --out-dir /tmp/sentry_handoff

# Inspect the RSF output
.venv-sdlc/bin/python -c "
import json
for label, path in [('self', '/tmp/self_handoff/scored.json'), ('sentry', '/tmp/sentry_handoff/scored.json')]:
    s = json.load(open(path))
    rsf = s['rsf']
    real = sum(1 for d in rsf['dimensions'] for c in d['criteria'] if isinstance(c['value'], int))
    unverified = sum(1 for d in rsf['dimensions'] for c in d['criteria'] if c['value'] == '?')
    print(f'{label}: {real} real, {unverified} unverified, {len(rsf[\"flagged_dimensions\"])} flagged dims')
    for p in rsf['personas']:
        print(f'  {p[\"persona_label\"]:<22} {p[\"total_pct\"]:>6.1f}%')
"

# Trust-mechanism: confirm legacy substrate is gone
for phrase in \
  "pass_threshold" "diligence bar" "use_case_profiles.json:" \
  "SEVERITY_WEIGHTS" "score-decomposition" "gap-analysis"; do
  count=$(grep -c "$phrase" /tmp/self_handoff/report.html /tmp/sentry_handoff/report.html 2>/dev/null | awk -F: '{s+=$NF} END {print s}')
  echo "  [$count] $phrase"
done
# Expect: all zeros.

# Open the reports
open /tmp/self_handoff/report.html /tmp/sentry_handoff/report.html
```

---

## 26. Code conventions used in the project

- **Dataclasses with `slots=True`** for value objects: `@dataclass(slots=True)` everywhere. Sometimes `frozen=True` for immutables.
- **Type hints** on every function signature, including returns. Use `from __future__ import annotations` to avoid runtime forward-reference issues.
- **`Path` instead of strings** for paths.
- **Module-level constants UPPERCASE_WITH_UNDERSCORES** (e.g., `BASE_WEIGHTS`, `RSF_CRITERIA`).
- **Private helpers prefixed with `_`** — not exported in `__all__`.
- **Pure functions where possible** — explicit dependency injection rather than module-level state.
- **Subprocess calls always use `_run_git`-style helpers with timeouts** + graceful failure.
- **Error handling**: catch broad exceptions only at process boundaries; everywhere else, let exceptions propagate and add context if needed.
- **Docstrings**: every public function has one. The first line is a one-liner; subsequent paragraphs are wrapped at ~80 chars.
- **Imports**: stdlib first, third-party second, local last; alphabetical within each group.
- **Test naming**: `test_<thing>_<condition>_<expected>` — long but searchable.

---

## 27. File map

```
sdlc_assessor/
├── __init__.py                          # __version__ = "0.9.0" (NOT BUMPED for current branch)
├── cli.py                               # CLI entrypoint (6 subcommands; see §6)
├── classifier/
│   ├── engine.py                        # Archetype/maturity/network detection
│   └── (helpers)
├── collector/
│   └── engine.py                        # Top-level evidence collection
├── core/
│   ├── schema.py                        # JSON schema validation (validate_evidence_full)
│   ├── evidence_schema.json             # The schema (packaged + docs/ copy)
│   └── io.py                            # write_json with sort_keys=True
├── detectors/
│   ├── common.py                        # Shared helpers (file walking, secrets scanner)
│   ├── git_history.py                   # git_summary collector
│   ├── dependency_hygiene.py
│   ├── python_pack.py                   # AST Python detectors
│   ├── tsjs_pack.py                     # TS/JS detectors (regex + tree-sitter)
│   ├── registry.py                      # Detector dispatch (line 52: SAST runs)
│   ├── treesitter/                      # Multi-language tree-sitter
│   │   ├── framework.py
│   │   ├── csharp_pack.py / go_pack.py / java_pack.py / kotlin_pack.py / rust_pack.py / tsjs_pack.py
│   │   └── rules/                       # Per-language rule packs
│   └── sast/                            # SAST adapters (NOT wired to RSF)
│       ├── framework.py
│       ├── semgrep_adapter.py / bandit_adapter.py / ruff_adapter.py / eslint_adapter.py / cargo_audit_adapter.py
│       └── __init__.py                  # run_sast_adapters(path)
├── normalizer/
│   ├── findings.py                      # normalize_findings, classify_path, is_fixture_finding
│   └── dedupe.py                        # Cross-detector dedupe via family map
├── scorer/
│   ├── engine.py                        # LEGACY 0–100 scoring (still runs)
│   ├── blockers.py                      # Hard-blocker detection
│   ├── precedence.py                    # Profile merge order
│   └── llm_narrator.py                  # Anthropic API integration
├── rsf/                                 # *** RSF v1.0 — canonical ***
│   ├── __init__.py
│   ├── criteria.py                      # 31 sub-criteria, 8 dimensions (verbatim)
│   ├── personas.py                      # 8 personas + weight matrix (verbatim)
│   ├── aggregate.py                     # D_i / T / T_% formulas + confidence flagging
│   ├── scorers.py                       # 31 per-criterion scorers (14 real, 17 ?)
│   └── score.py                         # Top-level assess_repository entry
├── remediation/
│   ├── planner.py                       # Generates remediation tasks
│   └── markdown.py                      # Renders remediation plan as Markdown
├── renderer/
│   ├── markdown.py                      # Legacy Markdown report
│   ├── html.py                          # Legacy v0.9.0 HTML
│   ├── deliverable_html.py              # *** Current HTML renderer ***
│   ├── persona.py                       # Persona narrative-block dispatch (SDLC-068)
│   ├── narrative_blocks.py              # Per-emphasis narrative-block builders (18 builders)
│   └── deliverables/                    # *** Persona-distinct deliverable framework ***
│       ├── base.py                      # Deliverable + supporting dataclasses
│       ├── acquisition.py / vc.py / engineering.py / remediation.py  # 4 builders
│       ├── _vocab.py                    # Per-persona vocabulary (axis labels, etc.)
│       ├── _provenance.py               # ProvenanceHeader collector
│       ├── _exec_summary.py             # RSF-grounded executive summary
│       ├── _methodology.py              # Methodology box + glossary registry
│       ├── _citations.py                # CitationRegistry for footnote markers
│       ├── _integrate.py                # apply_depth_pass() — glue layer
│       ├── charts/                      # Pure-Python SVG chart primitives (5 charts)
│       └── (legacy: _decomposition.py, _gap.py — present but no longer rendered)
├── compare/
│   ├── engine.py                        # Two-repo comparison
│   └── markdown.py                      # Comparison report renderer
├── profiles/
│   ├── loader.py                        # Profile loaders + build_effective_profile
│   ├── packs.py                         # Signed profile-pack infrastructure
│   └── data/                            # JSON profile files
│       ├── use_case_profiles.json       # 4 use_cases (LEGACY threshold fields kept)
│       ├── maturity_profiles.json       # production/prototype/research
│       └── repo_type_profiles.json      # 8 archetypes
└── (no `__main__.py` — CLI runs via `python -m sdlc_assessor.cli`)

docs/
├── HANDOFF.md                           # *** This file ***
├── frameworks/
│   ├── rsf_v1.0.md                      # *** CANONICAL FRAMEWORK ***
│   ├── cwe_cvss.md                      # Background research (committed earlier)
│   └── dora.md                          # Background research (committed earlier)
├── ANALYSIS.md                          # Original gap analysis (now stale vs RSF)
├── ACTION_PLAN.md                       # Original SDLC-001..035 plan (now stale)
├── SDLC_Framework_v2_Spec.md            # Original spec (now stale vs RSF)
├── scoring_engine_spec.md               # Legacy scoring engine spec (stale)
├── calibration_targets.md               # Legacy fixture-based calibration (stale)
├── detector_pack_starter_spec.md
├── evidence_schema.json                 # Schema (also packaged in core/)
├── remediation_planner_spec.md
├── renderer_template.md
└── README.md                            # docs/ index (out of date — points at moved profile JSONs)

tests/
├── conftest.py
├── unit/                                # 28 test files
│   ├── test_rsf_framework.py            # RSF framework integrity (21 tests)
│   ├── test_rsf_scorers.py              # Per-criterion scorer tests (44 tests)
│   ├── test_methodology.py              # Methodology + glossary
│   ├── test_deliverable_depth.py        # Integration: render + grep
│   ├── test_charts.py                   # SVG chart primitives
│   ├── test_classifier.py / test_collector_evidence.py / test_detectors.py / test_normalizer_*.py / test_remediation.py / test_render_*.py / test_scorer_*.py / test_profile_packs.py / test_compare.py / test_core_schema.py / test_version_sync.py / ... (legacy + scaffolding tests)
├── golden/
│   └── test_report_render.py            # Golden Markdown rendering
└── fixtures/                            # 26 fixtures (see §15)

scripts/
├── benchmark_calibration.py             # Runs the assessor across all fixtures
├── calibration_check.py                 # Asserts fixture scores fall within docs/calibration_targets.md bands
└── check_schema_sync.py                 # Asserts core/ + docs/ schema files are byte-identical

PLANS.md                                 # User's project-level planning doc (separate from .claude plans)
README.md                                # Top-level README
SECURITY.md / CONTRIBUTING.md / CHANGELOG.md / LICENSE   # Governance files
.github/workflows/                       # ci.yml + release.yml
pyproject.toml
.pre-commit-config.yaml                  # ruff + mypy + check-yaml + check-json + check_schema_sync
```

---

## 28. Glossary of project-specific terms

| Term | Meaning |
|---|---|
| **archetype** | The classifier's repo type: `service`, `monorepo`, `library`, `cli`, `internal_tool`, `research_repo`, `infrastructure`, `unknown` |
| **maturity** | The classifier's repo maturity: `production`, `prototype`, `research`, `unknown` |
| **applicability** | Whether a category counts toward the score for this archetype × maturity. Values: `applicable`, `partial`, `not_applicable` |
| **subcategory** | Specific finding pattern under a category (e.g. `probable_secrets`, `subprocess_shell_true`, `bare_except`) |
| **fixture finding** | A finding whose primary path is in `tests/fixtures/` / `examples/` / `vendor/` etc. — segregated in reports so it doesn't pollute production-finding tables |
| **path-class tag** | Tag on a finding like `source:test_fixture` indicating the path-class. From `normalize_findings → classify_path` (SDLC-067) |
| **hard blocker** | A finding-class that gates the verdict regardless of score. Detected by `scorer/blockers.py` |
| **closure_requirements** | Per-blocker list of what must be done to clear it (in scored.hard_blockers[]) |
| **score_impact** | Per-finding magnitude (`{direction: "negative", magnitude: 0..10, rationale: str}`) used by the legacy scorer |
| **base_weights** | Legacy scorer's per-category point allocation (sum=100) |
| **applied_weights** | Legacy scorer's per-category weights AFTER applying use_case multipliers |
| **flat_penalty** | Legacy scorer's flat deductions for production-grade gaps (missing_ci=10, missing_readme=8, missing_tests=15) |
| **score_confidence** | Legacy scorer's `low`/`medium`/`high` based on classifier confidence × proxy ratio × evidence density |
| **verdict** | Legacy scorer's 4-way: `pass_with_distinction`, `pass`, `conditional_pass`, `fail` |
| **RSF** | Repository Scoring Framework v1.0 — the canonical scoring framework, at `docs/frameworks/rsf_v1.0.md` |
| **dimension (D_i)** | One of 8 RSF dimensions (D1–D8). Score is mean of sub-criterion scores, on 0–5 scale |
| **sub-criterion** | One of 31 RSF leaf criteria (D1.1 through D8.4). Scored 0–5, `?`, or `N/A` |
| **persona-weighted total (T_%)** | RSF aggregation: `Σ D_i × w_i / 5` where `w_i` is the persona's weight from §3 matrix |
| **`?` (unverified)** | RSF special value: evidence not collected. Treated as 0 in math but flagged separately |
| **`N/A`** | RSF special value: criterion does not apply. Excluded from dimension's denominator; persona weights for N/A dims are proportionally redistributed |
| **confidence_flagged** | A dimension is flagged if ≥1 sub-criterion is `?` |
| **limited_confidence_warning** | A persona total carries this when >25% of its weight maps to flagged dimensions (RSF §4) |
| **Deliverable** | Top-level dataclass for the persona-distinct report (cover, sections, recommendation, RSF assessment, etc.) |
| **CoverPage** | Title + recommendation pill + headline metric + classification line on page 1 |
| **Section** | Polymorphic body section: `kind` is one of `prose`, `facts`, `chart`, `swot`, `day_n`, `options_ladder`, `questions`, `claims_evaluation`, `remediation_table`, `recommendation` |
| **Recommendation** | Headline + options ladder (4-way verdict per RSF supersession). Currently used in cover rationale |
| **MethodologyNote** | The methodology box content — formula, threshold explanation, multiplier explanation, verdict-rule table, calibration band |
| **GlossaryEntry** | Glossary appendix item — term + short_def + long_def + sources |
| **Citation** | In-prose footnote — claim_id + text + evidence_refs + source_files |
| **CitationRegistry** | Hands out monotonic footnote numbers, dedupes by claim_id |
| **CriterionScore** | Per-criterion RSF result — value (int/`?`/`N/A`) + evidence + rationale |
| **DimensionScore** | Per-dimension RSF aggregate — mean + n_scored + n_unverified + n_total + confidence_flagged + criteria list |
| **PersonaTotal** | Per-persona RSF aggregate — total + total_pct + weights_used + confidence_flagged + limited_confidence_warning |
| **ProvenanceHeader** | Identity + scan-context block at top of every report — project name + URL + commit SHA + branch + scanned_at + scorer_version + classifier output + inventory snapshot |
| **narrative_emphasis** | Profile field listing the report subjects each persona cares about (e.g. acquisition's `["integration risk", "maintenance burden", ...]`) |
| **NarrativeBlock** | Builder output for one `narrative_emphasis` term — title + summary + facts + callouts |
| **dedupe family** | Cross-detector grouping of related findings (e.g. `code_eval`, `shell_exec`, `committed_credential`) so the same issue isn't reported by 3 detectors |
| **detector pack** | A logical grouping of detectors per language or concern (Python pack, TS/JS pack, common pack, SAST pack, etc.) |
| **classification_confidence** | 0.0–1.0 float from the classifier indicating how sure it is of the archetype + maturity |
| **0.11.0 depth pass** | The session's term for the methodology + glossary + citations + score-decomposition + gap-analysis + exec-summary work that was added then partially superseded by RSF |
| **trust mechanism** | The user's discipline requirement: paste audit before code, commit removals before additions, grep output before claiming done, name mid-flight state explicitly |
| **half-measure** | Adding new substrate while leaving legacy substrate in place — produces self-contradicting output. The user's primary failure-mode label for the prior session |

---

## 29. Pending todos at handoff

```
[completed] Fix sticky-banner transparency
[completed] Fix duplicate persona-paragraph bug
[completed] Rip out legacy threshold language across renderer + builders + tests
[completed] Run RSF assessor on /tmp/AgentSentry; grep for legacy phrases
[in_progress] Persona-contextual translation of RSF top-5 findings
[pending] Bump version + CHANGELOG + PR + CI + merge + tag
```

The "persona-contextual translation" todo is the next user-visible deliverable and the user asked for it explicitly. Do not skip to release until that lands AND the user has reviewed.

---

## 30. One-paragraph summary

This is a repository-scoring CLI tool (Python 3.12) that recently underwent a substrate cutover from a self-authored 0–100 rubric to the user-provided **RSF v1.0** industry-anchored framework. The framework is correctly codified at `docs/frameworks/rsf_v1.0.md` and `sdlc_assessor/rsf/`; the 31 per-criterion scorers are correctly written for 14 sub-criteria but return `?` for 17 because the detector pipeline doesn't collect the evidence those criteria need (no SAST→RSF wiring, no OSV scan, no GitHub API integration, no DORA history walk, no SBOM generation, no real coverage analysis). Persona-distinct rendering exists at the cover/exec-summary layer; persona-distinct *body* artifacts (license matrices, pitch ingestion, DORA dashboards, JSON manifests) do not yet exist. The user's next-priority ask is persona-contextual translation of RSF top-5 findings into each reader's lens. The substantive multi-week gap is detector-pipeline expansion (highest leverage: wire the existing SAST adapters into RSF D1.2/D2.3 — that's 1 day of work that closes 2 critical sub-criteria). Trust has been damaged in this branch by repeated half-measures; rebuild it by showing audit-before-code, removals-before-additions, and grep-before-claiming-done. The user is paying attention; they will catch shortcuts. Read `docs/frameworks/rsf_v1.0.md`, the 9 feedback-memory files in `~/.claude/projects/-Users-ethanallen-SDLC-assesment/memory/`, and this document end-to-end before writing any code.

---

**End of handoff.**
