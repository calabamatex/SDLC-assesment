"""Compatibility re-export: TS/JS detectors moved to ``treesitter.tsjs_pack`` in v0.4.0.

The v0.2.0/v0.3.0 module lived here as a regex-with-stripper implementation
(SDLC-020). v0.4.0 (SDLC-047) replaced it with a real tree-sitter AST-driven
pack. This shim preserves the import path so external tooling continues to
work; new code should import from ``sdlc_assessor.detectors.treesitter.tsjs_pack``.
"""

from __future__ import annotations

from sdlc_assessor.detectors.treesitter.tsjs_pack import run_tsjs_detectors

__all__ = ["run_tsjs_detectors"]
