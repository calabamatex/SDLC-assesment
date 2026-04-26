"""LLM-backed category narratives (SDLC-066).

Optional Anthropic API integration that replaces the deterministic
:func:`scorer.engine._build_category_summary` output with a richer,
LLM-generated narrative for each category. Disabled by default — the
deterministic narrator stays the canonical path for reproducibility,
auditability, and offline use.

## Activation

Three independent gates, all of which must be open:

1. ``ANTHROPIC_API_KEY`` set in the environment.
2. The ``anthropic`` Python SDK importable (install via the
   ``[llm]`` extra).
3. The caller passes ``use_llm=True`` (the CLI flips this from
   ``--narrate-with-llm``).

If any gate is closed, :func:`narrate_category` returns ``None`` and the
caller falls back to the deterministic summary. The LLM never silently
replaces the deterministic narrative.

## Caching

Per-process LRU cache keyed on ``(category, applicable, score, max_score,
deduction_total, sorted-finding-fingerprint)``. Identical inputs produce
identical prompts and we don't want to pay for the same call twice in a
single ``sdlc run``.

## Prompt discipline

The system prompt explicitly bounds the model: 2–5 sentences, no
exaggeration, cite findings by id, no invented evidence. Prompt-cacheable
where the SDK supports it.
"""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from functools import lru_cache
from typing import Any

# Cap to keep prompt sizes predictable. The deterministic summary
# already prioritises strongest-deduction findings; we ask the model
# only for narrative shaping over the same shortlist.
_MAX_FINDINGS_IN_PROMPT = 8

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
"""Latest Haiku at v0.8.0 cut. CLI / scorer can override.

The system prompt + per-category prompt are short enough that Haiku is
fast and cheap; reviewers asking for richer prose can pass `--llm-model
claude-sonnet-4-6` or `claude-opus-4-7`.
"""

_SYSTEM_PROMPT = (
    "You write 2–5 sentence narrative summaries for a single SDLC-assessment "
    "category. The summary must:\n"
    "- Stay grounded in the supplied findings — never invent evidence.\n"
    "- Reference specific finding IDs in parentheses where helpful.\n"
    "- Avoid exaggeration; if findings are minor, say so.\n"
    "- Avoid hedging boilerplate ('it should be noted', 'arguably', etc.).\n"
    "- Stay between 2 and 5 sentences. Prose, no bullet lists.\n"
    "- If applicable=False, simply state the category is not applicable and "
    "  why in one sentence.\n"
    "Return only the narrative, no preamble."
)


def llm_available() -> bool:
    """Return True when the SDK is importable and an API key is set."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def _finding_fingerprint(findings: Sequence[dict]) -> str:
    """Stable cache key for a finding shortlist."""
    items: list[tuple] = []
    for f in findings[:_MAX_FINDINGS_IN_PROMPT]:
        items.append(
            (
                f.get("id"),
                f.get("subcategory"),
                f.get("severity"),
                f.get("confidence"),
                (f.get("evidence") or [{}])[0].get("path"),
                (f.get("evidence") or [{}])[0].get("line_start"),
            )
        )
    return json.dumps(sorted(items, key=lambda t: tuple("" if x is None else str(x) for x in t)))


def _serialise_findings(findings: Sequence[dict]) -> list[dict]:
    out: list[dict] = []
    for f in findings[:_MAX_FINDINGS_IN_PROMPT]:
        ev = (f.get("evidence") or [{}])[0]
        out.append(
            {
                "id": f.get("id"),
                "subcategory": f.get("subcategory"),
                "severity": f.get("severity"),
                "confidence": f.get("confidence"),
                "statement": f.get("statement"),
                "path": ev.get("path"),
                "line": ev.get("line_start"),
            }
        )
    return out


@lru_cache(maxsize=256)
def _cached_call(
    *,
    category: str,
    applicable: bool,
    score: int,
    max_score: int,
    deduction_total: float,
    findings_fingerprint: str,
    findings_json: str,
    model: str,
) -> str:
    """Single cached entry-point — ``findings_json`` is a JSON string for hashability."""
    import anthropic

    client = anthropic.Anthropic()
    user_prompt = (
        "Write the category narrative.\n\n"
        f"Category: {category}\n"
        f"Applicable: {applicable}\n"
        f"Score: {score}/{max_score}\n"
        f"Deductions total (raw, pre-bound): {deduction_total:.2f}\n"
        f"Findings (JSON, up to {_MAX_FINDINGS_IN_PROMPT}):\n{findings_json}"
    )
    response = client.messages.create(
        model=model,
        max_tokens=400,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    parts: list[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            parts.append(getattr(block, "text", "") or "")
    return ("".join(parts)).strip()


def narrate_category(
    *,
    category: str,
    applicability: str,
    findings_in_cat: Sequence[dict],
    deduction_total: float,
    score: float,
    max_score: float,
    model: str = DEFAULT_MODEL,
    use_llm: bool = False,
) -> str | None:
    """Return an LLM narrative or ``None`` when any activation gate is closed.

    A ``None`` return is the signal for callers to fall back to the
    deterministic ``_build_category_summary``. Errors during the API
    call also degrade to ``None`` rather than raising — narratives are
    never load-bearing for the pipeline.
    """
    if not use_llm:
        return None
    if not llm_available():
        return None

    is_applicable = applicability != "not_applicable"
    findings = _serialise_findings(findings_in_cat)
    fingerprint = _finding_fingerprint(findings_in_cat)
    findings_json = json.dumps(findings, sort_keys=True)

    try:
        return _cached_call(
            category=category,
            applicable=is_applicable,
            score=int(round(score)),
            max_score=int(round(max_score)),
            deduction_total=float(deduction_total),
            findings_fingerprint=fingerprint,
            findings_json=findings_json,
            model=model,
        )
    except Exception:
        # Any API/network/auth failure falls back silently.
        return None


def reset_cache() -> None:
    """Test hook — drop the per-process LRU cache."""
    _cached_call.cache_clear()


def _module_state() -> dict[str, Any]:
    """Test hook — surface internal state for assertions without exposing globals."""
    return {"max_findings_in_prompt": _MAX_FINDINGS_IN_PROMPT}


__all__ = [
    "DEFAULT_MODEL",
    "llm_available",
    "narrate_category",
    "reset_cache",
]
