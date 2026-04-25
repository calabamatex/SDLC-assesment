"""Python-specific detectors using ``ast`` (SDLC-019).

Replaces the v0.1 substring-based heuristics with AST-driven detection that
captures line numbers, occurrence counts, and avoids the systematic false
positives documented in ANALYSIS.md §5.2 (e.g. ``pprint(`` matching ``print(``,
``Many`` matching ``Any``).
"""

from __future__ import annotations

import ast
import re
from collections import Counter
from pathlib import Path

from sdlc_assessor.detectors.common import iter_repo_files
from sdlc_assessor.normalizer.findings import build_score_impact

TYPE_IGNORE_RE = re.compile(r"#\s*type\s*:\s*ignore\b")


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _snippet(source_lines: list[str], lineno: int) -> str:
    if 1 <= lineno <= len(source_lines):
        return source_lines[lineno - 1].rstrip()
    return ""


def _is_typing_any(node: ast.AST) -> bool:
    if isinstance(node, ast.Name):
        return node.id == "Any"
    if isinstance(node, ast.Attribute):
        return (
            node.attr == "Any"
            and isinstance(node.value, ast.Name)
            and node.value.id in {"typing", "t", "T"}
        )
    return False


def _annotation_visitor(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, (ast.AnnAssign, ast.arg)):
            ann = node.annotation
            if ann is None:
                continue
            for sub in ast.walk(ann):
                if _is_typing_any(sub):
                    yield getattr(sub, "lineno", 1)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.returns is not None:
                for sub in ast.walk(node.returns):
                    if _is_typing_any(sub):
                        yield getattr(sub, "lineno", 1)


def _detect_in_file(path: Path, repo_path: Path) -> list[dict]:
    rel = path.relative_to(repo_path).as_posix()
    source = _read(path)
    if source is None:
        return []
    source_lines = source.splitlines()
    findings: list[dict] = []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return findings

    bare_except_lines: list[int] = []
    broad_except_lines: list[int] = []
    shell_true_lines: list[int] = []
    print_lines: list[int] = []
    any_lines: list[int] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                bare_except_lines.append(node.lineno)
            elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
                broad_except_lines.append(node.lineno)
        elif isinstance(node, ast.Call):
            if any(
                isinstance(kw, ast.keyword)
                and kw.arg == "shell"
                and isinstance(kw.value, ast.Constant)
                and kw.value.value is True
                for kw in node.keywords
            ):
                shell_true_lines.append(node.lineno)
            func = node.func
            func_name = (
                func.id if isinstance(func, ast.Name)
                else func.attr if isinstance(func, ast.Attribute)
                else None
            )
            if func_name == "print" and isinstance(func, ast.Name):
                print_lines.append(node.lineno)

    any_lines.extend(_annotation_visitor(tree))

    type_ignore_lines = [
        i + 1 for i, line in enumerate(source_lines) if TYPE_IGNORE_RE.search(line)
    ]

    def emit(subcat: str, severity: str, lines: list[int], statement: str) -> None:
        if not lines:
            return
        primary = lines[0]
        findings.append(
            {
                "category": "code_quality_contracts",
                "subcategory": subcat,
                "severity": severity,
                "statement": statement,
                "evidence": [
                    {
                        "path": rel,
                        "line_start": primary,
                        "line_end": primary,
                        "snippet": _snippet(source_lines, primary),
                        "match_type": "exact",
                        "count": len(lines),
                    }
                ],
                "confidence": "high",
                "applicability": "applicable",
                "score_impact": build_score_impact(severity, rationale=statement),
                "detector_source": f"python_pack.{subcat}",
            }
        )

    emit("bare_except", "high", bare_except_lines, "Bare `except:` handler detected.")
    emit("broad_except_exception", "medium", broad_except_lines, "`except Exception` handler detected.")
    emit(
        "subprocess_shell_true",
        "high",
        shell_true_lines,
        "subprocess invoked with `shell=True` (command-injection risk).",
    )
    emit("print_usage", "low", print_lines, "`print` call in module-level code.")
    emit("any_usage", "low", any_lines, "`typing.Any` used in annotations.")
    emit("type_ignore", "medium", type_ignore_lines, "`# type: ignore` comment present.")

    return findings


def run_python_detectors(repo_path: Path) -> list[dict]:
    findings: list[dict] = []
    for path in iter_repo_files(repo_path):
        if path.suffix != ".py":
            continue
        findings.extend(_detect_in_file(path, repo_path))
    return findings


__all__ = ["run_python_detectors"]
_ = Counter  # keep imports minimal but stable
