# sdlc-assessor

An evidence-driven SDLC repository assessment framework. `sdlc-assessor` runs a five-stage pipeline (classify → collect → score → render → remediate) against a repository, emits machine-readable JSON artifacts, a Markdown report, and a remediation plan tied to detector findings.

The framework, profiles, and scoring rules are specified in [`docs/SDLC_Framework_v2_Spec.md`](docs/SDLC_Framework_v2_Spec.md). The output schema is [`docs/evidence_schema.json`](docs/evidence_schema.json).

## Status

This is `v0.1` — the scaffolding is in place and the CLI runs end-to-end, but several detectors and the scorer are still under active calibration. See [`CHANGELOG.md`](CHANGELOG.md) and the **Roadmap** section below for what's done vs in progress.

## Install

Requires Python 3.12+.

```bash
git clone https://github.com/calabamatex/SDLC-assesment.git
cd SDLC-assesment
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

This installs the package in editable mode plus development dependencies (`pytest`, `jsonschema`, `mypy`, `ruff`, `pathspec`, `pyyaml`, `json5`, `pre-commit`). The console entrypoint `sdlc` is wired up automatically.

## Quickstart

Run the full pipeline against a fixture repo:

```bash
sdlc run tests/fixtures/fixture_python_basic \
    --use-case engineering_triage \
    --maturity prototype \
    --repo-type cli \
    --out-dir ./.sdlc
```

This writes five artifacts to `./.sdlc/`:

| File | Contents |
|---|---|
| `classification.json` | Inferred archetype, maturity, release surface, language packs |
| `evidence.json` | Inventory + raw findings per detector |
| `scored.json` | Category scores, overall score, verdict, hard blockers |
| `report.md` | Human-readable Markdown report |
| `remediation.md` | Phased remediation plan with verification commands |

## CLI reference

| Subcommand | Inputs | Outputs |
|---|---|---|
| `classify <repo>` | repo path | `classification.json` |
| `collect <repo> --classification <path>` | repo path + classification.json | `evidence.json` |
| `score <evidence> --use-case <id> [--maturity <id>] [--repo-type <id>]` | evidence.json + profile selectors | `scored.json` |
| `render <scored>` | scored.json | `report.md` |
| `remediate <scored>` | scored.json | `remediation.md` |
| `run <repo> --use-case <id>` | repo path + use case | all five artifacts |

Append `--json` to `classify`/`collect`/`score` to also write the JSON artifact. `--maturity` and `--repo-type` default to the classifier's inferred values when omitted.

## Profiles

Three orthogonal axes define how scoring is weighted:

- **Use case** (4 — `engineering_triage`, `acquisition_diligence`, `vc_diligence`, `compliance_audit`)
- **Maturity** (3 — `prototype`, `production`, `research`)
- **Repo type** (8 — `cli`, `library`, `service`, `monorepo`, `research_repo`, `infrastructure`, `published_package`, `unknown`)

Profile data lives at [`sdlc_assessor/profiles/data/`](sdlc_assessor/profiles/data/). Each profile JSON declares category weights, severity multipliers, and applicability rules. The use-case × maturity × repo-type triple is merged into a single effective profile by `sdlc_assessor.profiles.loader.build_effective_profile`.

## Documentation

- [`docs/SDLC_Framework_v2_Spec.md`](docs/SDLC_Framework_v2_Spec.md) — overall framework
- [`docs/scoring_engine_spec.md`](docs/scoring_engine_spec.md) — scoring rules, severity weights, blockers
- [`docs/remediation_planner_spec.md`](docs/remediation_planner_spec.md) — remediation task schema and phase ordering
- [`docs/renderer_template.md`](docs/renderer_template.md) — Markdown report template
- [`docs/detector_pack_starter_spec.md`](docs/detector_pack_starter_spec.md) — how to author a detector pack
- [`docs/evidence_schema.json`](docs/evidence_schema.json) — JSON Schema for evidence and scored artifacts

## Development

```bash
pytest -q                              # run the test suite
pytest -q --cov=sdlc_assessor          # with coverage
ruff check .                           # lint
mypy sdlc_assessor/                    # type check
SDLC_STRICT=1 sdlc run ...             # raise on schema-conformance violations
python scripts/benchmark_calibration.py    # score the bundled fixtures
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for instructions on adding detectors and profiles, and [`PLANS.md`](PLANS.md) for the architecture rationale.

## Roadmap

The following are **not yet implemented** and are tracked in `CHANGELOG.md` `[Unreleased]`:

- Language packs for Go, Rust, Java, C#, Kotlin
- Real SAST integration (`semgrep`, `bandit`, `eslint`, `cargo-audit`) feeding the common schema
- Dependency graph extraction from `requirements.txt`, `package-lock.json`, `Cargo.lock`
- Git-history detectors (commit signing, CODEOWNERS coverage, bus-factor)
- `sdlc compare repo_a repo_b` mode
- HTML renderer in addition to Markdown
- Remote profile distribution (signed packs)
- LLM-backed category narratives via the Anthropic API (deterministic path stays default)

## Security

To report a vulnerability, see [`SECURITY.md`](SECURITY.md).

## License

MIT. See [`LICENSE`](LICENSE).
