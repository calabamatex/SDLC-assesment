# PLANS.md — Implementation-Grade Build Plan (v1)

## Scope
This is an execution-ready build plan for a CLI-first SDLC repository assessment system.
No code is written in this document.

Docs in `docs/` are the source of truth.

---

## v1 invariants
1. CLI-first.
2. Human-readable output first (Markdown), structured JSON underneath.
3. Required commands: `classify`, `collect`, `score`, `render`, `remediate`.
4. Modular profiles: use-case, maturity, repo-type.
5. Language-agnostic core with detector packs.
6. Agent-agnostic tool layer.
7. No GUI in v1.
8. Remediation guidance uses stable anchors, not exact line-number dependence.

---

## Implementation language
**Python 3.12+**

---

## Final project structure (v1, as built)

```text
sdlc-assessor/
  PLANS.md
  pyproject.toml
  README.md
  CHANGELOG.md
  CONTRIBUTING.md
  SECURITY.md
  LICENSE
  .pre-commit-config.yaml
  .github/
    workflows/
      ci.yml
      release.yml
  docs/
    SDLC_Framework_v2_Spec.md
    scoring_engine_spec.md
    remediation_planner_spec.md
    renderer_template.md
    detector_pack_starter_spec.md
    evidence_schema.json
    calibration_targets.md

  sdlc_assessor/                 # flat layout (no src/), per pyproject.toml
    __init__.py                  # __version__ exposed
    cli.py                       # `run` is inlined here, not in pipeline/run_single.py
    core/
      __init__.py                # re-exports load_evidence_schema, validate_evidence_full
      schema.py                  # package-local-first schema resolution
      io.py
      models.py
      enums.py
      evidence_schema.json       # byte-equal copy of docs/evidence_schema.json
    profiles/
      loader.py                  # use_case × maturity × repo_type loader
      data/
        use_case_profiles.json
        maturity_profiles.json
        repo_type_profiles.json
    classifier/
      engine.py                  # real archetype/network/maturity inference (SDLC-016)
    collector/
      engine.py
    detectors/
      registry.py
      common.py                  # single-pass walker, ignore-dirs, pathspec
      python_pack.py             # ast-based (SDLC-019)
      tsjs_pack.py               # regex with boundaries + tsconfig extends chain (SDLC-020)
    normalizer/
      findings.py                # severity → magnitude mapping
    scorer/
      engine.py                  # category_scores as list, int overall_score, summaries
      precedence.py
      blockers.py                # 6 blocker rules per scoring_engine_spec
      policy.py
    renderer/
      markdown.py                # 11-section template (SDLC-023)
    remediation/
      planner.py                 # subcategory→change_type/phase mapping (SDLC-024)
      markdown.py                # phase-grouped, nested-list rendering (SDLC-025)

  scripts/
    benchmark_calibration.py
    calibration_check.py         # CI gate for fixture score bands
    check_schema_sync.py         # CI gate for evidence_schema.json equality

  tests/
    conftest.py                  # `classification_json_path` shared fixture
    unit/
      test_classifier.py
      test_cli.py
      test_collector_evidence.py
      test_core_schema.py
      test_detectors.py
      test_phase8_policy.py
      test_profiles_loader.py
      test_remediation.py
      test_schema_conformance.py
      test_scorer_blockers.py
      test_version_sync.py
    golden/
      test_report_render.py
    fixtures/                    # 15 fixture repos (see scripts/calibration_check.py)
```

Differences from the original plan:

- **No `src/` prefix.** The `pyproject.toml` `[tool.setuptools.packages.find]` now points at the flat `sdlc_assessor/` directory and works from a fresh clone.
- **No `pipeline/run_single.py`.** The `run` subcommand is inlined directly in `cli.py` because the orchestration was small enough to live next to argument parsing.
- **No `profiles/merger.py`.** Profile merge is performed inline by `scorer/precedence.py::build_effective_profile` plus `scorer/policy.py`.
- **Profile JSONs are not duplicated.** They live only at `sdlc_assessor/profiles/data/`. The `docs/` copies were removed (SDLC-018).
- **Schema lives in two places by design.** `docs/evidence_schema.json` is the human-edited canonical copy; `sdlc_assessor/core/evidence_schema.json` is shipped in the wheel. `scripts/check_schema_sync.py` enforces byte equality.

---

## Exact v1 artifact names
All artifacts are written under `./.sdlc/`.

1. `classification.json`
2. `evidence.json`
3. `scored.json`
4. `report.md`
5. `remediation.md`

Artifact flow:
`classification.json` + detector/collector data -> `evidence.json` -> `scored.json` -> `report.md` / `remediation.md`.

---

## Exact CLI examples (every command)

### classify
```bash
sdlc classify ./tests/fixtures/fixture_python_basic --out ./.sdlc/classification.json --json
```

### collect
```bash
sdlc collect ./tests/fixtures/fixture_python_basic --classification ./.sdlc/classification.json --out ./.sdlc/evidence.json --json
```

### score
```bash
sdlc score ./.sdlc/evidence.json \
  --use-case engineering_triage \
  --maturity production \
  --repo-type service \
  --out ./.sdlc/scored.json --json
```

### render
```bash
sdlc render ./.sdlc/scored.json --format markdown --out ./.sdlc/report.md
```

### remediate
```bash
sdlc remediate ./.sdlc/scored.json --format markdown --out ./.sdlc/remediation.md
```

### end-to-end helper (v1 convenience)
```bash
sdlc run ./tests/fixtures/fixture_python_basic \
  --use-case engineering_triage \
  --maturity production \
  --repo-type service \
  --out-dir ./.sdlc
```

---

## Exact v1 detector list

### common detectors
1. probable secrets
2. large files
3. committed artifacts
4. missing CI
5. missing README
6. missing SECURITY.md

### Python detectors
1. `Any`
2. `type: ignore`
3. bare `except`
4. broad `except Exception`
5. `print` usage
6. `subprocess` with `shell=True`

### TypeScript/JavaScript detectors
1. `as any`
2. `console.*`
3. empty `catch`
4. `JSON.parse`
5. `exec` / `execSync`
6. missing strict mode

---

## Exact scoring precedence and deterministic merge order

Profile precedence for final scoring configuration is deterministic:

1. **use-case profile** (base multipliers + thresholds)
2. **maturity profile** (category applicability + severity behavior)
3. **repo-type profile** (final applicability overrides)

Deterministic merge algorithm:
1. Load use-case profile into `effective_config`.
2. Apply maturity profile fields on top of `effective_config`.
3. Apply repo-type profile overrides last.
4. If conflicts remain at same key level, last writer wins (repo-type).
5. Persist effective merged config into `scored.json` metadata for auditability.

---

## Exact score formula (v1)

Given categories `C`.

1. Determine applicability per category after precedence merge:
   - `applicable`
   - `partially_applicable`
   - `not_applicable`

2. For each applicable or partially applicable category `c`:
   - base max points `base_max_c`
   - use-case multiplier `u_c`
   - weighted max `weighted_max_c = base_max_c * u_c`

3. Effective denominator:
`denominator = sum(weighted_max_c for applicable/partially_applicable categories)`

4. Normalize category max:
`normalized_max_c = 100 * weighted_max_c / denominator`

5. Deductions per finding `f` in category `c`:
`deduction_f = severity_weight_f * confidence_multiplier_f * maturity_multiplier * magnitude_modifier_f`

6. Category score:
`category_score_c = clamp(normalized_max_c - sum(deduction_f) + bounded_credits_c, 0, normalized_max_c)`

7. Raw final score:
`raw_score = sum(category_score_c)`

8. Hard blockers:
- hard blockers are reported separately in `scored.json` and report output
- blocker presence affects verdict, not direct arithmetic subtraction

9. Final normalized score:
`final_score = round(raw_score, 2)`

10. Verdict:
- compare `final_score` against use-case thresholds
- downgrade verdict if blocker rules require it

---

## Exact remediation task schema (v1)
Each remediation task entry must contain exactly these keys:

- `id`
- `phase`
- `priority`
- `linked_finding_ids`
- `target_paths`
- `anchor_guidance`
- `change_type`
- `rationale`
- `implementation_steps`
- `test_requirements`
- `verification_commands`

Rendered remediation output (`remediation.md`) must serialize tasks in this schema order.

---

## Exact fixture repos (v1)
Under `tests/fixtures/` create and use:

1. `fixture_empty_repo`
2. `fixture_python_basic`
3. `fixture_typescript_basic`
4. `fixture_no_ci`
5. `fixture_probable_secret`
6. `fixture_research_repo`

---

## 8 executable phases (0–7)

## Phase 0 — Bootstrap
### Deliverables
- package skeleton
- CLI entrypoint
- core schema/models/io
- profile loader

### Exact verification commands
```bash
python -m sdlc_assessor.cli --help
pytest -q tests/unit -k "core or profiles"
```

---

## Phase 1 — Classifier
### Deliverables
- classifier engine
- `classify` command producing `classification.json`

### Exact verification commands
```bash
sdlc classify ./tests/fixtures/fixture_empty_repo --out ./.sdlc/classification.json --json
pytest -q tests/unit -k classifier
```

---

## Phase 2 — Collector + evidence assembly
### Deliverables
- collector engine
- detector registry plumbing
- `collect` command producing `evidence.json`

### Exact verification commands
```bash
sdlc collect ./tests/fixtures/fixture_python_basic --classification ./.sdlc/classification.json --out ./.sdlc/evidence.json --json
pytest -q tests/unit -k "collector or evidence"
```

---

## Phase 3 — v1 detector implementation
### Deliverables
- all common detectors
- Python detectors
- TypeScript/JavaScript detectors
- finding normalization into evidence format

### Exact verification commands
```bash
pytest -q tests/unit -k detectors
sdlc collect ./tests/fixtures/fixture_probable_secret --classification ./.sdlc/classification.json --out ./.sdlc/evidence.json --json
```

---

## Phase 4 — Scorer
### Deliverables
- precedence merge logic
- formula implementation
- hard blocker and verdict logic
- `score` command producing `scored.json`

### Exact verification commands
```bash
sdlc score ./.sdlc/evidence.json --use-case engineering_triage --maturity production --repo-type service --out ./.sdlc/scored.json --json
pytest -q tests/unit -k "scorer or blockers"
```

---

## Phase 5 — Renderer
### Deliverables
- markdown renderer implementing report template
- `render` command producing `report.md`

### Exact verification commands
```bash
sdlc render ./.sdlc/scored.json --format markdown --out ./.sdlc/report.md
pytest -q tests/golden -k report
```

---

## Phase 6 — Remediation planner
### Deliverables
- remediation planner with exact schema
- markdown remediation rendering
- `remediate` command producing `remediation.md`

### Exact verification commands
```bash
sdlc remediate ./.sdlc/scored.json --format markdown --out ./.sdlc/remediation.md
pytest -q tests/unit -k remediation
```

---

## Phase 7 — End-to-end hardening
### Deliverables
- fixture-based full pipeline runs
- packaging + installability checks
- full passing tests

### Exact verification commands
```bash
sdlc run ./tests/fixtures/fixture_typescript_basic --use-case engineering_triage --maturity prototype --repo-type cli --out-dir ./.sdlc
pytest -q
python -m sdlc_assessor.cli --help
```

---

## Milestones
- **M1:** phases 0–2 complete (`classification.json`, `evidence.json` produced).
- **M2:** phases 3–4 complete (`scored.json` produced with deterministic scoring).
- **M3:** phases 5–6 complete (`report.md`, `remediation.md` produced).
- **M4:** phase 7 complete (all fixture pipelines and tests passing).

---

## Deferred after v1
Non-v1 items are deferred and intentionally excluded from this build plan:
- HTML renderer
- comparison mode
- additional language packs beyond Python and TypeScript/JavaScript
- remote plugin distribution/signing
- organization policy override packs

---

## Done criteria
Done when all are true:
1. Installable CLI exists.
2. Commands work: classify, collect, score, render, remediate.
3. Exact artifacts are produced: `classification.json`, `evidence.json`, `scored.json`, `report.md`, `remediation.md`.
4. Required v1 detectors are implemented exactly as listed.
5. Scoring precedence and score formula are implemented exactly as specified.
6. Remediation tasks follow the exact schema.
7. Fixture repos run successfully.
8. Tests pass locally.

## Post-v0.1 status

The v0.2.0 remediation effort (tasks SDLC-001..035) is captured in [`CHANGELOG.md`](CHANGELOG.md) under `[0.2.0]`. It addresses every issue identified in the [analysis report](docs/ANALYSIS.md), driven by the [action plan](docs/ACTION_PLAN.md), and grounds each fix in a verification command. The original v1 specification above is preserved verbatim for historical reference; for current behaviour, defer to `CHANGELOG.md`, the docs in `docs/`, and the live source.
