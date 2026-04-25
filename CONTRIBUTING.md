# Contributing to sdlc-assessor

Thanks for your interest. This document covers the day-to-day mechanics: setup, test, lint, type-check, and how to extend the framework with new detectors and profiles.

## Setup

```bash
git clone https://github.com/calabamatex/SDLC-assesment.git
cd SDLC-assesment
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install   # optional but recommended
```

## Running locally

```bash
pytest -q                              # full test suite (target: zero failures)
pytest -q --cov=sdlc_assessor          # with coverage
ruff check .                           # lint
ruff format .                          # autoformat
mypy sdlc_assessor/                    # type check
SDLC_STRICT=1 sdlc run <repo> ...      # raise on schema-conformance violations
python scripts/benchmark_calibration.py   # score the bundled fixtures
python scripts/calibration_check.py    # assert each fixture's score lands in target band
```

## Repository layout

```
sdlc_assessor/
  classifier/   — detect archetype, maturity, language packs
  collector/    — assemble inventory + run detector registry
  detectors/    — pluggable detector packs (common, python, tsjs, ...)
  normalizer/   — coerce raw findings into schema-compliant findings
  profiles/     — load and merge use_case × maturity × repo_type
  scorer/       — apply weights, compute deductions, identify blockers
  renderer/     — render Markdown report
  remediation/  — derive a phased remediation plan from findings
  core/         — shared schema, IO, models, enums
  cli.py        — entrypoint
docs/             — specs and JSON Schema (single source of truth)
tests/            — unit + golden tests + fixture repos
scripts/          — benchmark and calibration utilities
```

## Adding a detector

Detectors live under `sdlc_assessor/detectors/`. Each pack is a module that exposes a `run(repo_path: Path) -> list[dict]` function returning raw findings. The schema for a finding is:

```json
{
  "id": "<unique-stable-id>",
  "category": "code_quality | testing_quality | ...",
  "subcategory": "<short identifier>",
  "severity": "info | low | medium | high | critical",
  "confidence": "low | medium | high",
  "statement": "<human-readable one-liner>",
  "evidence": [{"path": "...", "line_start": 12, "line_end": 12, "snippet": "...", "match_type": "exact", "count": 1}],
  "score_impact": {"direction": "negative", "magnitude": 7, "rationale": "..."}
}
```

Steps:

1. Create `sdlc_assessor/detectors/your_pack.py` with a `run` function.
2. Register it in `sdlc_assessor/detectors/registry.py` so the collector dispatches to it.
3. Add fixture(s) under `tests/fixtures/` that exercise the new detector with both true positives and known false positives.
4. Add tests under `tests/unit/test_detectors.py` (or a sibling).
5. Run `pytest -q tests/unit/test_detectors.py` and `pytest -q tests/unit/test_schema_conformance.py`.

When writing detectors:

- Use the AST when one is available (e.g. Python's `ast` module). Avoid substring matches.
- Capture `line_start`/`line_end`/`snippet`/`count` for every finding.
- Respect the ignore-directory list defined in `sdlc_assessor/detectors/common.py` (`DEFAULT_IGNORES`).
- Cap file reads at 5 MB. Use the binary-detection helper to skip non-text files.

See [`docs/detector_pack_starter_spec.md`](docs/detector_pack_starter_spec.md) for the full contract.

## Adding a profile

Profile JSON files live at [`sdlc_assessor/profiles/data/`](sdlc_assessor/profiles/data/). Three axes:

- `use_case_profiles.json` — what the assessment is for
- `maturity_profiles.json` — production / prototype / research
- `repo_type_profiles.json` — cli / library / service / monorepo / ...

To add a profile, edit the relevant JSON file. Each profile object declares category weights, severity multipliers, and applicability flags. Then add a fixture and a test that asserts the new profile loads, merges, and produces an expected scoring distribution.

## Coding conventions

- Python 3.12+. Use `from __future__ import annotations` in every module.
- Type hints on every public function. `mypy` is part of CI.
- `ruff format` for formatting (line length 120). `ruff check` for linting.
- Deterministic JSON: use `sdlc_assessor.core.io.write_json` (which sets `sort_keys=True`).
- Tests must not depend on side effects from other tests or other commands. Use `tmp_path` and the existing `classification_json_path` fixture.

## Running pre-commit

```bash
pre-commit install
pre-commit run --all-files
```

Pre-commit runs `ruff check`, `ruff format`, `mypy`, JSON/YAML linting, and the schema-sync byte-equality check.

## Sending changes

1. Fork and create a branch (`git checkout -b feat/your-detector`).
2. Make focused commits using conventional commit messages (`feat(detectors): add go pack`, `fix(scorer): handle empty inventory`).
3. Open a pull request against `main`.
4. CI must be green. Address review comments by pushing additional commits — do not force-push during review.

## Versioning

`sdlc_assessor.__version__` (in [`sdlc_assessor/__init__.py`](sdlc_assessor/__init__.py)) and `[project].version` in [`pyproject.toml`](pyproject.toml) must always match. A unit test (`tests/unit/test_version_sync.py`) enforces this. To bump:

1. Update both `__version__` and `pyproject.toml`'s `version`.
2. Add a `CHANGELOG.md` entry under `## [X.Y.Z] - YYYY-MM-DD`.
3. Commit (`chore(release): vX.Y.Z`).
4. Tag (`git tag vX.Y.Z`) and push the tag — this triggers the release workflow.
