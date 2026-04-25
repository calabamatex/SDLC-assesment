"""Collector + evidence assembly engine.

Walks the repo using the same ignore-aware iterator as the detector packs
(``iter_repo_files``) so the inventory counts what the detectors actually
analyze.
"""

from __future__ import annotations

import contextlib
from pathlib import Path

from sdlc_assessor.core.io import read_json
from sdlc_assessor.detectors.common import iter_repo_files
from sdlc_assessor.detectors.registry import DetectorRegistry
from sdlc_assessor.normalizer.findings import normalize_findings

CODE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".go", ".rs", ".java", ".cs", ".kt", ".kts"}


def _is_test_file(rel_parts: tuple[str, ...], filename: str) -> bool:
    """Use only repo-relative path parts to determine test-ness."""
    if any(part in {"tests", "test", "__tests__", "spec", "specs"} for part in rel_parts):
        return True
    lower = filename.lower()
    if lower.startswith("test_") or lower.endswith("_test.py"):
        return True
    return lower.endswith((".test.ts", ".test.tsx", ".test.js", ".test.jsx", ".spec.ts", ".spec.js"))


def _inventory(repo_path: Path) -> dict:
    source_files = 0
    source_loc = 0
    test_files = 0
    largest: list[tuple[str, int]] = []
    for path in iter_repo_files(repo_path, max_file_size=10**12):
        try:
            size = path.stat().st_size
        except OSError:
            continue
        try:
            rel = path.relative_to(repo_path)
        except ValueError:
            rel = path
        rel_parts = rel.parts
        if path.suffix.lower() in CODE_SUFFIXES:
            source_files += 1
            with contextlib.suppress(OSError):
                source_loc += len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
        if _is_test_file(rel_parts, path.name):
            test_files += 1
        largest.append((rel.as_posix() if isinstance(rel, Path) else str(rel), size))

    workflow_files = 0
    workflow_jobs = 0
    workflow_dir = repo_path / ".github" / "workflows"
    if workflow_dir.exists():
        for wf in workflow_dir.glob("*.y*ml"):
            workflow_files += 1
            try:
                content = wf.read_text(encoding="utf-8", errors="ignore")
                # Crude job count: top-level keys under ``jobs:``.
                workflow_jobs += sum(
                    1
                    for line in content.splitlines()
                    if line.startswith("  ") and line.rstrip().endswith(":") and not line.startswith("    ")
                )
            except OSError:
                pass

    runtime_dependencies = 0
    dev_dependencies = 0
    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists():
        try:
            text = pyproject.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            text = ""
        runtime_dependencies = len(_dep_block(text, "dependencies"))
        dev_dependencies = sum(
            1 for line in text.splitlines() if line.lstrip().startswith("\"") and "[project.optional-dependencies]" not in line
        )

    largest.sort(key=lambda t: -t[1])
    largest_files = [{"path": p, "bytes": s} for p, s in largest[:5]]

    test_to_source_ratio = (test_files / source_files) if source_files else 0.0

    return {
        "source_files": source_files,
        "source_loc": source_loc,
        "test_files": test_files,
        "estimated_test_cases": test_files,  # crude proxy until parsing per-file occurrences lands
        "test_to_source_ratio": round(test_to_source_ratio, 2),
        "workflow_files": workflow_files,
        "workflow_jobs": workflow_jobs,
        "runtime_dependencies": runtime_dependencies,
        "dev_dependencies": dev_dependencies,
        "largest_files": largest_files,
    }


def _dep_block(text: str, key: str) -> list[str]:
    """Heuristic: extract entries from ``key = [ ... ]`` in a pyproject."""
    import re

    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=\s*\[([^\]]*)\]", re.MULTILINE | re.DOTALL)
    match = pattern.search(text)
    if not match:
        return []
    body = match.group(1)
    return [line.strip().strip(",").strip('"').strip("'") for line in body.splitlines() if line.strip().startswith(("'", '"'))]


def collect_evidence(repo_target: str, classification_path: str) -> dict:
    repo_path = Path(repo_target)
    if not repo_path.exists() or not repo_path.is_dir():
        raise ValueError(f"Repository path does not exist or is not a directory: {repo_target}")

    classification = read_json(classification_path)
    registry = DetectorRegistry()
    raw_findings = registry.run(repo_path)
    findings = normalize_findings(raw_findings)

    evidence = {
        "repo_meta": classification.get("repo_meta", {}),
        "classification": classification.get("classification", {}),
        "inventory": _inventory(repo_path),
        "findings": findings,
        "scoring": {},
        "hard_blockers": [],
    }
    return evidence
