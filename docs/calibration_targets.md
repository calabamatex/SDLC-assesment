# Calibration targets

`scripts/calibration_check.py` runs the full pipeline against every bundled fixture and asserts that each fixture's `overall_score` and verdict signature land in the band declared here. CI runs the check on every PR.

The bands encode three properties:

1. **Discrimination** — broken fixtures must score meaningfully below clean ones.
2. **Stability** — a fixture's band is wide enough that small detector tweaks don't churn the calibration; narrow enough that regression in scoring still trips the gate.
3. **Spirit-of-spec** — empty repos do not earn distinction; probable-secret repos score below the pass threshold; committed-credential repos surface ≥1 critical blocker.

Use cases are fixed at `engineering_triage` for these bands.

| Fixture | Maturity | Repo type | Score band | Verdict | Critical blockers | High blockers |
|---|---|---|---|---|---|---|
| `fixture_empty_repo` | production | internal_tool | 40 — 70 | conditional_pass / fail | ≥ 1 | — |
| `fixture_python_basic` | prototype | cli | 80 — 99 | pass_with_distinction / pass | 0 | 0 |
| `fixture_probable_secret` | production | service | 30 — 60 | conditional_pass / fail | ≥ 1 | — |
| `fixture_typescript_basic` | prototype | library | 75 — 99 | pass_with_distinction / pass | 0 | 0 |
| `fixture_no_ci` | production | library | 50 — 90 | pass / conditional_pass | 0 | ≥ 1 |
| `fixture_research_repo` | research | research_repo | 75 — 99 | pass_with_distinction / pass | 0 | 0 |
| `fixture_javascript_basic` | prototype | library | 75 — 99 | pass_with_distinction / pass | 0 | 0 |
| `fixture_tsx_only` | prototype | library | 75 — 99 | pass_with_distinction / pass | 0 | 0 |
| `fixture_vendored_node_modules` | prototype | library | 75 — 99 | pass_with_distinction / pass | 0 | 0 |
| `fixture_service_archetype` | production | service | 50 — 85 | pass / conditional_pass | — | — |
| `fixture_library_archetype` | prototype | library | 80 — 99 | pass_with_distinction / pass | 0 | 0 |
| `fixture_monorepo_archetype` | prototype | monorepo | 80 — 99 | pass_with_distinction / pass | 0 | 0 |
| `fixture_infrastructure_archetype` | prototype | infrastructure | 80 — 99 | pass_with_distinction / pass | 0 | 0 |
| `fixture_internal_tool_archetype` | prototype | internal_tool | 80 — 99 | pass_with_distinction / pass | 0 | 0 |
| `fixture_committed_credential` | production | service | 30 — 70 | conditional_pass / fail | ≥ 1 | — |

## How to update

If a calibration band needs to widen or shift, that's a deliberate decision — change the band here, capture the rationale in `CHANGELOG.md` under `[Unreleased]`, and re-run the check locally. Bands should rarely change: if every other day someone is loosening a band, the scorer is calibrated for the wrong distribution and the fix is in the scoring engine, not in this file.

When adding a new fixture:

1. Add its directory under `tests/fixtures/`.
2. Add it to the `DEFAULT_PROFILES` list in `scripts/benchmark_calibration.py`.
3. Add its row here.
4. Add a row to the lookup table at the top of `scripts/calibration_check.py`.
