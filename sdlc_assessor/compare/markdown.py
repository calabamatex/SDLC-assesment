"""Markdown renderer for ``sdlc compare`` (SDLC-063).

Walks a :class:`Comparison` and produces a side-by-side Markdown report
suitable for diligence reviewers. Sections:

1. Header (repo paths, overall scores, verdicts)
2. Score deltas — overall + per-category
3. Verdict change (or "unchanged")
4. Blocker count delta
5. Finding-set diff: only-in-A, only-in-B, common (with counts)
6. Classification delta (archetype, maturity, network exposure)
"""

from __future__ import annotations

from sdlc_assessor.compare.engine import Comparison


def _delta_marker(delta: int) -> str:
    if delta > 0:
        return f"▲ +{delta}"
    if delta < 0:
        return f"▼ {delta}"
    return "  0"


def _classification_field(payload_a: dict, payload_b: dict, key: str) -> tuple[str, str, str]:
    a = str(payload_a.get(key, "n/a"))
    b = str(payload_b.get(key, "n/a"))
    marker = "" if a == b else " 🔄"
    return a, b, marker


def render_comparison_markdown(c: Comparison) -> str:
    lines: list[str] = []

    lines.append("# SDLC Comparison Report")
    lines.append("")
    lines.append(f"- **Repo A**: `{c.repo_a}`")
    lines.append(f"- **Repo B**: `{c.repo_b}`")
    lines.append("")

    # Section 1 — Overall
    lines.append("## 1. Overall Score and Verdict")
    lines.append("")
    lines.append("| | Repo A | Repo B | Δ |")
    lines.append("|---|---:|---:|---:|")
    lines.append(
        f"| Overall score | {c.overall_score_a} | {c.overall_score_b} | "
        f"{_delta_marker(c.overall_score_delta)} |"
    )
    lines.append(f"| Verdict | `{c.verdict_a}` | `{c.verdict_b}` | {c.verdict_change} |")
    lines.append("")

    # Section 2 — Per-category deltas
    lines.append("## 2. Per-category Score Deltas")
    lines.append("")
    if not c.category_deltas:
        lines.append("_No applicable categories._")
    else:
        lines.append("| Category | Score A / Max | Score B / Max | Δ |")
        lines.append("|---|---:|---:|---:|")
        for cd in c.category_deltas:
            lines.append(
                f"| {cd.category} | "
                f"{cd.score_a} / {cd.max_score_a} | "
                f"{cd.score_b} / {cd.max_score_b} | "
                f"{_delta_marker(cd.delta)} |"
            )
    lines.append("")

    # Section 3 — Blocker delta
    lines.append("## 3. Hard-blocker Delta")
    lines.append("")
    lines.append("| Severity | Δ (B − A) |")
    lines.append("|---|---:|")
    lines.append(f"| critical | {_delta_marker(c.blocker_delta_critical)} |")
    lines.append(f"| high | {_delta_marker(c.blocker_delta_high)} |")
    lines.append("")

    # Section 4 — Finding-set diff
    only_a = [d for d in c.finding_deltas if d.only_in == "a"]
    only_b = [d for d in c.finding_deltas if d.only_in == "b"]
    common = [d for d in c.finding_deltas if d.only_in == "both"]

    lines.append("## 4. Finding-set Diff")
    lines.append("")
    lines.append(
        f"_{len(only_a)} only in A · {len(only_b)} only in B · "
        f"{len(common)} present in both._"
    )
    lines.append("")

    def _render_block(title: str, items: list, count_a_first: bool) -> None:
        lines.append(f"### {title}")
        lines.append("")
        if not items:
            lines.append("_(none)_")
            lines.append("")
            return
        lines.append("| Severity | Category / Subcategory | Count A | Count B | Δ | Sample statement |")
        lines.append("|---|---|---:|---:|---:|---|")
        for d in items[:25]:
            lines.append(
                f"| `{d.severity}` | "
                f"{d.category} / `{d.subcategory}` | "
                f"{d.count_a} | "
                f"{d.count_b} | "
                f"{_delta_marker(d.delta)} | "
                f"{(d.sample_statement or '').replace('|', '\\|')[:90]} |"
            )
        if len(items) > 25:
            lines.append("")
            lines.append(f"_…and {len(items) - 25} more rows omitted._")
        lines.append("")

    _render_block("4.1 Only in Repo A (resolved or absent in B)", only_a, count_a_first=True)
    _render_block("4.2 Only in Repo B (regression or new in B)", only_b, count_a_first=False)
    _render_block("4.3 In both — count delta", common, count_a_first=True)

    # Section 5 — Classification delta
    lines.append("## 5. Classification Delta")
    lines.append("")
    lines.append("| Field | Repo A | Repo B | |")
    lines.append("|---|---|---|---|")
    for key in (
        "repo_archetype",
        "maturity_profile",
        "deployment_surface",
        "release_surface",
        "network_exposure",
        "classification_confidence",
    ):
        a, b, marker = _classification_field(c.classification_a, c.classification_b, key)
        lines.append(f"| {key} | {a} | {b} |{marker} |")
    lines.append("")

    return "\n".join(lines) + "\n"


__all__ = ["render_comparison_markdown"]
