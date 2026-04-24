"""Markdown report renderer."""

from __future__ import annotations


def render_markdown_report(scored: dict) -> str:
    repo_meta = scored.get("repo_meta", {})
    classification = scored.get("classification", {})
    inventory = scored.get("inventory", {})
    findings = scored.get("findings", [])
    scoring = scored.get("scoring", {})
    blockers = scored.get("hard_blockers", [])

    lines: list[str] = ["# SDLC Assessment Report", ""]

    lines.extend([
        "## 1. Header",
        f"- Project name: {repo_meta.get('name', 'unknown')}",
        f"- Analysis date: {repo_meta.get('analysis_timestamp', 'unknown')}",
        f"- Default branch: {repo_meta.get('default_branch', 'unknown')}",
        f"- Head commit: {repo_meta.get('head_commit', 'unknown')}",
        "",
        "## 2. Executive Summary",
        "This assessment summarizes repository evidence, scoring outputs, risks, and remediation direction.",
        "",
        "## 3. Overall Score and Verdict",
        f"- Overall score: {scoring.get('overall_score', 'n/a')}",
        f"- Verdict: {scoring.get('verdict', 'n/a')}",
        f"- Score confidence: {scoring.get('score_confidence', 'n/a')}",
        "",
        "## 4. Repo Classification Box",
        f"- Repository archetype: {classification.get('repo_archetype', 'unknown')}",
        f"- Maturity profile: {classification.get('maturity_profile', 'unknown')}",
        f"- Deployment surface: {classification.get('deployment_surface', 'unknown')}",
        f"- Release surface: {classification.get('release_surface', 'unknown')}",
        f"- Classification confidence: {classification.get('classification_confidence', 'unknown')}",
        "",
        "## 5. Quantitative Inventory",
        f"- Source files: {inventory.get('source_files', 0)}",
        f"- Source LOC: {inventory.get('source_loc', 0)}",
        f"- Test files: {inventory.get('test_files', 0)}",
        f"- Estimated test cases: {inventory.get('estimated_test_cases', 0)}",
        f"- Test-to-source ratio: {inventory.get('test_to_source_ratio', 0)}",
        f"- Workflow files: {inventory.get('workflow_files', 0)}",
        f"- Workflow jobs: {inventory.get('workflow_jobs', 0)}",
        f"- Runtime dependencies: {inventory.get('runtime_dependencies', 0)}",
        f"- Dev dependencies: {inventory.get('dev_dependencies', 0)}",
        f"- Commit count: {repo_meta.get('commit_count', 0)}",
        f"- Tag count: {repo_meta.get('tag_count', 0)}",
        f"- Release count: {repo_meta.get('release_count', 0)}",
        "",
        "## 6. Top Strengths",
    ])

    strengths = []
    if scoring.get("overall_score", 0) >= 70:
        strengths.append("- Overall scoring indicates generally healthy baseline controls.")
    if inventory.get("test_files", 0) > 0:
        strengths.append("- Tests are present in repository.")
    if inventory.get("workflow_files", 0) > 0:
        strengths.append("- CI workflow files are present.")
    lines.extend(strengths or ["- No major strengths were detected with high confidence."])
    lines.append("")

    lines.append("## 7. Top Risks")
    if findings:
        for f in sorted(findings, key=lambda x: {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}.get(x.get("severity", "info"), 0), reverse=True)[:5]:
            lines.append(f"- {f.get('severity', 'unknown').upper()}: {f.get('statement', 'n/a')} ({f.get('subcategory', 'unknown')})")
    else:
        lines.append("- No explicit risks detected.")
    lines.append("")

    lines.append("## 8. Hard Blockers")
    if not blockers:
        lines.append("No hard blockers were triggered.")
    else:
        for b in blockers:
            lines.append(f"- {b.get('severity', 'unknown')}: {b.get('reason', 'n/a')} (finding {b.get('finding_id', 'unknown')})")
    lines.append("")

    lines.extend([
        "## 9. Category Scoring Matrix",
        "| Category | Applicable | Score | Max | Summary |",
        "|---|---|---:|---:|---|",
    ])
    for item in scoring.get("category_scores", []):
        lines.append(
            f"| {item.get('category', 'n/a')} | {item.get('applicable', True)} | {item.get('score', 0)} | {item.get('max_score', 0)} | {item.get('summary', '')} |"
        )
    lines.append("")

    lines.append("## 10. Detailed Findings by Category")
    by_cat: dict[str, list[dict]] = {}
    for f in findings:
        by_cat.setdefault(f.get("category", "unknown"), []).append(f)
    for cat, items in by_cat.items():
        lines.append(f"### {cat}")
        for f in items:
            lines.append(f"- [{f.get('severity', 'unknown')}] {f.get('statement', 'n/a')} | confidence={f.get('confidence', 'n/a')} | source={f.get('detector_source', 'n/a')}")
        lines.append("")

    lines.append("## 11. Evidence Appendix")
    lines.append(f"- Total findings: {len(findings)}")
    lines.append(f"- Detector sources: {sorted({f.get('detector_source', 'unknown') for f in findings})}")

    return "\n".join(lines) + "\n"
