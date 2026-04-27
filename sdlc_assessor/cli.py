"""CLI entrypoint for sdlc assessor."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sdlc_assessor.classifier.engine import classify_repo
from sdlc_assessor.collector.engine import collect_evidence
from sdlc_assessor.compare.engine import build_comparison, comparison_to_dict
from sdlc_assessor.compare.markdown import render_comparison_markdown
from sdlc_assessor.core.io import read_json, write_json
from sdlc_assessor.remediation.markdown import render_remediation_markdown
from sdlc_assessor.remediation.planner import build_remediation_plan
from sdlc_assessor.renderer.deliverable_html import render_html_report
from sdlc_assessor.renderer.deliverables._provenance import collect_provenance
from sdlc_assessor.renderer.markdown import render_markdown_report
from sdlc_assessor.rsf import assess_repository as rsf_assess
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
    score.add_argument(
        "--narrate-with-llm",
        action="store_true",
        help=(
            "Replace the deterministic per-category summary with an LLM-generated narrative. "
            "Requires ANTHROPIC_API_KEY and the [llm] extra. Falls back silently to the "
            "deterministic summary on any gate failure."
        ),
    )
    score.add_argument(
        "--llm-model",
        default=None,
        help="Anthropic model id (default: claude-haiku-4-5-20251001).",
    )

    render = sub.add_parser("render", help="Render report (markdown or html)")
    render.add_argument("scored_path", help="Path to scored.json")
    render.add_argument(
        "--format",
        default="markdown",
        choices=["markdown", "html", "both"],
        help="Render format. `both` writes report.md AND report.html.",
    )
    render.add_argument("--out", default=None, help="Output path (default: ./.sdlc/report.md or .html)")

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
    run.add_argument(
        "--format",
        default="markdown",
        choices=["markdown", "html", "both"],
        help="Report format produced under <out-dir>/report.{md,html}",
    )
    run.add_argument(
        "--narrate-with-llm",
        action="store_true",
        help=(
            "Replace deterministic per-category summaries with LLM-generated narratives "
            "(requires ANTHROPIC_API_KEY + [llm] extra)."
        ),
    )
    run.add_argument("--llm-model", default=None, help="Anthropic model id")
    run.add_argument(
        "--narrator",
        default="deterministic",
        choices=["deterministic", "llm", "both"],
        help=(
            "Which narrative voice to render in the report body. `deterministic` (default) "
            "uses only the rule-based persona narrative blocks. `llm` replaces them with "
            "Claude-authored prose. `both` renders the two side-by-side. `llm` and `both` "
            "require ANTHROPIC_API_KEY; both gracefully fall back to deterministic when the "
            "key is absent."
        ),
    )
    run.add_argument(
        "--repo-name",
        default=None,
        help=(
            "Project name shown in the report's provenance banner. Defaults to the basename "
            "of <repo_target> or the repo name parsed from the git origin URL."
        ),
    )
    run.add_argument(
        "--repo-url",
        default=None,
        help=(
            "Project source URL shown in the report's provenance banner. Defaults to the git "
            "origin URL when <repo_target> is a git checkout, otherwise 'local path: <abs>' "
            "with explicit 'no git origin' disclosure."
        ),
    )
    run.add_argument(
        "--d8-not-applicable",
        action="store_true",
        help=(
            "Mark all RSF D8 (compliance & governance) sub-criteria as N/A "
            "rather than `?`. Use for internal / non-customer-facing assets "
            "that are genuinely out of compliance scope. Without this flag, "
            "D8 stays unverified — the framework-correct disclosure when "
            "compliance evidence is unavailable."
        ),
    )

    compare = sub.add_parser(
        "compare",
        help="Compare two repos side-by-side and emit a Markdown delta report (SDLC-061).",
    )
    compare.add_argument("repo_a", help="Path to the baseline repository (A)")
    compare.add_argument("repo_b", help="Path to the comparison repository (B)")
    compare.add_argument("--use-case", required=True, help="Use-case profile applied to both repos")
    compare.add_argument(
        "--maturity",
        default=None,
        help="Maturity profile for both repos (default: classifier-inferred from each repo independently)",
    )
    compare.add_argument(
        "--repo-type",
        default=None,
        help="Repo type profile for both repos (default: classifier-inferred from each repo independently)",
    )
    compare.add_argument("--policy", help="Optional policy override JSON path applied to both repos")
    compare.add_argument(
        "--out-dir",
        default="./.sdlc/compare",
        help="Output directory (default: ./.sdlc/compare). Each repo's artifacts go in repo_a/ and repo_b/.",
    )
    compare.add_argument(
        "--out-md",
        default=None,
        help="Output path for the Markdown comparison report (default: <out-dir>/comparison.md).",
    )
    compare.add_argument(
        "--out-json",
        default=None,
        help="Output path for the JSON comparison artifact (default: <out-dir>/comparison.json).",
    )

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
            evidence,
            args.use_case,
            maturity,
            repo_type,
            policy_overrides=policy,
            use_llm_narrator=getattr(args, "narrate_with_llm", False),
            llm_model=getattr(args, "llm_model", None),
        )
        if args.json:
            write_json(args.out, payload)
        return 0

    if args.command == "render":
        scored = read_json(args.scored_path)
        return _render_with_format(
            scored,
            fmt=args.format,
            out=args.out,
            default_dir=Path("./.sdlc"),
        )

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
            evidence,
            args.use_case,
            maturity,
            repo_type,
            policy_overrides=policy,
            use_llm_narrator=getattr(args, "narrate_with_llm", False),
            llm_model=getattr(args, "llm_model", None),
        )
        # Build the remediation plan first so it can be attached to scored
        # before rendering. This lets the deliverable layer's gap analysis
        # and exec summary cite real per-phase projections (0.11.0 depth pass).
        remediation = build_remediation_plan(scored)
        scored["remediation_plan"] = remediation

        # Run the RSF v1.0 assessment and attach to scored. RSF is the
        # canonical scoring framework as of 0.11.0 — every value is
        # anchored to a published reference (NIST SSDF, DORA, CWE, CVSS,
        # SLSA, CycloneDX/SPDX, Sigstore, ISO 27001, AICPA SOC 2,
        # CSA CAIQ). See docs/frameworks/rsf_v1.0.md for the spec.
        from sdlc_assessor.rsf.aggregate import assessment_to_dict
        rsf_result = rsf_assess(
            scored,
            repo_path=args.repo_target,
            d8_not_applicable=getattr(args, "d8_not_applicable", False),
        )
        scored["rsf"] = assessment_to_dict(rsf_result)

        scored_path = out_dir / "scored.json"
        write_json(scored_path, scored)

        narrator = getattr(args, "narrator", "deterministic")
        provenance = collect_provenance(
            repo_path=args.repo_target,
            scored=scored,
            project_name_override=getattr(args, "repo_name", None),
            project_url_override=getattr(args, "repo_url", None),
        )
        if args.format in ("markdown", "both"):
            (out_dir / "report.md").write_text(render_markdown_report(scored), encoding="utf-8")
        if args.format in ("html", "both"):
            (out_dir / "report.html").write_text(
                render_html_report(scored, narrator=narrator, provenance=provenance),
                encoding="utf-8",
            )

        remediation_md = render_remediation_markdown(remediation)
        (out_dir / "remediation.md").write_text(remediation_md, encoding="utf-8")
        return 0

    if args.command == "compare":
        return _run_compare(args)

    return 0


def _render_with_format(scored: dict, *, fmt: str, out: str | None, default_dir: Path) -> int:
    """Write report(s) honouring ``--format`` and an optional ``--out`` override.

    Default output paths are ``./.sdlc/report.md`` and ``./.sdlc/report.html``.
    When ``fmt == "both"``, ``--out`` is treated as a base name and ``.md``/
    ``.html`` are appended.
    """
    base: Path | None = None if out is None else Path(out)

    def _md_path() -> Path:
        if base is None:
            return default_dir / "report.md"
        if fmt == "both":
            return base.with_suffix(".md")
        return base

    def _html_path() -> Path:
        if base is None:
            return default_dir / "report.html"
        if fmt == "both":
            return base.with_suffix(".html")
        return base

    if fmt in ("markdown", "both"):
        path = _md_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_markdown_report(scored), encoding="utf-8")
    if fmt in ("html", "both"):
        path = _html_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_html_report(scored), encoding="utf-8")
    return 0


def _run_pipeline_for_compare(
    repo_target: str,
    *,
    out_dir: Path,
    use_case: str,
    maturity_arg: str | None,
    repo_type_arg: str | None,
    policy: dict | None,
) -> dict:
    """Run classify → collect → score for one repo and write the artifacts.

    Returns the ``scored`` dict in-memory so the caller can build a
    comparison without re-reading from disk.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    classification = classify_repo(repo_target)
    classification_path = out_dir / "classification.json"
    write_json(classification_path, classification)

    maturity, repo_type = _resolve_profile_defaults(
        classification.get("classification", {}),
        maturity=maturity_arg,
        repo_type=repo_type_arg,
    )

    evidence = collect_evidence(repo_target, str(classification_path))
    write_json(out_dir / "evidence.json", evidence)

    scored = score_evidence(
        evidence, use_case, maturity, repo_type, policy_overrides=policy
    )
    write_json(out_dir / "scored.json", scored)
    return scored


def _run_compare(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    policy = read_json(args.policy) if args.policy else None

    print(f"compare: scoring repo A at {args.repo_a}", file=sys.stderr)
    scored_a = _run_pipeline_for_compare(
        args.repo_a,
        out_dir=out_dir / "repo_a",
        use_case=args.use_case,
        maturity_arg=args.maturity,
        repo_type_arg=args.repo_type,
        policy=policy,
    )
    print(f"compare: scoring repo B at {args.repo_b}", file=sys.stderr)
    scored_b = _run_pipeline_for_compare(
        args.repo_b,
        out_dir=out_dir / "repo_b",
        use_case=args.use_case,
        maturity_arg=args.maturity,
        repo_type_arg=args.repo_type,
        policy=policy,
    )

    comparison = build_comparison(scored_a, scored_b, label_a=args.repo_a, label_b=args.repo_b)

    md_path = Path(args.out_md) if args.out_md else (out_dir / "comparison.md")
    json_path = Path(args.out_json) if args.out_json else (out_dir / "comparison.json")

    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_comparison_markdown(comparison), encoding="utf-8")
    write_json(json_path, comparison_to_dict(comparison))

    print(
        f"compare: overall {comparison.overall_score_a} → {comparison.overall_score_b} "
        f"(Δ {comparison.overall_score_delta:+d}); verdict {comparison.verdict_change}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
