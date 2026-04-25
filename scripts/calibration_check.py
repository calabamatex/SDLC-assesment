#!/usr/bin/env python3
"""Assert each fixture's score falls in its declared calibration band.

Wired into CI (``calibration-check`` job) and re-runnable locally:

    python scripts/calibration_check.py

Bands live in ``docs/calibration_targets.md``. The lookup table below mirrors
that file — when widening or shifting a band, update both this dict and the
docs table in the same commit.

Exit 0 on full conformance, non-zero with a diff hint otherwise.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sdlc_assessor.classifier.engine import classify_repo  # noqa: E402
from sdlc_assessor.collector.engine import collect_evidence  # noqa: E402
from sdlc_assessor.core.io import write_json  # noqa: E402
from sdlc_assessor.scorer.engine import score_evidence  # noqa: E402

# (fixture, use_case, maturity, repo_type, min_score, max_score,
#  allowed_verdicts, min_critical, min_high)
TARGETS = [
    ("tests/fixtures/fixture_empty_repo", "engineering_triage", "production", "internal_tool",
     40, 70, {"conditional_pass", "fail"}, 1, None),
    ("tests/fixtures/fixture_python_basic", "engineering_triage", "prototype", "cli",
     80, 99, {"pass_with_distinction", "pass"}, 0, 0),
    ("tests/fixtures/fixture_probable_secret", "engineering_triage", "production", "service",
     30, 60, {"conditional_pass", "fail"}, 1, None),
    ("tests/fixtures/fixture_typescript_basic", "engineering_triage", "prototype", "library",
     75, 99, {"pass_with_distinction", "pass"}, 0, 0),
    ("tests/fixtures/fixture_no_ci", "engineering_triage", "production", "library",
     50, 90, {"pass", "conditional_pass"}, 0, 1),
    ("tests/fixtures/fixture_research_repo", "engineering_triage", "research", "research_repo",
     75, 99, {"pass_with_distinction", "pass"}, 0, 0),
    ("tests/fixtures/fixture_javascript_basic", "engineering_triage", "prototype", "library",
     75, 99, {"pass_with_distinction", "pass"}, 0, 0),
    ("tests/fixtures/fixture_tsx_only", "engineering_triage", "prototype", "library",
     75, 99, {"pass_with_distinction", "pass"}, 0, 0),
    ("tests/fixtures/fixture_vendored_node_modules", "engineering_triage", "prototype", "library",
     75, 99, {"pass_with_distinction", "pass"}, 0, 0),
    ("tests/fixtures/fixture_service_archetype", "engineering_triage", "production", "service",
     50, 85, {"pass", "conditional_pass"}, None, None),
    ("tests/fixtures/fixture_library_archetype", "engineering_triage", "prototype", "library",
     80, 99, {"pass_with_distinction", "pass"}, 0, 0),
    ("tests/fixtures/fixture_monorepo_archetype", "engineering_triage", "prototype", "monorepo",
     80, 99, {"pass_with_distinction", "pass"}, 0, 0),
    ("tests/fixtures/fixture_infrastructure_archetype", "engineering_triage", "prototype", "infrastructure",
     80, 99, {"pass_with_distinction", "pass"}, 0, 0),
    ("tests/fixtures/fixture_internal_tool_archetype", "engineering_triage", "prototype", "internal_tool",
     80, 99, {"pass_with_distinction", "pass"}, 0, 0),
    ("tests/fixtures/fixture_committed_credential", "engineering_triage", "production", "service",
     30, 70, {"conditional_pass", "fail"}, 1, None),
]


def _check(target, out_dir: Path) -> tuple[bool, str]:
    repo, use_case, maturity, repo_type, lo, hi, verdicts, min_crit, min_high = target
    classification = classify_repo(repo)
    cp = out_dir / "classification.json"
    write_json(cp, classification)
    evidence = collect_evidence(repo, str(cp))
    scored = score_evidence(evidence, use_case, maturity, repo_type)
    overall = scored["scoring"]["overall_score"]
    verdict = scored["scoring"]["verdict"]
    blockers = scored.get("hard_blockers", [])
    crit = sum(1 for b in blockers if b.get("severity") == "critical")
    high = sum(1 for b in blockers if b.get("severity") == "high")

    failures: list[str] = []
    if not (lo <= overall <= hi):
        failures.append(f"score {overall} outside band [{lo}, {hi}]")
    if verdict not in verdicts:
        failures.append(f"verdict '{verdict}' not in {sorted(verdicts)}")
    if min_crit is not None and crit < min_crit:
        failures.append(f"critical_blockers {crit} < expected min {min_crit}")
    if min_high is not None and high < min_high:
        failures.append(f"high_blockers {high} < expected min {min_high}")
    summary = (
        f"{repo}: score={overall} verdict={verdict} crit={crit} high={high}"
    )
    if failures:
        summary += " | " + "; ".join(failures)
        return False, summary
    return True, summary


def main(argv: list[str] | None = None) -> int:
    out_dir = Path(".sdlc")
    out_dir.mkdir(parents=True, exist_ok=True)

    failures: list[str] = []
    for target in TARGETS:
        ok, summary = _check(target, out_dir)
        prefix = "OK  " if ok else "FAIL"
        print(f"{prefix} {summary}")
        if not ok:
            failures.append(summary)

    if failures:
        print(
            "\nCalibration check FAILED. Update the scorer or "
            "docs/calibration_targets.md (and this script) in the same commit.",
            file=sys.stderr,
        )
        return 1
    print(f"\nCalibration check OK ({len(TARGETS)} fixtures).")
    return 0


def collect_calibration_rows() -> list[dict]:
    """Helper used by tests — return the per-fixture scoring summary."""
    out_dir = Path(".sdlc")
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for target in TARGETS:
        repo, use_case, maturity, repo_type, *_ = target
        classification = classify_repo(repo)
        cp = out_dir / "classification.json"
        write_json(cp, classification)
        evidence = collect_evidence(repo, str(cp))
        scored = score_evidence(evidence, use_case, maturity, repo_type)
        rows.append(
            {
                "fixture": repo,
                "score": scored["scoring"]["overall_score"],
                "verdict": scored["scoring"]["verdict"],
                "blockers": json.dumps(scored.get("hard_blockers", [])),
            }
        )
    return rows


if __name__ == "__main__":
    raise SystemExit(main())
