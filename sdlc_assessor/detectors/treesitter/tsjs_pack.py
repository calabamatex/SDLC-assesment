"""Tree-sitter-based TS/JS detector pack (SDLC-047).

Replaces ``sdlc_assessor.detectors.tsjs_pack`` (regex stripper). Same finding
surface plus four new patterns the regex approach couldn't reliably catch:
``eval_usage``, ``function_constructor``, ``inner_html_assignment``,
``dangerously_set_inner_html``.

The tsconfig ``missing_strict_mode`` check is preserved unchanged (it's a
JSON inspection, not an AST query).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from sdlc_assessor.detectors.common import iter_repo_files
from sdlc_assessor.detectors.treesitter.framework import run_treesitter_pack
from sdlc_assessor.detectors.treesitter.rules.tsjs_rules import (
    JS_RULES,
    JS_SUFFIXES,
    TS_RULES,
    TS_SUFFIXES,
    TSX_RULES,
    TSX_SUFFIXES,
)
from sdlc_assessor.normalizer.findings import build_score_impact


def _has_any_tsjs(repo_path: Path) -> bool:
    target_suffixes = JS_SUFFIXES + TS_SUFFIXES + TSX_SUFFIXES
    return any(
        path.suffix.lower() in target_suffixes
        for path in iter_repo_files(repo_path)
    )


def _load_tsconfig_text(path: Path) -> dict | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    try:
        import json5

        return json5.loads(text)
    except ImportError:
        # Strip JSONC features as a fallback.
        stripped = re.sub(r"//[^\n]*", "", text)
        stripped = re.sub(r"/\*.*?\*/", "", stripped, flags=re.DOTALL)
        stripped = re.sub(r",(\s*[}\]])", r"\1", stripped)
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return None
    except Exception:
        return None


def _resolve_strict(tsconfig_path: Path, *, depth: int = 0) -> bool:
    if depth > 3:
        return False
    cfg = _load_tsconfig_text(tsconfig_path)
    if cfg is None:
        return False
    compiler = cfg.get("compilerOptions", {}) or {}
    if compiler.get("strict") is True:
        return True
    strict_subflags = (
        "noImplicitAny",
        "strictNullChecks",
        "strictFunctionTypes",
        "strictBindCallApply",
        "strictPropertyInitialization",
        "noImplicitThis",
        "alwaysStrict",
    )
    if all(compiler.get(flag) is True for flag in strict_subflags):
        return True
    extends = cfg.get("extends")
    if isinstance(extends, str):
        candidates = [extends]
    elif isinstance(extends, list):
        candidates = [e for e in extends if isinstance(e, str)]
    else:
        candidates = []
    for candidate in candidates:
        if not candidate.endswith(".json"):
            candidate = candidate + ".json"
        ext_path = (tsconfig_path.parent / candidate).resolve()
        if ext_path.exists() and _resolve_strict(ext_path, depth=depth + 1):
            return True
    return False


def run_tsjs_detectors(repo_path: Path | str) -> list[dict]:
    repo_path = Path(repo_path)
    findings: list[dict] = []

    if not _has_any_tsjs(repo_path):
        return findings

    findings.extend(
        run_treesitter_pack(
            repo_path,
            language="javascript",
            suffixes=JS_SUFFIXES,
            rules=JS_RULES,
            detector_source="tsjs_pack",
        )
    )
    findings.extend(
        run_treesitter_pack(
            repo_path,
            language="typescript",
            suffixes=TS_SUFFIXES,
            rules=TS_RULES,
            detector_source="tsjs_pack",
        )
    )
    findings.extend(
        run_treesitter_pack(
            repo_path,
            language="tsx",
            suffixes=TSX_SUFFIXES,
            rules=TSX_RULES,
            detector_source="tsjs_pack",
        )
    )

    tsconfig = repo_path / "tsconfig.json"
    if tsconfig.exists() and not _resolve_strict(tsconfig):
        findings.append(
            {
                "category": "code_quality_contracts",
                "subcategory": "missing_strict_mode",
                "severity": "medium",
                "statement": "TypeScript strict mode not enabled.",
                "evidence": [{"path": "tsconfig.json", "match_type": "derived"}],
                "confidence": "high",
                "applicability": "applicable",
                "score_impact": build_score_impact(
                    "medium",
                    rationale="TypeScript strict mode disabled or absent in tsconfig.",
                ),
                "detector_source": "tsjs_pack.missing_strict_mode",
            }
        )

    return findings


__all__ = ["run_tsjs_detectors"]
