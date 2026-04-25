"""TypeScript / JavaScript detectors with regex boundaries (SDLC-020).

Includes a comment-and-string stripper that preserves line numbers, regex
patterns with word boundaries to avoid the ``execa(`` / ``pprint(`` style
false positives documented in ANALYSIS.md §5.3, an ``extends`` chain
resolution for tsconfig (up to 3 levels via ``json5`` if available), and a
``json_parse`` severity demotion to ``info``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from sdlc_assessor.detectors.common import iter_repo_files
from sdlc_assessor.normalizer.findings import build_score_impact

TSJS_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}

PATTERNS: list[tuple[str, str, str, str, re.Pattern]] = [
    (
        "as_any",
        "medium",
        "code_quality_contracts",
        "`as any` type cast detected.",
        re.compile(r"\bas\s+any\b"),
    ),
    (
        "console_usage",
        "low",
        "code_quality_contracts",
        "`console.*` usage detected.",
        re.compile(r"\bconsole\.(log|warn|error|info|debug)\s*\("),
    ),
    (
        "empty_catch",
        "medium",
        "code_quality_contracts",
        "Empty `catch` block detected.",
        re.compile(r"catch\s*(?:\(\s*(?:\w+|_)\s*\))?\s*\{\s*\}"),
    ),
    (
        "json_parse",
        "info",
        "code_quality_contracts",
        "`JSON.parse` call (informational; check for missing try/catch).",
        re.compile(r"\bJSON\.parse\s*\("),
    ),
    (
        "exec_usage",
        "high",
        "security_posture",
        "`exec(` call detected (command-injection risk).",
        re.compile(r"(?<!\w)exec\s*\("),
    ),
    (
        "exec_sync_usage",
        "high",
        "security_posture",
        "`execSync(` call detected (command-injection risk).",
        re.compile(r"(?<!\w)execSync\s*\("),
    ),
]


def _strip_comments_and_strings(source: str) -> str:
    """Replace comment / string-literal contents with spaces, preserving line numbers."""
    out = []
    i = 0
    n = len(source)
    while i < n:
        ch = source[i]
        nxt = source[i + 1] if i + 1 < n else ""
        # Block comment.
        if ch == "/" and nxt == "*":
            end = source.find("*/", i + 2)
            if end == -1:
                out.append(" " * (n - i))
                break
            replacement = source[i: end + 2]
            out.append(re.sub(r"[^\n]", " ", replacement))
            i = end + 2
            continue
        # Line comment.
        if ch == "/" and nxt == "/":
            end = source.find("\n", i)
            if end == -1:
                end = n
            out.append(" " * (end - i))
            i = end
            continue
        # String literal (single, double, backtick).
        if ch in {"'", '"', "`"}:
            quote = ch
            j = i + 1
            while j < n:
                if source[j] == "\\":
                    j += 2
                    continue
                if source[j] == quote:
                    j += 1
                    break
                j += 1
            replacement = source[i:j]
            # Preserve newlines (template literals can span lines), blank everything else.
            out.append("".join(c if c == "\n" else " " for c in replacement))
            i = j
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _line_for_offset(source: str, offset: int) -> int:
    return source.count("\n", 0, offset) + 1


def _detect_in_file(path: Path, repo_path: Path) -> list[dict]:
    rel = path.relative_to(repo_path).as_posix()
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    stripped = _strip_comments_and_strings(source)
    source_lines = source.splitlines()
    findings: list[dict] = []
    for subcat, severity, category, statement, pattern in PATTERNS:
        matches = list(pattern.finditer(stripped))
        if not matches:
            continue
        primary = _line_for_offset(source, matches[0].start())
        snippet = source_lines[primary - 1].rstrip() if 1 <= primary <= len(source_lines) else ""
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
                        "snippet": snippet,
                        "match_type": "pattern",
                        "count": len(matches),
                    }
                ],
                "confidence": "high",
                "applicability": "applicable",
                "score_impact": build_score_impact(severity, rationale=statement),
                "detector_source": f"tsjs_pack.{subcat}",
            }
        )
    return findings


def _load_tsconfig_text(path: Path) -> dict | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    try:
        import json5
        return json5.loads(text)
    except ImportError:
        # Fallback: strip simple JSONC comments.
        stripped = re.sub(r"//[^\n]*", "", text)
        stripped = re.sub(r"/\*.*?\*/", "", stripped, flags=re.DOTALL)
        # Drop trailing commas (jsonc).
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


def run_tsjs_detectors(repo_path: Path) -> list[dict]:
    findings: list[dict] = []
    has_any = False
    for path in iter_repo_files(repo_path):
        if path.suffix.lower() not in TSJS_SUFFIXES:
            continue
        has_any = True
        findings.extend(_detect_in_file(path, repo_path))
    if not has_any:
        return findings

    tsconfig = repo_path / "tsconfig.json"
    if tsconfig.exists():
        strict_enabled = _resolve_strict(tsconfig)
        if not strict_enabled:
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
                        "medium", rationale="TypeScript strict mode disabled or absent in tsconfig."
                    ),
                    "detector_source": "tsjs_pack.missing_strict_mode",
                }
            )

    return findings


__all__ = ["run_tsjs_detectors", "TSJS_SUFFIXES"]
