"""Markdown renderer for Phase 5."""

from __future__ import annotations

from datetime import datetime, timezone


def render_markdown_report(scored: dict) -> str:
    repo_meta = scored.get("repo_meta", {})
    classification = scored.get("classification", {})
    scoring = scored.get("scoring", {})
    blockers = scored.get("hard_blockers", [])
    inventory = scored.get("inventory", {})

    lines: list[str] = []
    lines.append("# SDLC Assessment Report")
    lines.append("")
    lines.append("## 1. Header")
    lines.append(f"- Project name: {repo_meta.get('name', 'unknown')}")
    lines.append(f"- Analysis date: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- Default branch: {repo_meta.get('default_branch', 'unknown')}")
    lines.append("")

    lines.append("## 2. Executive Summary")
    lines.append("This report summarizes repository evidence, scoring, and blocker status.")
    lines.append("")

    lines.append("## 3. Overall Score and Verdict")
    lines.append(f"- Overall score: {scoring.get('overall_score', 'n/a')}")
    lines.append(f"- Verdict: {scoring.get('verdict', 'n/a')}")
    lines.append(f"- Score confidence: {scoring.get('score_confidence', 'n/a')}")
    lines.append("")

    lines.append("## 4. Repo Classification Box")
    lines.append(f"- Repository archetype: {classification.get('repo_archetype', 'unknown')}")
    lines.append(f"- Maturity profile: {classification.get('maturity_profile', 'unknown')}")
    lines.append(f"- Deployment surface: {classification.get('deployment_surface', 'unknown')}")
    lines.append("")

    lines.append("## 5. Quantitative Inventory")
    lines.append(f"- Source files: {inventory.get('source_files', 0)}")
    lines.append(f"- Source LOC: {inventory.get('source_loc', 0)}")
    lines.append(f"- Test files: {inventory.get('test_files', 0)}")
    lines.append(f"- Workflow files: {inventory.get('workflow_files', 0)}")
    lines.append("")

    lines.append("## 6. Top Strengths")
    lines.append("- Evidence collection and scoring pipeline executed.")
    lines.append("")

    lines.append("## 7. Top Risks")
    if scored.get("findings"):
        first = scored["findings"][0]
        lines.append(f"- {first.get('severity', 'unknown').upper()}: {first.get('statement', 'n/a')}")
    else:
        lines.append("- No explicit risks detected.")
    lines.append("")

    lines.append("## 8. Hard Blockers")
    if not blockers:
        lines.append("No hard blockers were triggered.")
    else:
        for b in blockers:
            lines.append(f"- {b.get('severity', 'unknown')}: {b.get('reason', 'n/a')}")
    lines.append("")

    lines.append("## 9. Category Scoring Matrix")
    lines.append("| Category | Applicability | Score | Max |")
    lines.append("|---|---|---:|---:|")
    for cat, data in scoring.get("category_scores", {}).items():
        lines.append(f"| {cat} | {data.get('applicability', 'n/a')} | {data.get('score', 0)} | {data.get('max', 0)} |")
    lines.append("")

    lines.append("## 10. Detailed Findings by Category")
    for finding in scored.get("findings", []):
        lines.append(f"- [{finding.get('category', 'unknown')}] {finding.get('statement', 'n/a')}")
    lines.append("")

    lines.append("## 11. Evidence Appendix")
    lines.append(f"- Total findings: {len(scored.get('findings', []))}")

    return "\n".join(lines) + "\n"
