"""Phase 2/3 collector + evidence assembly engine."""

from __future__ import annotations

from pathlib import Path

from sdlc_assessor.core.io import read_json
from sdlc_assessor.detectors.registry import DetectorRegistry
from sdlc_assessor.normalizer.findings import normalize_findings


CODE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".cs"}


def _iter_files(repo_path: Path):
    for p in repo_path.rglob("*"):
        if p.is_file() and ".git" not in p.parts:
            yield p


def _inventory(repo_path: Path) -> dict:
    source_files = 0
    source_loc = 0
    test_files = 0
    for p in _iter_files(repo_path):
        if p.suffix.lower() in CODE_SUFFIXES:
            source_files += 1
            try:
                source_loc += len(p.read_text(encoding="utf-8", errors="ignore").splitlines())
            except OSError:
                pass
        if "test" in p.name.lower() or "tests" in p.parts:
            test_files += 1

    workflow_files = 0
    workflow_dir = repo_path / ".github" / "workflows"
    if workflow_dir.exists():
        workflow_files = sum(1 for _ in workflow_dir.glob("*.y*ml"))

    return {
        "source_files": source_files,
        "source_loc": source_loc,
        "test_files": test_files,
        "workflow_files": workflow_files,
        "runtime_dependencies": 0,
        "dev_dependencies": 0,
    }


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
