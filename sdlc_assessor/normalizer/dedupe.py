"""Cross-detector dedupe (SDLC-062).

Native packs (Python AST, tree-sitter) and SAST adapters (bandit, ruff,
eslint, semgrep, cargo-audit) frequently flag the same issue on the same
line. v0.6.0 emitted both findings — that's signal honesty (each detector
is a witness) but it inflates counts and makes the "top risks" list
chatty.

This module collapses near-duplicates into single merged findings while
preserving every detector's contribution as evidence and tags.

## How dedupe works

1. **Family map.** Each subcategory is mapped to a family key (e.g.
   ``python_pack.eval_or_exec`` and ``bandit_B307`` both map to
   ``"eval_call"``). Subcategories not in the map are never deduped.
2. **Group key.** Findings are grouped by
   ``(path, line_start_or_zero, family_key)``.
3. **Merge.** Within each group, the strongest-severity finding wins as
   the primary; weaker ones contribute their ``evidence``, ``tags``, and
   detector sources to the merged record. The merged finding's
   ``detector_source`` becomes ``"merged:<source_a>+<source_b>+..."``.

Findings without a family-key remain untouched.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

# Family-key map: maps a "detector_source-or-subcategory" handle to a family.
# Keys can be:
#   - exact subcategory string (e.g. "eval_or_exec"), or
#   - ``"<detector_source>:<subcategory>"`` for unambiguous routing.
# We try both forms when classifying a finding.
_FAMILY_MAP = {
    # eval / exec / arbitrary code execution
    "eval_or_exec": "code_eval",
    "bandit_B307": "code_eval",          # bandit blacklist for eval
    "bandit_B102": "code_eval",          # bandit exec_used
    "ruff_S307": "code_eval",            # ruff eval-used
    "ruff_S102": "code_eval",            # ruff exec-builtin
    "eval_usage": "code_eval",           # tsjs_pack
    "function_constructor": "code_eval", # tsjs_pack new Function()

    # Shell exec
    "subprocess_shell_true": "shell_exec",
    "bandit_B602": "shell_exec",         # subprocess_popen_with_shell_equals_true
    "bandit_B605": "shell_exec",         # start_process_with_a_shell
    "ruff_S602": "shell_exec",
    "os_system_call": "shell_exec",
    "exec_usage": "shell_exec",          # tsjs
    "exec_sync_usage": "shell_exec",
    "go_exec_command_shell": "shell_exec",
    "java_runtime_exec": "shell_exec",
    "kotlin_runtime_exec": "shell_exec",
    "csharp_process_start": "shell_exec",

    # Pickle
    "pickle_load_untrusted": "unsafe_deserialize",
    "bandit_B301": "unsafe_deserialize",
    "ruff_S301": "unsafe_deserialize",

    # SQL injection
    "unsafe_sql_string": "sql_injection",
    "bandit_B608": "sql_injection",
    "ruff_S608": "sql_injection",

    # Hardcoded secrets / passwords
    "probable_secrets": "hardcoded_secret",
    "bandit_B105": "hardcoded_secret",   # hardcoded_password_string
    "bandit_B106": "hardcoded_secret",
    "bandit_B107": "hardcoded_secret",
    "ruff_S105": "hardcoded_secret",
    "ruff_S106": "hardcoded_secret",
    "ruff_S107": "hardcoded_secret",

    # TLS validation off
    "requests_verify_false": "tls_validation_off",
    "bandit_B501": "tls_validation_off",
    "ruff_S501": "tls_validation_off",

    # XML / SAX vulnerabilities — bandit only, but place in family for future
    "bandit_B313": "xml_external_entity",
    "ruff_S313": "xml_external_entity",
}

# Severity rank for "strongest wins" tie-breaks.
_SEVERITY_RANK = {
    "info": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def _family_for(finding: dict) -> str | None:
    """Best-effort classification: try direct subcategory then prefixed forms."""
    subcat = finding.get("subcategory") or ""
    detector = finding.get("detector_source") or ""
    candidates = [
        subcat,
        f"{detector}:{subcat}",
        f"{detector.split('.')[-1]}:{subcat}" if "." in detector else None,
    ]
    for key in candidates:
        if key and key in _FAMILY_MAP:
            return _FAMILY_MAP[key]
    return None


def _line_start_of(finding: dict) -> int:
    evidence = finding.get("evidence") or [{}]
    primary = evidence[0]
    line = primary.get("line_start")
    return line if isinstance(line, int) else 0


def _path_of(finding: dict) -> str:
    evidence = finding.get("evidence") or [{}]
    return str(evidence[0].get("path") or "")


def _strongest(findings: list[dict]) -> dict:
    return max(
        findings,
        key=lambda f: (
            _SEVERITY_RANK.get(f.get("severity", "low"), 0),
            f.get("confidence") == "high",
        ),
    )


def _merge_group(group: list[dict]) -> dict:
    """Collapse ``group`` into a single merged finding."""
    primary = _strongest(group)
    merged = dict(primary)

    # Combined evidence: primary's evidence first, then unique extras.
    seen: set[tuple[str, int | None, str | None]] = set()
    combined_evidence: list[dict] = []
    for f in [primary] + [g for g in group if g is not primary]:
        for ev in f.get("evidence", []) or []:
            key = (
                str(ev.get("path") or ""),
                ev.get("line_start"),
                ev.get("snippet"),
            )
            if key in seen:
                continue
            seen.add(key)
            combined_evidence.append(dict(ev))
    merged["evidence"] = combined_evidence

    # detector_source becomes merged:<sorted-sources>
    sources = sorted({f.get("detector_source") or "" for f in group if f.get("detector_source")})
    merged["detector_source"] = "merged:" + "+".join(sources) if len(sources) > 1 else sources[0]

    # Combined tags (deduped, sorted for determinism).
    combined_tags: set[str] = set()
    for f in group:
        for tag in f.get("tags") or []:
            if isinstance(tag, str) and tag.strip():
                combined_tags.add(tag)
    # Source-detector trail tags — explicit so consumers can see what merged in.
    for f in group:
        ds = f.get("detector_source") or ""
        if ds:
            combined_tags.add(f"detector:{ds}")
    if combined_tags:
        merged["tags"] = sorted(combined_tags)

    # Statement: keep primary's, but suffix with the count when multiple
    # detectors agreed.
    if len(group) > 1:
        statement = merged.get("statement") or ""
        merged["statement"] = (
            f"{statement} ({len(group)} detectors agreed: {', '.join(sources)})"
            if sources
            else f"{statement} ({len(group)} detectors agreed)"
        )

    return merged


def deduplicate_findings(findings: list[dict]) -> list[dict]:
    """Return ``findings`` with cross-detector duplicates collapsed.

    Findings without a family-key are passed through unchanged.
    """
    grouped: dict[tuple[str, int, str], list[dict]] = defaultdict(list)
    untouched: list[dict] = []

    for finding in findings:
        family = _family_for(finding)
        if family is None:
            untouched.append(finding)
            continue
        key = (_path_of(finding), _line_start_of(finding), family)
        grouped[key].append(finding)

    out: list[dict] = list(untouched)
    for group in grouped.values():
        if len(group) == 1:
            out.append(group[0])
        else:
            out.append(_merge_group(group))
    return out


def family_for(finding: dict) -> str | None:
    """Public helper: which dedupe family does ``finding`` belong to (or None)."""
    return _family_for(finding)


__all__ = ["deduplicate_findings", "family_for"]


def _ensure_dict(_obj: Any) -> Any:
    return _obj
