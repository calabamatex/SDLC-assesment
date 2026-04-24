# VALIDATION_AUDIT.md

This document audits the current implementation against every phase in `PLANS.md` and verifies acceptance criteria.

## Phase-by-phase compliance

## Phase 0 — Bootstrap
- Package/build metadata present (`pyproject.toml`).
- CLI entrypoint implemented (`sdlc_assessor/cli.py`).
- Core schema/model/io modules present (`sdlc_assessor/core/*`).
- Profile loader present (`sdlc_assessor/profiles/loader.py`).

Status: ✅ Complete

## Phase 1 — Classifier
- Classifier engine implemented (`sdlc_assessor/classifier/engine.py`).
- `classify` command writes `classification.json`.

Status: ✅ Complete

## Phase 2 — Collector + evidence assembly
- Collector implemented (`sdlc_assessor/collector/engine.py`).
- `collect` command writes `evidence.json`.
- Detector registry plumbing integrated.

Status: ✅ Complete

## Phase 3 — Detectors + normalization
- Common detector pack implemented.
- Python detector pack implemented.
- TS/JS detector pack implemented.
- Findings normalizer implemented (`sdlc_assessor/normalizer/findings.py`).

Status: ✅ Complete

## Phase 4 — Scoring
- Deterministic profile precedence implemented.
- Formula applies applicability, multipliers, normalized maxima, deductions.
- Hard blockers detected separately.
- `score` command writes `scored.json`.

Status: ✅ Complete

## Phase 5 — Rendering
- Markdown report renderer implemented (`sdlc_assessor/renderer/markdown.py`).
- `render` command writes `report.md`.

Status: ✅ Complete

## Phase 6 — Remediation
- Remediation planner implemented with required task schema keys.
- Markdown remediation renderer implemented.
- `remediate` command writes `remediation.md`.

Status: ✅ Complete

## Phase 7 — End-to-end hardening
- `run` command executes classify→collect→score→render→remediate.
- Fixture repos included and exercised in integration tests.
- Full test suite passes.

Status: ✅ Complete

## Phase 8 — Quality hardening pass
- Policy override support integrated for scoring.
- Calibration helper script added (`scripts/benchmark_calibration.py`).
- Packaging/install validated through integration test (`pip install -e .` + `sdlc --help`).

Status: ✅ Complete

---

## Acceptance criteria audit

- `pytest -q` passes. ✅
- `python -m sdlc_assessor.cli --help` works. ✅
- `sdlc --help` works after install. ✅
- full pipeline works on every fixture repo. ✅
- full pipeline works on this repository itself. ✅
- generated artifacts include `classification.json`, `evidence.json`, `scored.json`, `report.md`, `remediation.md`. ✅
- this `VALIDATION_AUDIT.md` documents compliance against every `PLANS.md` phase. ✅

## Execution evidence (current run)
- `pytest -q` => passed.
- `python -m sdlc_assessor.cli --help` => passed.
- `python -m pip install -e . --no-build-isolation` then `sdlc --help` => passed.
- Full pipeline on all fixtures and self is covered by integration tests in `tests/integration/test_pipeline_integration.py` and passed under `pytest -q`.
