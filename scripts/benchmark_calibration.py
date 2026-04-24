#!/usr/bin/env python3
"""Phase 8 calibration helper over fixture repositories."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sdlc_assessor.classifier.engine import classify_repo
from sdlc_assessor.collector.engine import collect_evidence
from sdlc_assessor.scorer.engine import score_evidence

FIXTURES = [
    "tests/fixtures/fixture_empty_repo",
    "tests/fixtures/fixture_python_basic",
    "tests/fixtures/fixture_probable_secret",
    "tests/fixtures/fixture_typescript_basic",
]


def main() -> int:
    rows = []
    out_dir = Path(".sdlc")
    out_dir.mkdir(exist_ok=True)

    for fixture in FIXTURES:
        classification = classify_repo(fixture)
        class_path = out_dir / "classification.json"
        class_path.write_text(json.dumps(classification), encoding="utf-8")
        evidence = collect_evidence(fixture, str(class_path))
        scored = score_evidence(evidence, "engineering_triage", "prototype", "cli")
        rows.append(
            {
                "fixture": fixture,
                "overall_score": scored["scoring"]["overall_score"],
                "verdict": scored["scoring"]["verdict"],
                "blockers": len(scored.get("hard_blockers", [])),
            }
        )

    print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
