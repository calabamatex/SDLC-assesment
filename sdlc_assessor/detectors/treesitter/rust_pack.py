"""Rust detector pack (SDLC-046)."""

from __future__ import annotations

from pathlib import Path

from sdlc_assessor.detectors.treesitter.framework import run_treesitter_pack
from sdlc_assessor.detectors.treesitter.rules.rust_rules import RUST_RULES, RUST_SUFFIXES


def run_rust_detectors(repo_path: Path) -> list[dict]:
    return run_treesitter_pack(
        repo_path,
        language="rust",
        suffixes=RUST_SUFFIXES,
        rules=RUST_RULES,
        detector_source="rust_pack",
    )


__all__ = ["run_rust_detectors"]
