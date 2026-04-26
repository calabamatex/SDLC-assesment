"""Provenance-header collector (0.11.0 depth pass).

Builds a :class:`ProvenanceHeader` from the assessor's actual run
context: the repo path that was scanned, the git origin URL (if any),
the commit SHA at scan time, the scorer version, and the classifier's
output. Without this, a diligence document is unauditable.

Real-world inputs only — no invented values. If a field can't be
sourced (e.g. local path with no .git dir), the field is set to a
disclosed sentinel like ``"local path: /abs/path"`` with explicit
"no git origin" text.
"""

from __future__ import annotations

import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import sdlc_assessor

from sdlc_assessor.renderer.deliverables.base import ProvenanceHeader


def _run_git(args: list[str], *, cwd: Path) -> str | None:
    """Best-effort git invocation; returns None on any failure."""
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None
    return out.stdout.strip() or None


def _normalize_remote_url(raw: str) -> tuple[str, str]:
    """Convert git-remote URL forms into (https_url, kind)."""
    raw = raw.strip()
    # SSH form: git@github.com:owner/repo.git
    m = re.match(r"git@([^:]+):([^/]+)/(.+?)(\.git)?$", raw)
    if m:
        host, owner, repo, _ = m.groups()
        return f"https://{host}/{owner}/{repo}", "git_remote"
    # HTTPS form: https://github.com/owner/repo(.git)?
    m = re.match(r"(https?://[^/]+/[^/]+/[^/]+?)(\.git)?$", raw)
    if m:
        return m.group(1), "git_remote"
    # Anything else: pass through.
    return raw, "git_remote"


def _project_name_from_url(url: str, *, fallback: str) -> str:
    m = re.search(r"/([^/]+?)(\.git)?$", url)
    if m:
        return m.group(1)
    return fallback


def collect_provenance(
    *,
    repo_path: str | Path,
    scored: dict,
    project_name_override: str | None = None,
    project_url_override: str | None = None,
) -> ProvenanceHeader:
    """Build a :class:`ProvenanceHeader` for ``repo_path``.

    Reads git origin / commit / branch where possible; falls back to
    explicit "no git origin" text when not in a git checkout.
    """
    repo_path = Path(repo_path).resolve()
    name_fallback = repo_path.name or "unknown_project"

    scanned_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    scorer_version = getattr(sdlc_assessor, "__version__", "unknown")

    if project_url_override:
        source_location = project_url_override
        source_kind = "explicit"
    else:
        # `git config remote.origin.url` walks up the directory tree, so a
        # subdir inside a parent git repo will silently inherit the parent's
        # origin (and falsely identify itself as that parent project). Guard
        # against this by checking whether the git toplevel matches the
        # repo_path we were asked about.
        toplevel = _run_git(["rev-parse", "--show-toplevel"], cwd=repo_path)
        is_own_repo = bool(toplevel) and Path(toplevel).resolve() == repo_path
        origin_raw = (
            _run_git(["config", "--get", "remote.origin.url"], cwd=repo_path)
            if is_own_repo
            else None
        )
        if origin_raw:
            source_location, source_kind = _normalize_remote_url(origin_raw)
        else:
            source_location = f"local path: {repo_path} (no git origin)"
            source_kind = "local_path"

    if project_name_override:
        project_name = project_name_override
    elif source_kind == "git_remote":
        project_name = _project_name_from_url(source_location, fallback=name_fallback)
    else:
        project_name = name_fallback

    # Commit + branch are only meaningful when repo_path IS the git repo,
    # not when it's a subdirectory inheriting a parent's git state.
    if source_kind == "git_remote":
        commit_sha = _run_git(["rev-parse", "--short=12", "HEAD"], cwd=repo_path)
        branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
        if branch in {"HEAD", None}:
            branch = None  # detached HEAD
    else:
        commit_sha = None
        branch = None

    classifier = scored.get("classification") or {}
    inventory = scored.get("inventory") or {}

    return ProvenanceHeader(
        project_name=project_name,
        source_location=source_location,
        source_kind=source_kind,
        commit_sha=commit_sha,
        branch=branch,
        scanned_at=scanned_at,
        scorer_version=str(scorer_version),
        classifier={
            "repo_archetype": classifier.get("repo_archetype"),
            "maturity_profile": classifier.get("maturity_profile"),
            "network_exposure": classifier.get("network_exposure"),
            "classification_confidence": classifier.get("classification_confidence"),
            "deployment_surface": classifier.get("deployment_surface"),
            "release_surface": classifier.get("release_surface"),
        },
        inventory_snapshot={
            "source_files": inventory.get("source_files"),
            "source_loc": inventory.get("source_loc"),
            "test_files": inventory.get("test_files"),
            "workflow_files": inventory.get("workflow_files"),
            "workflow_jobs": inventory.get("workflow_jobs"),
            "runtime_dependencies": inventory.get("runtime_dependencies"),
            "dev_dependencies": inventory.get("dev_dependencies"),
        },
    )


__all__ = ["collect_provenance"]
