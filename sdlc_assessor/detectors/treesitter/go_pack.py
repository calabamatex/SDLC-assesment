"""Go detector pack (SDLC-045) — runs ``GO_RULES`` via the tree-sitter framework."""

from __future__ import annotations

from pathlib import Path

from sdlc_assessor.detectors.treesitter.framework import run_treesitter_pack
from sdlc_assessor.detectors.treesitter.rules.go_rules import GO_RULES, GO_SUFFIXES


def run_go_detectors(repo_path: Path) -> list[dict]:
    return run_treesitter_pack(
        repo_path,
        language="go",
        suffixes=GO_SUFFIXES,
        rules=GO_RULES,
        detector_source="go_pack",
    )


__all__ = ["run_go_detectors"]
