"""CLI entrypoint for sdlc assessor."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sdlc_assessor.classifier.engine import classify_repo
from sdlc_assessor.collector.engine import collect_evidence
from sdlc_assessor.core.io import read_json, write_json
from sdlc_assessor.remediation.markdown import render_remediation_markdown
from sdlc_assessor.remediation.planner import build_remediation_plan
from sdlc_assessor.renderer.markdown import render_markdown_report
from sdlc_assessor.scorer.engine import score_evidence

# Fallbacks when the classifier cannot infer a maturity or archetype but the
# user has also not supplied one explicitly. These are deliberately permissive
# — the user is expected to confirm via --maturity / --repo-type when accuracy
# matters.
DEFAULT_MATURITY_FALLBACK = "prototype"
DEFAULT_REPO_TYPE_FALLBACK = "internal_tool"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sdlc", description="SDLC assessor CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    classify = sub.add_parser("classify", help="Classify repository")
    classify.add_argument("repo_target", help="Path to repository")
    classify.add_argument("--out", default="./.sdlc/classification.json", help="Output JSON path")
    classify.add_argument("--json", action="store_true", help="Emit JSON artifact")

    collect = sub.add_parser("collect", help="Collect evidence")
    collect.add_argument("repo_target", help="Path to repository")
    collect.add_argument("--classification", required=True, help="Path to classification.json")
    collect.add_argument("--out", default="./.sdlc/evidence.json", help="Output JSON path")
    collect.add_argument("--json", action="store_true", help="Emit JSON artifact")

    score = sub.add_parser("score", help="Score evidence")
    score.add_argument("evidence_path", help="Path to evidence.json")
    score.add_argument("--use-case", required=True, help="Use-case profile")
    score.add_argument("--maturity", default=None, help="Maturity profile (default: classifier-inferred)")
    score.add_argument("--repo-type", default=None, help="Repo type profile (default: classifier-inferred)")
    score.add_argument("--repo-target", default=None, help="Repo path used to infer defaults when omitted")
    score.add_argument("--policy", help="Optional policy override JSON path")
    score.add_argument("--out", default="./.sdlc/scored.json", help="Output JSON path")
    score.add_argument("--json", action="store_true", help="Emit JSON artifact")

    render = sub.add_parser("render", help="Render markdown report")
    render.add_argument("scored_path", help="Path to scored.json")
    render.add_argument("--format", default="markdown", choices=["markdown"], help="Render format")
    render.add_argument("--out", default="./.sdlc/report.md", help="Output report path")

    remediate = sub.add_parser("remediate", help="Generate remediation plan")
    remediate.add_argument("scored_path", help="Path to scored.json")
    remediate.add_argument("--format", default="markdown", choices=["markdown"], help="Render format")
    remediate.add_argument("--out", default="./.sdlc/remediation.md", help="Output remediation path")

    run = sub.add_parser("run", help="Run full pipeline")
    run.add_argument("repo_target", help="Path to repository")
    run.add_argument("--use-case", required=True, help="Use-case profile")
    run.add_argument("--maturity", default=None, help="Maturity profile (default: classifier-inferred)")
    run.add_argument("--repo-type", default=None, help="Repo type profile (default: classifier-inferred)")
    run.add_argument("--policy", help="Optional policy override JSON path")
    run.add_argument("--out-dir", default="./.sdlc", help="Output directory")

    return parser


def _resolve_profile_defaults(
    classification: dict,
    *,
    maturity: str | None,
    repo_type: str | None,
    log: bool = True,
) -> tuple[str, str]:
    """Fill in missing --maturity / --repo-type from classification output.

    Implements SDLC-017. Logs the defaulted choice to stderr so the user can
    spot which decisions came from the classifier vs from the command line.
    """
    inferred_maturity = classification.get("maturity_profile") or DEFAULT_MATURITY_FALLBACK
    inferred_repo_type = classification.get("repo_archetype") or DEFAULT_REPO_TYPE_FALLBACK
    if inferred_maturity == "unknown":
        inferred_maturity = DEFAULT_MATURITY_FALLBACK
    if inferred_repo_type == "unknown":
        inferred_repo_type = DEFAULT_REPO_TYPE_FALLBACK

    chosen_maturity = maturity or inferred_maturity
    chosen_repo_type = repo_type or inferred_repo_type

    if log:
        defaulted = []
        if maturity is None:
            defaulted.append(f"maturity={chosen_maturity} (from classifier)")
        if repo_type is None:
            defaulted.append(f"repo-type={chosen_repo_type} (from classifier)")
        if defaulted:
            print("using " + ", ".join(defaulted), file=sys.stderr)
    return chosen_maturity, chosen_repo_type


def _classification_for_evidence(evidence: dict, repo_target: str | None) -> dict:
    """Get a classification dict either from the evidence payload or by re-running."""
    cls = evidence.get("classification") or {}
    if cls.get("repo_archetype") and cls.get("maturity_profile"):
        return cls
    if repo_target:
        return classify_repo(repo_target).get("classification", {})
    return cls


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "classify":
        payload = classify_repo(args.repo_target)
        if args.json:
            write_json(args.out, payload)
        return 0

    if args.command == "collect":
        payload = collect_evidence(args.repo_target, args.classification)
        if args.json:
            write_json(args.out, payload)
        return 0

    if args.command == "score":
        evidence = read_json(args.evidence_path)
        classification = _classification_for_evidence(evidence, args.repo_target)
        maturity, repo_type = _resolve_profile_defaults(
            classification, maturity=args.maturity, repo_type=args.repo_type
        )
        policy = read_json(args.policy) if args.policy else None
        payload = score_evidence(
            evidence, args.use_case, maturity, repo_type, policy_overrides=policy
        )
        if args.json:
            write_json(args.out, payload)
        return 0

    if args.command == "render":
        scored = read_json(args.scored_path)
        report = render_markdown_report(scored)
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report)
        return 0

    if args.command == "remediate":
        scored = read_json(args.scored_path)
        plan = build_remediation_plan(scored)
        markdown = render_remediation_markdown(plan)
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(markdown)
        return 0

    if args.command == "run":
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        classification = classify_repo(args.repo_target)
        classification_path = out_dir / "classification.json"
        write_json(classification_path, classification)

        maturity, repo_type = _resolve_profile_defaults(
            classification.get("classification", {}),
            maturity=args.maturity,
            repo_type=args.repo_type,
        )

        evidence = collect_evidence(args.repo_target, str(classification_path))
        evidence_path = out_dir / "evidence.json"
        write_json(evidence_path, evidence)

        policy = read_json(args.policy) if args.policy else None
        scored = score_evidence(
            evidence, args.use_case, maturity, repo_type, policy_overrides=policy
        )
        scored_path = out_dir / "scored.json"
        write_json(scored_path, scored)

        report_md = render_markdown_report(scored)
        (out_dir / "report.md").write_text(report_md, encoding="utf-8")

        remediation = build_remediation_plan(scored)
        remediation_md = render_remediation_markdown(remediation)
        (out_dir / "remediation.md").write_text(remediation_md, encoding="utf-8")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
