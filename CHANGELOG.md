# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Tracks the v0.2.0 remediation effort. Items move into [0.2.0] on release.

### Roadmap (not yet implemented)

- Language packs for Go, Rust, Java, C#, Kotlin
- Real SAST integration (`semgrep`, `bandit`, `eslint`, `cargo-audit`) feeding the common schema
- Dependency graph extraction from `requirements.txt`, `package-lock.json`, `Cargo.lock`
- Git-history detectors (commit signing, CODEOWNERS coverage, bus-factor)
- `sdlc compare repo_a repo_b` mode
- HTML renderer in addition to Markdown
- Remote profile distribution (signed packs)
- LLM-backed category narratives via the Anthropic API (deterministic path stays default)

## [0.2.0] - Unreleased

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
