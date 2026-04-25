# SDLC Framework v2 — documentation

Authoritative specs for the `sdlc-assessor` framework. Profile JSON data is no longer duplicated under `docs/`; the canonical location is [`sdlc_assessor/profiles/data/`](../sdlc_assessor/profiles/data/) (see SDLC-018 in `CHANGELOG.md`).

## Files

- [`SDLC_Framework_v2_Spec.md`](SDLC_Framework_v2_Spec.md) — master architecture specification.
- [`evidence_schema.json`](evidence_schema.json) — canonical JSON Schema for evidence, findings, scoring, and blockers. A byte-equal copy is shipped at [`sdlc_assessor/core/evidence_schema.json`](../sdlc_assessor/core/evidence_schema.json) for installed-package use; `scripts/check_schema_sync.py` keeps the two in sync.
- [`scoring_engine_spec.md`](scoring_engine_spec.md) — scoring and verdict logic, including applicability and blocker behavior.
- [`renderer_template.md`](renderer_template.md) — human-readable report template.
- [`remediation_planner_spec.md`](remediation_planner_spec.md) — patch-safe remediation planner specification.
- [`detector_pack_starter_spec.md`](detector_pack_starter_spec.md) — starter design for language-specific detector packs.
- [`calibration_targets.md`](calibration_targets.md) — score bands the calibration script enforces in CI.

## Profile data (live at `sdlc_assessor/profiles/data/`)

- [`use_case_profiles.json`](../sdlc_assessor/profiles/data/use_case_profiles.json) — engineering_triage, vc_diligence, acquisition_diligence, remediation_agent.
- [`maturity_profiles.json`](../sdlc_assessor/profiles/data/maturity_profiles.json) — production, prototype, research.
- [`repo_type_profiles.json`](../sdlc_assessor/profiles/data/repo_type_profiles.json) — service, library, cli, monorepo, research_repo, sdk, infrastructure, internal_tool, unknown.

## Implementation status

The implementation order (origin-of-truth → scaffolding → calibration) is described in [`PLANS.md`](../PLANS.md) and progress against it is tracked in [`CHANGELOG.md`](../CHANGELOG.md).
