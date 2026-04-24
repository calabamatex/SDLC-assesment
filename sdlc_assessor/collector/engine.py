"""Collector and evidence assembly engine."""

from __future__ import annotations

import json
import subprocess
from collections import Counter
from pathlib import Path

from sdlc_assessor.core.io import read_json
from sdlc_assessor.detectors.registry import DetectorRegistry
from sdlc_assessor.normalizer.findings import normalize_findings

CODE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".cs"}


def _iter_files(repo_path: Path):
    for p in repo_path.rglob("*"):
        if p.is_file() and ".git" not in p.parts:
            yield p


def _git_count(repo_path: Path, args: list[str]) -> int:
    try:
        out = subprocess.check_output(["git", "-C", str(repo_path), *args], text=True, stderr=subprocess.DEVNULL)
        return len([line for line in out.splitlines() if line.strip()])
    except Exception:
        return 0


def _detect_dependencies(repo_path: Path) -> tuple[int, int]:
    runtime = 0
    dev = 0

    package_json = repo_path / "package.json"
    if package_json.exists():
        data = json.loads(package_json.read_text(encoding="utf-8", errors="ignore"))
        runtime += len(data.get("dependencies", {}))
        dev += len(data.get("devDependencies", {}))

    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8", errors="ignore")
        runtime += text.count("dependencies")
        dev += text.count("optional-dependencies")

    reqs = repo_path / "requirements.txt"
    if reqs.exists():
        runtime += len([l for l in reqs.read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip() and not l.startswith("#")])

    return runtime, dev


def _language_breakdown(repo_path: Path) -> list[dict]:
    counts = Counter()
    for p in _iter_files(repo_path):
        if p.suffix.lower() in CODE_SUFFIXES:
            counts[p.suffix.lower()] += 1
    total = sum(counts.values()) or 1
    mapping = {
        ".py": "Python",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".js": "JavaScript",
        ".jsx": "JavaScript",
        ".go": "Go",
        ".rs": "Rust",
        ".java": "Java",
        ".cs": "C#",
    }
    folded = Counter()
    for ext, c in counts.items():
        folded[mapping.get(ext, ext)] += c
    return [{"name": k, "percent": round((v / total) * 100, 2)} for k, v in folded.items()]


def _inventory(repo_path: Path) -> dict:
    source_files = 0
    source_loc = 0
    test_files = 0
    for p in _iter_files(repo_path):
        if p.suffix.lower() in CODE_SUFFIXES:
            source_files += 1
            source_loc += len(p.read_text(encoding="utf-8", errors="ignore").splitlines())
        if "test" in p.name.lower() or "tests" in p.parts:
            test_files += 1

    workflow_files = 0
    workflow_jobs = 0
    workflow_dir = repo_path / ".github" / "workflows"
    if workflow_dir.exists():
        workflows = list(workflow_dir.glob("*.y*ml"))
        workflow_files = len(workflows)
        for wf in workflows:
            text = wf.read_text(encoding="utf-8", errors="ignore")
            workflow_jobs += text.count("jobs:")

    runtime_dependencies, dev_dependencies = _detect_dependencies(repo_path)

    return {
        "source_files": source_files,
        "source_loc": source_loc,
        "test_files": test_files,
        "estimated_test_cases": max(test_files, 0),
        "test_to_source_ratio": round((test_files / source_files), 3) if source_files else 0.0,
        "workflow_files": workflow_files,
        "workflow_jobs": workflow_jobs,
        "runtime_dependencies": runtime_dependencies,
        "dev_dependencies": dev_dependencies,
    }


def collect_evidence(repo_target: str, classification_path: str) -> dict:
    repo_path = Path(repo_target)
    if not repo_path.exists() or not repo_path.is_dir():
        raise ValueError(f"Repository path does not exist or is not a directory: {repo_target}")

    classification_doc = read_json(classification_path)
    repo_meta = classification_doc.get("repo_meta", {})
    repo_meta["commit_count"] = _git_count(repo_path, ["rev-list", "--count", "HEAD"])
    repo_meta["tag_count"] = _git_count(repo_path, ["tag", "--list"])
    repo_meta["release_count"] = repo_meta.get("tag_count", 0)
    repo_meta["languages"] = _language_breakdown(repo_path)

    registry = DetectorRegistry()
    raw_findings = registry.run(repo_path)
    findings = normalize_findings(raw_findings)

    evidence = {
        "repo_meta": repo_meta,
        "classification": classification_doc.get("classification", {}),
        "inventory": _inventory(repo_path),
        "findings": findings,
        "scoring": {},
        "hard_blockers": [],
    }
    return evidence
