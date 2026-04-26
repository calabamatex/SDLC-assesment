"""Comparison engine for ``sdlc compare`` (SDLC-061).

Given two ``scored.json`` payloads, produce a structured ``Comparison``
object summarising:

- per-category score deltas (with sign)
- overall score and verdict change
- finding-set diffs grouped by ``(category, subcategory)``: only-in-A,
  only-in-B, and the common subset
- blocker count deltas (critical / high)
- classification deltas (archetype, maturity, network exposure)

The output shape is JSON-serialisable; the renderer (``compare/markdown.py``)
walks it to produce a side-by-side report.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass

_SEVERITY_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


@dataclass(slots=True)
class CategoryDelta:
    category: str
    score_a: int
    score_b: int
    max_score_a: int
    max_score_b: int
    delta: int  # b - a
    summary_a: str
    summary_b: str


@dataclass(slots=True)
class FindingFamilyDelta:
    """A single (category, subcategory) row in the finding-set diff."""

    category: str
    subcategory: str
    count_a: int
    count_b: int
    delta: int
    severity: str  # max severity seen across both sides
    sample_statement: str
    only_in: str  # "a" | "b" | "both"


@dataclass(slots=True)
class Comparison:
    repo_a: str
    repo_b: str
    overall_score_a: int
    overall_score_b: int
    overall_score_delta: int
    verdict_a: str
    verdict_b: str
    verdict_change: str  # e.g. "pass → conditional_pass" or "unchanged"
    category_deltas: list[CategoryDelta]
    finding_deltas: list[FindingFamilyDelta]
    blocker_delta_critical: int  # b - a
    blocker_delta_high: int
    classification_a: dict
    classification_b: dict


def _category_index(scored: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for entry in (scored.get("scoring") or {}).get("category_scores", []) or []:
        if isinstance(entry, dict) and entry.get("category"):
            out[str(entry["category"])] = entry
    return out


def _finding_key(finding: dict) -> tuple[str, str]:
    return (
        str(finding.get("category") or ""),
        str(finding.get("subcategory") or ""),
    )


def _index_findings(scored: dict) -> dict[tuple[str, str], list[dict]]:
    out: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for finding in scored.get("findings") or []:
        out[_finding_key(finding)].append(finding)
    return out


def _max_severity(findings: list[dict]) -> str:
    best = "info"
    best_rank = -1
    for f in findings:
        sev = f.get("severity") or "info"
        rank = _SEVERITY_RANK.get(sev, 0)
        if rank > best_rank:
            best = sev
            best_rank = rank
    return best


def _verdict_change(a: str, b: str) -> str:
    if a == b:
        return "unchanged"
    return f"{a} → {b}"


def build_comparison(scored_a: dict, scored_b: dict, *, label_a: str, label_b: str) -> Comparison:
    """Compute every cross-cutting delta between two scored payloads."""
    scoring_a = scored_a.get("scoring") or {}
    scoring_b = scored_b.get("scoring") or {}

    overall_a = int(scoring_a.get("overall_score", 0) or 0)
    overall_b = int(scoring_b.get("overall_score", 0) or 0)
    verdict_a = str(scoring_a.get("verdict", "n/a"))
    verdict_b = str(scoring_b.get("verdict", "n/a"))

    # Category deltas: union of categories appearing in either side.
    cat_a = _category_index(scored_a)
    cat_b = _category_index(scored_b)
    all_categories = sorted(set(cat_a) | set(cat_b))

    category_deltas: list[CategoryDelta] = []
    for cat in all_categories:
        ent_a = cat_a.get(cat) or {}
        ent_b = cat_b.get(cat) or {}
        sa = int(ent_a.get("score", 0) or 0)
        sb = int(ent_b.get("score", 0) or 0)
        ma = int(ent_a.get("max_score", 0) or 0)
        mb = int(ent_b.get("max_score", 0) or 0)
        category_deltas.append(
            CategoryDelta(
                category=cat,
                score_a=sa,
                score_b=sb,
                max_score_a=ma,
                max_score_b=mb,
                delta=sb - sa,
                summary_a=str(ent_a.get("summary", "") or ""),
                summary_b=str(ent_b.get("summary", "") or ""),
            )
        )

    # Finding deltas: by (category, subcategory).
    findings_a = _index_findings(scored_a)
    findings_b = _index_findings(scored_b)
    keys = sorted(set(findings_a) | set(findings_b))

    finding_deltas: list[FindingFamilyDelta] = []
    for key in keys:
        a_list = findings_a.get(key, [])
        b_list = findings_b.get(key, [])
        ca = len(a_list)
        cb = len(b_list)
        only_in: str
        if ca > 0 and cb == 0:
            only_in = "a"
        elif cb > 0 and ca == 0:
            only_in = "b"
        else:
            only_in = "both"
        sample = (a_list or b_list)[0]
        finding_deltas.append(
            FindingFamilyDelta(
                category=key[0],
                subcategory=key[1],
                count_a=ca,
                count_b=cb,
                delta=cb - ca,
                severity=_max_severity(a_list + b_list),
                sample_statement=str(sample.get("statement", "") or ""),
                only_in=only_in,
            )
        )

    # Sort: largest delta-magnitude first, then by severity rank, then by name.
    finding_deltas.sort(
        key=lambda d: (
            -abs(d.delta),
            -_SEVERITY_RANK.get(d.severity, 0),
            d.category,
            d.subcategory,
        )
    )

    # Blocker counts.
    def _count(scored: dict, severity: str) -> int:
        return sum(1 for b in scored.get("hard_blockers") or [] if b.get("severity") == severity)

    return Comparison(
        repo_a=label_a,
        repo_b=label_b,
        overall_score_a=overall_a,
        overall_score_b=overall_b,
        overall_score_delta=overall_b - overall_a,
        verdict_a=verdict_a,
        verdict_b=verdict_b,
        verdict_change=_verdict_change(verdict_a, verdict_b),
        category_deltas=category_deltas,
        finding_deltas=finding_deltas,
        blocker_delta_critical=_count(scored_b, "critical") - _count(scored_a, "critical"),
        blocker_delta_high=_count(scored_b, "high") - _count(scored_a, "high"),
        classification_a=dict(scored_a.get("classification") or {}),
        classification_b=dict(scored_b.get("classification") or {}),
    )


def comparison_to_dict(comparison: Comparison) -> dict:
    """JSON-friendly serialisation."""
    return asdict(comparison)


__all__ = [
    "Comparison",
    "CategoryDelta",
    "FindingFamilyDelta",
    "build_comparison",
    "comparison_to_dict",
]
