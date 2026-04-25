#!/usr/bin/env python3
"""Assert byte-equality between the canonical and packaged evidence schema.

Two copies of ``evidence_schema.json`` exist:

- ``docs/evidence_schema.json`` — the human-authoritative copy linked from
  README and docs.
- ``sdlc_assessor/core/evidence_schema.json`` — the package-local copy
  resolved by ``load_evidence_schema()`` from installed wheels.

If they diverge, ``SDLC_STRICT=1`` validation will silently disagree depending
on whether the user is running from source or from an installed package. This
script is wired into both the CI ``schema-validate`` job and the pre-commit
hook list to prevent that drift.

Exit 0 on match, non-zero with a diff hint on mismatch.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs" / "evidence_schema.json"
PACKAGE = REPO_ROOT / "sdlc_assessor" / "core" / "evidence_schema.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if not DOCS.exists():
        print(f"ERROR: {DOCS} missing", file=sys.stderr)
        return 2
    if not PACKAGE.exists():
        print(f"ERROR: {PACKAGE} missing", file=sys.stderr)
        return 2

    docs_hash = _sha256(DOCS)
    pkg_hash = _sha256(PACKAGE)
    if docs_hash != pkg_hash:
        print(
            "ERROR: evidence_schema.json out of sync between docs/ and "
            "sdlc_assessor/core/.",
            file=sys.stderr,
        )
        print(f"  docs/    sha256 = {docs_hash}", file=sys.stderr)
        print(f"  package/ sha256 = {pkg_hash}", file=sys.stderr)
        print(
            "  Run: cp docs/evidence_schema.json sdlc_assessor/core/evidence_schema.json",
            file=sys.stderr,
        )
        return 1
    print(f"schema sync OK ({docs_hash[:16]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
