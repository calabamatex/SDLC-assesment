# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing yet — see Roadmap below.

### Roadmap (not yet implemented)

- Language packs for Java, C#, Kotlin (framework exists; cheap follow-up via tree-sitter rule files)
- `cargo-audit` SAST adapter for Rust dependency CVEs
- `sdlc compare repo_a repo_b` mode
- HTML renderer in addition to Markdown
- Remote profile distribution (signed packs)
- LLM-backed category narratives via the Anthropic API (deterministic path stays default)
- Cross-detector dedupe — when both a native pack and a SAST adapter flag the same line, current behaviour is to emit both findings; a future pass can collapse them

## [0.5.0] - 2026-04-26

Third Phase-8 milestone: real SAST integration. Native packs continue to provide opinionated AST-driven signal; SAST adapters layer on industry-standard tools as an additive surface. Together: native packs detect what we have *opinions* about; SAST adapters catch breadth we don't want to maintain ourselves.

### Added

- **SDLC-050: SAST adapter framework.** `sdlc_assessor/detectors/sast/framework.py` introduces a base `SASTAdapter` class. Each adapter declares its `tool_name`, `ecosystems`, `build_command`, and `parse_output`; the framework handles availability detection (graceful no-op when the tool isn't on PATH), subprocess discipline (argument-array invocation, hard timeout, captured I/O, tolerated non-zero exits), schema mapping, and an opt-in cache (`SDLC_SAST_CACHE=1` keys results on `(tool_name, version, repo-state hash)` under `.sdlc/sast-cache/`).
- **SDLC-051: bandit adapter** — Python security scanner. `bandit -r <repo> -f json`. Maps bandit's HIGH/MEDIUM/LOW severity + confidence to our schema. Each finding tagged with `bandit_<test_id>` and CWE.
- **SDLC-052: ruff adapter** — Python linter (covers SAST-grade rules under the `S` flake8-bandit subset, `B` bugbear, `F` pyflakes). `ruff check . --output-format=json --exit-zero --no-cache`. Severity inferred from rule prefix.
- **SDLC-053: eslint adapter** — JS/TS/JSX/TSX. `eslint . --format=json`. `should_run` requires an actual ESLint config in the repo; without one ESLint emits "no config" errors rather than findings, so we skip cleanly. `no-eval` and similar rule names route to `security_posture`.
- **SDLC-054: semgrep adapter** — multi-language. `semgrep scan --json --config=auto --metrics=off`. Results' `extra.metadata.category` decides whether the finding lands in `security_posture` or `code_quality_contracts`.
- Registry adds `sast` to its detector list; `run_sast_adapters()` is dispatched after the native packs.
- 16 new tests in `tests/unit/test_sast.py` covering each adapter's parse layer (mocked JSON), framework graceful-degrade paths (missing tool, wrong ecosystem, timeout, raised exceptions), and one real-binary integration test guarded by `pytest.mark.skipif(shutil.which("ruff") is None)`.

### Changed

- Detector pack count: 7 → 8 (`sast` joins the existing 7).
- `dev` and new `sast` extras pull in `bandit`, `semgrep`, and `eslint`-adjacent runtimes — but they remain opt-in. Default `pip install` doesn't pull them.
- A bad SAST adapter can no longer break the pipeline: `run_sast_adapters` wraps each adapter in a broad exception handler and surfaces the failure as a one-shot warning.

### Notes

- Findings from native packs and SAST adapters are emitted side-by-side. Same line, same issue can produce two findings. Cross-detector dedupe is intentionally deferred — it's value-additive but not load-bearing for v0.5.0.
- Tool installs have meaningful disk weight (semgrep ~150 MB, eslint depends on Node tooling). The framework's "no-op when not installed" path means nothing breaks for users who only have a subset.

## [0.4.0] - 2026-04-25

Second Phase-8 milestone: AST-driven multi-language detection. Five packs (Python stdlib + four tree-sitter) covering Python, Go, Rust, TypeScript, JSX, and JavaScript. ~40 detectable patterns vs v0.3.0's ~20.

### Added

- **SDLC-044: Tree-sitter framework.** New module `sdlc_assessor/detectors/treesitter/` with a generic query runner. Per-language packs are *data* — a list of `TreeSitterRule` entries pairing a tree-sitter S-expression query with schema metadata. Lazy import: when `tree-sitter` or `tree-sitter-language-pack` is missing, every tree-sitter pack returns `[]` with one warning per process; the CLI never crashes. New optional extra `[treesitter]` to install the deps; `[dev]` includes them automatically.
- **SDLC-045: Go detector pack.** 7 patterns: `go_panic_call` (high), `go_unsafe_pointer` (high), `go_exec_command_shell` (critical), `go_fmt_println` (low), `go_recover_without_repanic` (medium), `go_init_with_side_effects` (low), `go_todo_or_fixme` (info).
- **SDLC-046: Rust detector pack.** 7 patterns: `rust_unsafe_block` (high), `rust_unwrap_call` (medium), `rust_expect_call` (low), `rust_panic_macro` (high), `rust_dbg_macro` (low), `rust_println_macro` (info), `rust_transmute_call` (critical, supports both `mem::transmute(x)` and `mem::transmute::<A,B>(x)` forms).
- **SDLC-047: TS/JS pack rewritten on tree-sitter.** Real AST queries replace the v0.2.0 regex-with-stripper. Same v0.2.0 patterns plus four new ones tree-sitter unlocks: `eval_usage` (critical), `function_constructor` (high), `inner_html_assignment` (high), `dangerously_set_inner_html` (high, JSX/TSX). `tsconfig.json` strict-mode + `extends`-chain handling preserved unchanged. `sdlc_assessor/detectors/tsjs_pack.py` is now a thin compat re-export to the new module.
- **SDLC-048: Python pack expanded.** 6 new patterns on top of the v0.2.0 stdlib-AST baseline: `eval_or_exec` (critical), `pickle_load_untrusted` (high), `os_system_call` (high), `requests_verify_false` (high), `mutable_default_argument` (medium), `unsafe_sql_string` (high — detects string concat, f-string, and `.format()` inside `cursor.execute()`), `module_level_assert` (medium — only flags non-test files since `python -O` strips them).
- **SDLC-049: Calibration coverage.** 4 new fixtures: `fixture_go_basic` / `fixture_go_panics` / `fixture_rust_basic` / `fixture_rust_unsafe`. `scripts/calibration_check.py` and `docs/calibration_targets.md` extended with bands for all four. 19 fixtures total, all in band.

### Changed

- `sdlc_assessor/detectors/registry.py` registers 7 packs (was 5): `common`, `python_pack`, `tsjs_pack`, `go_pack`, `rust_pack`, `dependency_hygiene`, `git_history`.
- TS/JS finding line numbers may differ slightly between v0.3.0 and v0.4.0 because the AST traversal order differs from regex offsets. No semantic change.

### Tests

23 new tests across `tests/unit/test_detectors.py` covering the Python expansion (12 tests), Go/Rust/TS-tree-sitter packs (10 tests, guarded by `pytest.mark.skipif` if tree-sitter isn't installed), and the framework's no-op fallback (1 test). 131 total tests, up from 108 in v0.3.0.

## [0.3.0] - 2026-04-25

First Phase-8 milestone: dependency-graph extraction and git-history detectors. Both ship without new external tooling; both extend the schema with optional fields so v0.2.0 outputs remain valid.

### Added

- **SDLC-036: dependency graph extractor.** `sdlc_assessor/collector/dependencies.py` parses `requirements*.txt`, `pyproject.toml [project.dependencies]/[optional-dependencies]/[tool.poetry...]`, `package.json`, `Cargo.toml`, and `go.mod`, plus detects 10 lockfile formats. Output lands at `inventory.dependency_graph = {runtime, dev, lockfiles, total_packages}` per the new `dependency_entry` schema definition.
- **Three new dependency-hygiene findings** (`sdlc_assessor/detectors/dependency_hygiene.py`):
  - `lockfile_missing` (medium, `dependency_release_hygiene`) — manifest declares deps but no lockfile present for the relevant ecosystem.
  - `excessive_runtime_deps` (low, `dependency_release_hygiene`) — runtime deps exceed the soft threshold (default 50).
  - `no_dependabot_or_renovate` (low, `dependency_release_hygiene`) — no `.github/dependabot.yml` or `renovate.json` despite declared dependencies.
- **SDLC-037: git-history detectors.** `sdlc_assessor/detectors/git_history.py` shells to `git log` (with hard timeout, no shell expansion, tolerant of missing `git`) over the last 100 commits.
- **Optional `repo_meta.git_summary`** — populated by the classifier when the target is a git checkout. Carries `commits_analyzed`, `signed_commit_count`, `signing_coverage`, `bus_factor`, `top_authors`, `codeowners_present`, `codeowners_coverage`.
- **Three new git-history findings**:
  - `unsigned_commits` (medium, `security_posture`) — signing coverage < 20% with at least 5 commits in the window.
  - `bus_factor_low` (high if 1, medium if 2–3, `architecture_design`) — author concentration over the analyzed window.
  - `missing_codeowners` (low, `architecture_design`) — no `CODEOWNERS` file at any conventional path.
- **Default-branch detection** — classifier now reads `.git/HEAD` to populate `repo_meta.default_branch` instead of hardcoding `"unknown"`.
- **Schema extensions**: `inventory.dependency_graph`, `repo_meta.git_summary`, `$defs.dependency_entry`. All optional, so v0.2.0-shaped payloads still validate.
- **Registry**: `dependency_hygiene` and `git_history` join the existing 3 detector packs.
- **Tests**: 20 new tests across `test_dependencies.py` (12) and `test_git_history.py` (8 — guarded by `pytest.mark.skipif` if `git` is absent).

### Changed

- Collector inventory now uses the structured graph for `runtime_dependencies` / `dev_dependencies` counts (was a brittle pyproject regex). Coverage extends to npm/cargo/go/poetry projects, not just `[project] dependencies`.

## [0.2.0] - 2026-04-25

### Added

- `LICENSE` (MIT), `SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG.md`.
- GitHub Actions CI: `pytest`, `ruff`, `mypy`, `schema-validate`, `calibration-check`.
- GitHub Actions release workflow that builds wheel + sdist on tag push.
- Pre-commit configuration (`ruff`, `mypy`, JSON/YAML lint, schema sync check).
- `tests/unit/test_schema_conformance.py` validating evidence + scored artifacts against `docs/evidence_schema.json`.
- `sdlc_assessor.core.schema.validate_evidence_full` using `jsonschema.Draft202012Validator`. Strict mode via `SDLC_STRICT=1`.
- `_build_category_summary` emitting per-category 2–5 sentence narratives in `scored.json`.
- Real classifier inferring `repo_archetype`, `maturity_profile`, `network_exposure`, `release_surface`, `deployment_surface`, `classification_confidence`.
- `tests/fixtures/fixture_no_ci/`, `fixture_research_repo/`, `fixture_javascript_basic/`, `fixture_tsx_only/`, `fixture_vendored_node_modules/`, plus per-archetype fixtures.
- `docs/calibration_targets.md` and `scripts/calibration_check.py` enforcing fixture score bands in CI.
- `scripts/check_schema_sync.py` enforcing byte-equality between `docs/evidence_schema.json` and the package-local copy.
- `tests/unit/test_version_sync.py` asserting `__version__` and `pyproject.toml` version match.
- Broader hard-blocker rules: `unsafe_command_execution` for service/network repos, `production_missing_tests_and_ci`, `committed_credential` for `*.pem`/`*.key`/`id_rsa`.

### Changed

- `pyproject.toml` declares `[project.optional-dependencies].dev` with all dev tools, `[tool.setuptools.packages.find]`, ruff/mypy/license/readme/authors.
- Detectors now emit `score_impact = {direction, magnitude, rationale}` per the schema, replacing `magnitude_modifier`.
- Scorer emits `category_scores` as a list of objects with `{category, applicable, score, max_score, summary, key_findings}`. `overall_score` is now an integer (precise float exposed as `overall_score_precise`). `base_weights` and `applied_weights` are emitted.
- Python detector pack uses `ast.parse` / `ast.walk` instead of substring matches. Findings include `line_start`/`line_end`/`snippet`/`count`.
- TS/JS detector pack uses regex with word boundaries and a comment/string stripper. tsconfig honors `extends` chain (up to 3 levels) via `json5`. `JSON.parse` severity demoted to `info`.
- Common detectors do a single-pass walk with `DEFAULT_IGNORES`, `.gitignore` respect via `pathspec`, binary detection, 5 MB file cap, and per-match line numbers for secrets.
- Classifier language detection uses a single ignore-aware traversal. JS-only and TSX-only repos correctly trigger the TS/JS pack.
- Renderer (`sdlc_assessor/renderer/markdown.py`) consumes the list shape with one-release back-compat for the legacy dict shape (warns).
- Renderer §2 Executive Summary, §6 Top Strengths, §7 Top Risks (top-5), §10 Detailed Findings (grouped by category, severity-sorted) all derived from data — no hardcoded text.
- Remediation planner derives `phase` and `change_type` from the finding subcategory; `verification_commands`, `effort`, and `expected_score_delta` are per-task.
- Remediation Markdown renders nested lists for list-valued keys and groups by phase with headers.
- Severity weights raised: low 2, medium 5, high 10, critical 20. Confidence multipliers tightened: medium 0.9, low 0.7.
- Production-maturity flat penalties for missing CI (-10), missing README (-8), missing tests (-15) when the corresponding finding fires.
- `score_confidence` is computed from evidence density, proxy reliance, and classification confidence (was hardcoded `medium`).
- Verdict logic distinguishes critical vs high blockers: critical blockers force `conditional_pass` or worse; high blockers permit `pass` with a note.
- CLI `--maturity` and `--repo-type` are optional and default to the classifier's inferred values; the defaulted choice is logged to stderr.
- Profile JSONs are deduplicated — the canonical location is `sdlc_assessor/profiles/data/`. `docs/*.json` profile copies removed.

### Fixed

- Test isolation violation in `tests/unit/test_collector_evidence.py` (was depending on side-effect of `.sdlc/classification.json` from prior CLI runs).
- Schema-load now prefers the package-local `sdlc_assessor/core/evidence_schema.json` first, falling back to `docs/evidence_schema.json` for source-tree development.
- `_default_schema_path` works correctly when the package is installed as a wheel.
- `p.stat().st_size` was being called twice per file in the large-file detector; now cached.
- Various detector false positives (substring matches like `pprint(` flagging as `print_usage`, `Many` flagging as `Any`, etc.).

### Removed

- Redundant `sdlc` shell wrapper at repo root (the `[project.scripts]` entry already provides the `sdlc` command on install).
- Duplicate profile JSONs under `docs/`.

## [0.1.0] - 2026-01

### Added

- Initial scaffolding: 5-stage pipeline (`classify`, `collect`, `score`, `render`, `remediate`) plus `run` convenience.
- Modular package layout: classifier, collector, detectors, normalizer, profiles, scorer, renderer, remediation, core.
- Profile JSON for 4 use cases × 3 maturity levels × 8 repo types.
- Initial detector packs: common, python, typescript_javascript.
- 26 unit tests + 1 golden test; 4 fixture repos.
- Phase 8 calibration and policy override hardening (commit `70c7f62`).
- Schema loading and TS/JS strict-mode detection hardening (commit `5fcf75a`).
