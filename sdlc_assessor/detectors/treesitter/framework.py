"""Tree-sitter detector framework (SDLC-044).

A small, generic runner that turns per-language *rule data* into schema-shaped
findings. Each language pack defines a list of :class:`TreeSitterRule` entries;
the framework loads the parser, runs each rule's query, and emits one finding
per rule when the query produces at least one capture.

Lazy import: ``tree-sitter`` and ``tree-sitter-language-pack`` are optional.
If either is unavailable, every tree-sitter pack returns ``[]`` and a single
warning is emitted (once per process). The CLI still works; the affected
findings just don't surface.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sdlc_assessor.detectors.common import iter_repo_files
from sdlc_assessor.normalizer.findings import build_score_impact

_DEPS_AVAILABLE: bool | None = None
_WARNED = False


@dataclass(slots=True)
class TreeSitterRule:
    """One detector rule for a tree-sitter pack.

    ``query`` is a tree-sitter S-expression. The framework runs it against
    every parsed file and emits a finding when at least one capture matches
    ``primary_capture`` (default ``"match"``).

    ``post_filter`` is an optional callable that receives each captured node
    and returns ``True`` to keep it. Useful for rules where tree-sitter's
    ``#match?`` predicate behaves inconsistently across grammar versions.
    """

    subcategory: str
    query: str
    severity: str
    category: str
    statement: str
    primary_capture: str = "match"
    rationale: str | None = None
    confidence: str = "high"
    tags: list[str] = field(default_factory=list)
    post_filter: Callable[[Any], bool] | None = None


def _ensure_deps() -> bool:
    """Return True when tree-sitter is importable; warn once on miss.

    Some tree-sitter-language-pack releases raise non-ImportError exceptions
    at import time (binary loader issues on certain libc versions, missing
    grammar entry points, etc.). We catch broadly and surface the *actual*
    exception in the warning so the CI diagnosis isn't a guessing game.
    """
    global _DEPS_AVAILABLE, _WARNED
    if _DEPS_AVAILABLE is not None:
        return _DEPS_AVAILABLE
    try:
        import tree_sitter  # noqa: F401
        import tree_sitter_language_pack  # noqa: F401
    except Exception as exc:  # ImportError, OSError, RuntimeError, etc.
        if not _WARNED:
            warnings.warn(
                f"tree-sitter or tree-sitter-language-pack failed to import "
                f"({type(exc).__name__}: {exc}); language packs (Go, Rust, "
                f"TS/JS) are disabled. Install the [treesitter] or [dev] "
                f"extra to enable them.",
                stacklevel=2,
            )
            _WARNED = True
        _DEPS_AVAILABLE = False
        return False
    _DEPS_AVAILABLE = True
    return True


def _get_parser_and_language(language: str) -> tuple[Any, Any] | None:
    if not _ensure_deps():
        return None
    try:
        from tree_sitter_language_pack import get_language, get_parser
    except Exception:
        return None
    try:
        # tree-sitter-language-pack types the language argument as a
        # ``Literal[...]`` of all 300+ supported languages. We accept only
        # the languages we register in our packs (``go``, ``rust``,
        # ``typescript``, ``tsx``, ``javascript``, ``python``), so the
        # str→Literal narrowing is safe at this call site.
        return get_parser(language), get_language(language)  # type: ignore[arg-type]
    except Exception:
        return None


def _compile_queries(language_obj: Any, rules: list[TreeSitterRule]) -> dict[str, Any]:
    """Compile each rule's query against the language. Skips invalid rules with a warning."""
    from tree_sitter import Query

    compiled: dict[str, Any] = {}
    for rule in rules:
        try:
            compiled[rule.subcategory] = Query(language_obj, rule.query)
        except Exception as exc:  # tree_sitter raises a generic error subtype
            warnings.warn(
                f"tree-sitter: query for rule {rule.subcategory!r} failed to compile: {exc}",
                stacklevel=2,
            )
    return compiled


def _node_snippet(source: bytes, source_lines: list[str], node: Any) -> str:
    line = node.start_point.row
    if 0 <= line < len(source_lines):
        return source_lines[line].rstrip()
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace").splitlines()[0] if node.start_byte < len(source) else ""


def run_treesitter_pack(
    repo_path: Path | str,
    *,
    language: str,
    suffixes: tuple[str, ...],
    rules: list[TreeSitterRule],
    detector_source: str,
) -> list[dict]:
    """Execute every rule against every matching file in ``repo_path``.

    One finding emitted per rule per file when the rule's primary capture
    matches at least once. Each finding includes the line number, snippet,
    and total occurrence count.
    """
    repo_path = Path(repo_path)
    bundle = _get_parser_and_language(language)
    if bundle is None:
        return []
    parser, language_obj = bundle
    if not rules:
        return []

    from tree_sitter import QueryCursor

    queries = _compile_queries(language_obj, rules)
    if not queries:
        return []

    findings: list[dict] = []

    for path in iter_repo_files(repo_path):
        if path.suffix.lower() not in suffixes:
            continue
        try:
            source_bytes = path.read_bytes()
        except OSError:
            continue
        # Decode once for snippet extraction; the parser eats bytes.
        try:
            source_lines = source_bytes.decode("utf-8", errors="replace").splitlines()
        except UnicodeError:
            source_lines = []
        try:
            tree = parser.parse(source_bytes)
        except Exception:
            continue
        try:
            rel = path.relative_to(repo_path).as_posix()
        except ValueError:
            rel = str(path)

        for rule in rules:
            query = queries.get(rule.subcategory)
            if query is None:
                continue
            cursor = QueryCursor(query)
            captures = cursor.captures(tree.root_node)
            if not isinstance(captures, dict):
                continue
            primary_nodes = captures.get(rule.primary_capture)
            if not primary_nodes:
                continue
            if rule.post_filter is not None:
                primary_nodes = [n for n in primary_nodes if rule.post_filter(n)]
                if not primary_nodes:
                    continue
            first = primary_nodes[0]
            line = first.start_point.row + 1
            snippet = _node_snippet(source_bytes, source_lines, first)
            findings.append(
                {
                    "category": rule.category,
                    "subcategory": rule.subcategory,
                    "severity": rule.severity,
                    "statement": rule.statement,
                    "evidence": [
                        {
                            "path": rel,
                            "line_start": line,
                            "line_end": first.end_point.row + 1,
                            "snippet": snippet,
                            "match_type": "exact",
                            "count": len(primary_nodes),
                        }
                    ],
                    "confidence": rule.confidence,
                    "applicability": "applicable",
                    "score_impact": build_score_impact(
                        rule.severity,
                        rationale=rule.rationale or rule.statement,
                    ),
                    "detector_source": f"{detector_source}.{rule.subcategory}",
                    "tags": list(rule.tags),
                }
            )

    return findings


__all__ = ["TreeSitterRule", "run_treesitter_pack"]
