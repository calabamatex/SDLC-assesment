"""Detector registry."""

from __future__ import annotations

from pathlib import Path

from sdlc_assessor.detectors.common import run_common_detectors
from sdlc_assessor.detectors.dependency_hygiene import run_dependency_hygiene
from sdlc_assessor.detectors.git_history import run_git_history_detectors
from sdlc_assessor.detectors.python_pack import run_python_detectors
from sdlc_assessor.detectors.sast import run_sast_adapters
from sdlc_assessor.detectors.treesitter.go_pack import run_go_detectors
from sdlc_assessor.detectors.treesitter.rust_pack import run_rust_detectors
from sdlc_assessor.detectors.treesitter.tsjs_pack import run_tsjs_detectors


class DetectorRegistry:
    def __init__(self) -> None:
        self._detectors = [
            "common",
            "python_pack",
            "tsjs_pack",
            "go_pack",
            "rust_pack",
            "dependency_hygiene",
            "git_history",
            "sast",
        ]

    def registered(self) -> list[str]:
        return list(self._detectors)

    def run(self, repo_path: str | Path) -> list[dict]:
        path = Path(repo_path)
        findings: list[dict] = []
        findings.extend(run_common_detectors(path))
        findings.extend(run_python_detectors(path))
        findings.extend(run_tsjs_detectors(path))
        findings.extend(run_go_detectors(path))
        findings.extend(run_rust_detectors(path))
        findings.extend(run_dependency_hygiene(path))
        findings.extend(run_git_history_detectors(path))
        findings.extend(run_sast_adapters(path))
        return findings
