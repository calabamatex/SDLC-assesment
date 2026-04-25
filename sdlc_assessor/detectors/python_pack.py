"""Python detectors using stdlib ``ast`` (SDLC-019, expanded SDLC-048).

v0.2.0 introduced AST-driven detection covering 6 patterns. v0.4.0 adds 6
more, all caught with simple ``ast.walk`` filters; the additions explicitly
target dangerous-by-default APIs that bandit / semgrep would otherwise own.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from sdlc_assessor.detectors.common import iter_repo_files
from sdlc_assessor.normalizer.findings import build_score_impact

TYPE_IGNORE_RE = re.compile(r"#\s*type\s*:\s*ignore\b")

# Common SQL-method names whose first argument we'll inspect for unsafe
# string concatenation / f-strings / .format usage.
SQL_EXEC_METHODS = {"execute", "executemany", "executescript"}

# Top-level dotted names that map to dangerous APIs.
PICKLE_LOAD_NAMES = {"pickle.load", "pickle.loads", "cPickle.load", "cPickle.loads"}


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


def _dotted_name(func: ast.expr) -> str | None:
    """Best-effort attribute-chain reduction to a dotted string."""
    parts: list[str] = []
    cur: ast.expr | None = func
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return ".".join(reversed(parts))
    return None


def _is_unsafe_sql_arg(arg: ast.expr) -> bool:
    """True when the SQL string is built via concatenation, f-string, or .format()."""
    if isinstance(arg, ast.JoinedStr):
        # f-strings — anything with substitutions is suspect
        return any(isinstance(v, ast.FormattedValue) for v in arg.values)
    if isinstance(arg, ast.BinOp) and isinstance(arg.op, (ast.Add, ast.Mod)):
        return True
    if isinstance(arg, ast.Call):
        method = arg.func
        if isinstance(method, ast.Attribute) and method.attr == "format":
            return True
    return False


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

    # v0.2.0 buckets
    bare_except_lines: list[int] = []
    broad_except_lines: list[int] = []
    shell_true_lines: list[int] = []
    print_lines: list[int] = []
    any_lines: list[int] = []

    # v0.4.0 expansions
    eval_exec_lines: list[int] = []
    pickle_load_lines: list[int] = []
    os_system_lines: list[int] = []
    requests_no_verify_lines: list[int] = []
    mutable_default_lines: list[int] = []
    unsafe_sql_lines: list[int] = []
    assert_in_module_lines: list[int] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                bare_except_lines.append(node.lineno)
            elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
                broad_except_lines.append(node.lineno)

        elif isinstance(node, ast.Call):
            # shell=True (v0.2.0)
            if any(
                isinstance(kw, ast.keyword)
                and kw.arg == "shell"
                and isinstance(kw.value, ast.Constant)
                and kw.value.value is True
                for kw in node.keywords
            ):
                shell_true_lines.append(node.lineno)

            # print() and bare-name calls
            func = node.func
            func_name_attr = (
                func.id if isinstance(func, ast.Name)
                else func.attr if isinstance(func, ast.Attribute)
                else None
            )
            if func_name_attr == "print" and isinstance(func, ast.Name):
                print_lines.append(node.lineno)

            # eval() / exec() — name-resolved, not string-matched
            if isinstance(func, ast.Name) and func.id in {"eval", "exec"}:
                eval_exec_lines.append(node.lineno)

            # pickle.load / pickle.loads / cPickle.*
            dotted = _dotted_name(func)
            if dotted in PICKLE_LOAD_NAMES:
                pickle_load_lines.append(node.lineno)

            # os.system / subprocess.getoutput / subprocess.getstatusoutput
            if dotted in {"os.system", "subprocess.getoutput", "subprocess.getstatusoutput"}:
                os_system_lines.append(node.lineno)

            # requests.* with verify=False
            if dotted and dotted.startswith("requests."):
                for kw in node.keywords:
                    if kw.arg == "verify" and isinstance(kw.value, ast.Constant) and kw.value.value is False:
                        requests_no_verify_lines.append(node.lineno)
                        break

            # SQL injection: cursor.execute(string-concat)
            if (
                isinstance(func, ast.Attribute)
                and func.attr in SQL_EXEC_METHODS
                and node.args
                and _is_unsafe_sql_arg(node.args[0])
            ):
                unsafe_sql_lines.append(node.lineno)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for default in node.args.defaults + node.args.kw_defaults:
                if default is None:
                    continue
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    mutable_default_lines.append(default.lineno)
                elif isinstance(default, ast.Call):
                    func = default.func
                    if isinstance(func, ast.Name) and func.id in {"list", "dict", "set"}:
                        mutable_default_lines.append(default.lineno)

        # Module-level asserts are precisely captured below by walking ``tree.body``;
        # the ast.walk loop handles only nested-context concerns.

    any_lines.extend(_annotation_visitor(tree))

    # Module-top-level asserts (precise via direct iteration of body).
    if "test" not in rel.lower():
        for stmt in tree.body:
            if isinstance(stmt, ast.Assert):
                assert_in_module_lines.append(stmt.lineno)

    type_ignore_lines = [
        i + 1 for i, line in enumerate(source_lines) if TYPE_IGNORE_RE.search(line)
    ]

    def emit(
        subcat: str,
        severity: str,
        category: str,
        lines: list[int],
        statement: str,
        confidence: str = "high",
    ) -> None:
        if not lines:
            return
        primary = lines[0]
        findings.append(
            {
                "category": category,
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
                "confidence": confidence,
                "applicability": "applicable",
                "score_impact": build_score_impact(severity, rationale=statement),
                "detector_source": f"python_pack.{subcat}",
            }
        )

    # v0.2.0 emissions
    emit("bare_except", "high", "code_quality_contracts", bare_except_lines, "Bare `except:` handler detected.")
    emit("broad_except_exception", "medium", "code_quality_contracts", broad_except_lines, "`except Exception` handler detected.")
    emit(
        "subprocess_shell_true",
        "high",
        "security_posture",
        shell_true_lines,
        "subprocess invoked with `shell=True` (command-injection risk).",
    )
    emit("print_usage", "low", "code_quality_contracts", print_lines, "`print` call in module-level code.")
    emit("any_usage", "low", "code_quality_contracts", any_lines, "`typing.Any` used in annotations.")
    emit("type_ignore", "medium", "code_quality_contracts", type_ignore_lines, "`# type: ignore` comment present.")

    # v0.4.0 expansions
    emit(
        "eval_or_exec",
        "critical",
        "security_posture",
        eval_exec_lines,
        "`eval()` or `exec()` call detected — arbitrary code execution.",
    )
    emit(
        "pickle_load_untrusted",
        "high",
        "security_posture",
        pickle_load_lines,
        "`pickle.load(s)` call — pickle is unsafe on untrusted input (RCE).",
    )
    emit(
        "os_system_call",
        "high",
        "security_posture",
        os_system_lines,
        "`os.system` / subprocess shell helper — command-injection risk.",
    )
    emit(
        "requests_verify_false",
        "high",
        "security_posture",
        requests_no_verify_lines,
        "`requests.*(verify=False)` — TLS validation disabled.",
    )
    emit(
        "mutable_default_argument",
        "medium",
        "code_quality_contracts",
        mutable_default_lines,
        "Mutable default argument — shared across calls, classic gotcha.",
    )
    emit(
        "unsafe_sql_string",
        "high",
        "security_posture",
        unsafe_sql_lines,
        "SQL `execute()` with string-concatenated/f-string/.format query — SQL-injection risk.",
    )
    emit(
        "module_level_assert",
        "medium",
        "code_quality_contracts",
        assert_in_module_lines,
        "Module-level `assert` — stripped under `python -O`; use explicit raise.",
    )

    return findings


def run_python_detectors(repo_path: Path) -> list[dict]:
    findings: list[dict] = []
    for path in iter_repo_files(repo_path):
        if path.suffix != ".py":
            continue
        findings.extend(_detect_in_file(path, repo_path))
    return findings


__all__ = ["run_python_detectors"]
