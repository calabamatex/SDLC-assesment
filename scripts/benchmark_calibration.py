#!/usr/bin/env python3
"""Run the scorer over each bundled fixture and emit a JSON summary.

Used by ``scripts/calibration_check.py`` (SDLC-026) to assert each fixture's
score lands in the band declared in ``docs/calibration_targets.md``.

Each row:
- ``fixture``                  — relative path to the fixture
- ``use_case`` / ``maturity`` / ``repo_type``
- ``overall_score`` (integer)
- ``verdict``
- ``blockers``                 — total count
- ``critical_blockers`` / ``high_blockers``
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sdlc_assessor.classifier.engine import classify_repo  # noqa: E402
from sdlc_assessor.collector.engine import collect_evidence  # noqa: E402
from sdlc_assessor.scorer.engine import score_evidence  # noqa: E402

# (fixture path, use_case, maturity, repo_type) — kept explicit so calibration
# bands can encode "this fixture under this profile" expectations.
DEFAULT_PROFILES: list[tuple[str, str, str, str]] = [
    ("tests/fixtures/fixture_empty_repo", "engineering_triage", "production", "internal_tool"),
    ("tests/fixtures/fixture_python_basic", "engineering_triage", "prototype", "cli"),
    ("tests/fixtures/fixture_probable_secret", "engineering_triage", "production", "service"),
    ("tests/fixtures/fixture_typescript_basic", "engineering_triage", "prototype", "library"),
    ("tests/fixtures/fixture_no_ci", "engineering_triage", "production", "library"),
    ("tests/fixtures/fixture_research_repo", "engineering_triage", "research", "research_repo"),
    ("tests/fixtures/fixture_javascript_basic", "engineering_triage", "prototype", "library"),
    ("tests/fixtures/fixture_tsx_only", "engineering_triage", "prototype", "library"),
    ("tests/fixtures/fixture_vendored_node_modules", "engineering_triage", "prototype", "library"),
    ("tests/fixtures/fixture_service_archetype", "engineering_triage", "production", "service"),
    ("tests/fixtures/fixture_library_archetype", "engineering_triage", "prototype", "library"),
    ("tests/fixtures/fixture_monorepo_archetype", "engineering_triage", "prototype", "monorepo"),
    ("tests/fixtures/fixture_infrastructure_archetype", "engineering_triage", "prototype", "infrastructure"),
    ("tests/fixtures/fixture_internal_tool_archetype", "engineering_triage", "prototype", "internal_tool"),
    ("tests/fixtures/fixture_committed_credential", "engineering_triage", "production", "service"),
]


def _row(repo_path: str, use_case: str, maturity: str, repo_type: str, out_dir: Path) -> dict:
    classification = classify_repo(repo_path)
    class_path = out_dir / "classification.json"
    class_path.write_text(json.dumps(classification), encoding="utf-8")
    evidence = collect_evidence(repo_path, str(class_path))
    scored = score_evidence(evidence, use_case, maturity, repo_type)
    blockers = scored.get("hard_blockers", [])
    return {
        "fixture": repo_path,
        "use_case": use_case,
        "maturity": maturity,
        "repo_type": repo_type,
        "overall_score": scored["scoring"]["overall_score"],
        "verdict": scored["scoring"]["verdict"],
        "blockers": len(blockers),
        "critical_blockers": sum(1 for b in blockers if b.get("severity") == "critical"),
        "high_blockers": sum(1 for b in blockers if b.get("severity") == "high"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score every bundled fixture.")
    parser.add_argument("--out-dir", default=".sdlc")
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = [_row(*entry, out_dir=out_dir) for entry in DEFAULT_PROFILES]
    print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
