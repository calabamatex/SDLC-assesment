"""Markdown renderer matching docs/renderer_template.md.

SDLC-015: consumes ``scoring.category_scores`` as a list-of-dicts (the
schema-required shape) with one-release back-compat for the legacy dict shape.
SDLC-023: the executive summary, top strengths, top risks, and detailed
findings sections are derived from data — no hardcoded prose.
"""

from __future__ import annotations

import warnings
from collections import defaultdict
from datetime import UTC, datetime

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
SEVERITY_RANK = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}
CONFIDENCE_RANK = {"high": 1.0, "medium": 0.9, "low": 0.7}

INVENTORY_FIELDS = [
    ("source_files", "Source files"),
    ("source_loc", "Source LOC"),
    ("test_files", "Test files"),
    ("estimated_test_cases", "Estimated test cases"),
    ("test_to_source_ratio", "Test-to-source ratio"),
    ("workflow_files", "Workflow files"),
    ("workflow_jobs", "Workflow jobs"),
    ("runtime_dependencies", "Runtime dependencies"),
    ("dev_dependencies", "Dev dependencies"),
    ("commit_count", "Commit count"),
    ("tag_count", "Tag count"),
    ("release_count", "Release count"),
]


def _normalize_category_scores(raw):
    """Convert legacy dict-of-cats to list-of-cats (back-compat for SDLC-015)."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        warnings.warn(
            "scoring.category_scores is in the legacy dict shape; "
            "convert to list-of-dicts per docs/evidence_schema.json. "
            "This back-compat branch will be removed in v1.1.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        out = []
        for cat, data in raw.items():
            applicability = data.get("applicability", "applicable")
            out.append(
                {
                    "category": cat,
                    "applicable": applicability != "not_applicable",
                    "score": int(round(data.get("score", 0))),
                    "max_score": int(round(data.get("max", data.get("max_score", 0)))),
                    "summary": data.get("summary", ""),
                    "key_findings": data.get("key_findings", []),
                }
            )
        return out
    return []


def _finding_rank(finding: dict) -> float:
    sev = SEVERITY_RANK.get(finding.get("severity", "low"), 0)
    conf = CONFIDENCE_RANK.get(finding.get("confidence", "medium"), 0.0)
    mag = float(finding.get("score_impact", {}).get("magnitude", 0)) / 10.0
    return sev * conf * mag


def _executive_summary(scored: dict, top_findings: list[dict]) -> list[str]:
    scoring = scored.get("scoring", {})
    classification = scored.get("classification", {})
    archetype = classification.get("repo_archetype", "unknown")
    confidence = classification.get("classification_confidence", 0.0)
    overall = scoring.get("overall_score", "n/a")
    verdict = scoring.get("verdict", "n/a")

    paragraphs: list[str] = []
    paragraphs.append(
        f"Overall the repository scored **{overall}/100** with a verdict of **`{verdict}`**, "
        f"on a classification of **{archetype}** "
        f"(classification confidence {confidence:.2f})."
    )

    if top_findings:
        bullets = "; ".join(
            f"`{f.get('subcategory', '?')}` ({f.get('severity', '?')})"
            for f in top_findings[:3]
        )
        paragraphs.append(
            f"Top issues by severity × confidence × magnitude: {bullets}."
        )
    else:
        paragraphs.append(
            "No findings were emitted by the detector packs for this repository."
        )

    blockers = scored.get("hard_blockers", [])
    if blockers:
        critical = sum(1 for b in blockers if b.get("severity") == "critical")
        high = sum(1 for b in blockers if b.get("severity") == "high")
        paragraphs.append(
            f"Hard blockers active: {critical} critical, {high} high. See §8 below."
        )
    else:
        paragraphs.append("No hard blockers were triggered for this profile.")

    return paragraphs


def _top_strengths(category_scores: list[dict]) -> list[str]:
    strong = [
        c for c in category_scores
        if c.get("applicable") and c.get("max_score", 0) > 0
        and c.get("score", 0) >= c.get("max_score", 0)
    ]
    if not strong:
        return [
            "- No category earned full points; see §7 Top Risks and "
            "§10 Detailed Findings for the gaps."
        ]
    bullets: list[str] = []
    for cat in strong[:5]:
        bullets.append(
            f"- **{cat['category']}** retained full points "
            f"({cat['score']}/{cat['max_score']})."
        )
    return bullets


def _top_risks(findings: list[dict]) -> list[str]:
    if not findings:
        return ["- No explicit risks detected."]
    ranked = sorted(findings, key=lambda f: -_finding_rank(f))
    bullets: list[str] = []
    for f in ranked[:5]:
        sev = (f.get("severity") or "unknown").upper()
        stmt = f.get("statement") or "(no statement)"
        ev = f.get("evidence", []) or [{}]
        path = ev[0].get("path", "n/a")
        line_start = ev[0].get("line_start")
        path_ref = f"{path}:{line_start}" if line_start else path
        conf = f.get("confidence", "?")
        bullets.append(f"- **{sev}** {stmt} — `{path_ref}` (confidence {conf}).")
    return bullets


def _findings_by_category(findings: list[dict]) -> list[str]:
    if not findings:
        return ["- No findings to display."]
    bucket: dict[str, list[dict]] = defaultdict(list)
    for f in findings:
        bucket[f.get("category", "unknown")].append(f)
    out: list[str] = []
    for cat in sorted(bucket.keys()):
        out.append(f"### {cat}")
        sorted_findings = sorted(
            bucket[cat],
            key=lambda f: SEVERITY_ORDER.get(f.get("severity", "low"), 5),
        )
        for f in sorted_findings:
            sev = (f.get("severity") or "unknown").upper()
            stmt = f.get("statement") or "(no statement)"
            ev = f.get("evidence", []) or []
            paths = []
            for e in ev[:3]:
                path = e.get("path", "")
                line = e.get("line_start")
                paths.append(f"{path}:{line}" if line else path)
            paths_str = ", ".join(paths) if paths else "n/a"
            out.append(f"- **{sev}** {stmt} — `{paths_str}`")
        out.append("")
    return out


def _evidence_appendix(findings: list[dict]) -> list[str]:
    if not findings:
        return ["- (no findings)"]
    out: list[str] = []
    for f in findings:
        ev = f.get("evidence", []) or []
        first = ev[0] if ev else {}
        out.append(
            f"- `{f.get('id', '?')}` {f.get('subcategory', '?')} — "
            f"`{first.get('path', 'n/a')}`"
            + (f":{first['line_start']}" if first.get("line_start") else "")
        )
    return out


def render_markdown_report(scored: dict) -> str:
    repo_meta = scored.get("repo_meta", {})
    classification = scored.get("classification", {})
    scoring = scored.get("scoring", {})
    blockers = scored.get("hard_blockers", [])
    inventory = scored.get("inventory", {})
    findings = scored.get("findings", [])
    category_scores = _normalize_category_scores(scoring.get("category_scores", []))
    ranked_findings = sorted(findings, key=lambda f: -_finding_rank(f))

    lines: list[str] = []

    # §1 Header
    lines.append("# SDLC Assessment Report")
    lines.append("")
    lines.append("## 1. Header")
    lines.append(f"- Project name: {repo_meta.get('name', 'unknown')}")
    lines.append(f"- Repository URL: {repo_meta.get('url', 'n/a')}")
    lines.append(f"- Default branch: {repo_meta.get('default_branch', 'unknown')}")
    lines.append(f"- Head commit: {repo_meta.get('head_commit', 'n/a')}")
    lines.append(f"- Analysis timestamp: {repo_meta.get('analysis_timestamp', datetime.now(UTC).isoformat())}")
    eff = scoring.get("effective_profile", {})
    lines.append(f"- Use-case profile: {eff.get('use_case', 'n/a')}")
    lines.append(f"- Maturity profile: {eff.get('maturity', 'n/a')}")
    lines.append(f"- Repo type: {eff.get('repo_type', 'n/a')}")
    lines.append("")

    # §2 Executive Summary
    lines.append("## 2. Executive Summary")
    for paragraph in _executive_summary(scored, ranked_findings):
        lines.append(paragraph)
        lines.append("")

    # §3 Overall Score and Verdict
    lines.append("## 3. Overall Score and Verdict")
    lines.append(f"- Overall score: {scoring.get('overall_score', 'n/a')}/100")
    lines.append(f"- Verdict: `{scoring.get('verdict', 'n/a')}`")
    lines.append(f"- Score confidence: {scoring.get('score_confidence', 'n/a')}")
    flat = scoring.get("flat_penalty_applied", 0)
    if flat:
        lines.append(f"- Flat penalty applied (production-essentials): {flat}")
    lines.append("")

    # §4 Repo Classification Box
    lines.append("## 4. Repo Classification Box")
    lines.append(f"- Repository archetype: {classification.get('repo_archetype', 'unknown')}")
    lines.append(f"- Maturity profile: {classification.get('maturity_profile', 'unknown')}")
    lines.append(f"- Deployment surface: {classification.get('deployment_surface', 'unknown')}")
    lines.append(f"- Network exposure: {classification.get('network_exposure', False)}")
    lines.append(f"- Release surface: {classification.get('release_surface', 'unknown')}")
    lines.append(f"- Classification confidence: {classification.get('classification_confidence', 0.0):.2f}")
    rationale = classification.get("rationale") or classification.get("classification_rationale") or []
    if rationale:
        lines.append("- Rationale:")
        for r in rationale:
            lines.append(f"  - {r}")
    lines.append("")

    # §5 Quantitative Inventory
    lines.append("## 5. Quantitative Inventory")
    for key, label in INVENTORY_FIELDS:
        value = inventory.get(key)
        lines.append(f"- {label}: {value if value is not None else 'n/a'}")
    lines.append("")

    # §6 Top Strengths
    lines.append("## 6. Top Strengths")
    for line in _top_strengths(category_scores):
        lines.append(line)
    lines.append("")

    # §7 Top Risks
    lines.append("## 7. Top Risks")
    for line in _top_risks(findings):
        lines.append(line)
    lines.append("")

    # §8 Hard Blockers
    lines.append("## 8. Hard Blockers")
    if not blockers:
        lines.append("No hard blockers were triggered.")
    else:
        for b in blockers:
            sev = b.get("severity", "?").upper()
            title = b.get("title", "(no title)")
            reason = b.get("reason", "")
            lines.append(f"- **{sev}** {title} — {reason}")
            for cr in b.get("closure_requirements", []) or []:
                lines.append(f"  - {cr}")
    lines.append("")

    # §9 Category Scoring Matrix
    lines.append("## 9. Category Scoring Matrix")
    lines.append("| Category | Applicable | Score | Max | Summary |")
    lines.append("|---|---|---:|---:|---|")
    for cat in category_scores:
        applicable = "yes" if cat.get("applicable") else "no"
        summary = (cat.get("summary") or "").replace("|", "\\|")
        if not cat.get("applicable"):
            score_str = "—"
            max_str = "—"
        else:
            score_str = str(cat.get("score", 0))
            max_str = str(cat.get("max_score", 0))
        lines.append(
            f"| {cat.get('category', '?')} | {applicable} | "
            f"{score_str} | {max_str} | {summary} |"
        )
    lines.append("")

    # §10 Detailed Findings by Category
    lines.append("## 10. Detailed Findings by Category")
    for line in _findings_by_category(findings):
        lines.append(line)

    # §11 Evidence Appendix
    lines.append("## 11. Evidence Appendix")
    lines.append(f"- Total findings: {len(findings)}")
    lines.append("- Findings index:")
    for line in _evidence_appendix(findings):
        lines.append(f"  {line}")

    return "\n".join(lines) + "\n"
