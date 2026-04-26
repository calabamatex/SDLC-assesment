"""Top-level RSF entry point: ``assess_repository``.

Drives the per-criterion scorers in :mod:`sdlc_assessor.rsf.scorers`,
aggregates per RSF §4 in :mod:`sdlc_assessor.rsf.aggregate`, and returns a
:class:`RSFAssessment` that the deliverable layer renders.

The call signature is intentionally narrow: ``scored`` (the existing
collector / scorer payload) plus the on-disk ``repo_path`` so the file-
system probes (README presence, workflow YAML, .gitleaks.toml, etc.)
have a place to look. Both inputs are already produced by the existing
pipeline.
"""

from __future__ import annotations

from pathlib import Path

from sdlc_assessor.rsf.aggregate import RSFAssessment, aggregate
from sdlc_assessor.rsf.scorers import score_all


def assess_repository(
    scored: dict,
    *,
    repo_path: str | Path,
    d8_not_applicable: bool = False,
) -> RSFAssessment:
    """Run the RSF v1.0 assessment against a scored payload + repo on disk.

    Parameters
    ----------
    scored:
        The output of ``sdlc_assessor.scorer.engine.score_evidence`` (the
        existing scoring payload). Provides inventory / classification /
        findings / hard_blockers / repo_meta.git_summary.
    repo_path:
        Path to the repository being assessed. The per-criterion scorers
        probe the filesystem here for governance / docs / SBOM /
        signing / dependency-update files and workflow YAML.
    d8_not_applicable:
        When True, every D8.* sub-criterion is recorded as ``N/A``
        rather than ``?``. Pass True for internal / non-customer-facing
        assets that are genuinely out of compliance scope.
    """
    path = Path(repo_path).resolve()
    scores = score_all(scored, path, d8_not_applicable=d8_not_applicable)
    return aggregate(scores)


__all__ = ["assess_repository"]
