# AGENTS.md

## Project goal
Build a production-quality, CLI-first SDLC repository assessment system from the specs in `docs/`.

## Source of truth
The source of truth is the documentation in `docs/`. Do not treat any prior scaffold outside this repo as authoritative.

## Required architecture
Implement a modular system with these components:
- classifier
- collector
- scorer
- renderer
- remediation planner
- detector packs
- profile loaders

## Output priorities
1. Human-readable output first
2. Structured JSON underneath
3. CLI-first execution
4. Agent-agnostic design

## v1 scope
Implement:
- classify
- collect
- score
- render
- remediate

## Constraints
- Do not build a GUI in v1
- Do not hardcode the system to one AI coding agent
- Do not depend on exact line numbers in remediation output
- Keep the implementation modular and testable
- Add tests for each major module
- Prefer clarity and correctness over premature optimization

## Done when
The project has:
- an installable CLI
- working end-to-end commands
- JSON outputs for internal artifacts
- markdown report output
- remediation plan output
- tests that pass locally

## Verification
Before finishing any phase:
- run tests
- run lint if configured
- verify CLI help output
- verify the end-to-end pipeline on a fixture repo
