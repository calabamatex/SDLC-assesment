"""Git-history detectors (SDLC-037).

Reads ``git log`` over the last ``GIT_LOG_WINDOW`` commits to surface signals
the static-analysis detectors can't see: commit signing coverage, author
concentration (bus factor), and CODEOWNERS reach.

The implementation shells out to ``git`` rather than using a third-party
library to keep the dependency surface small. All subprocess calls run with
a strict timeout, suppress shell expansion via argument arrays, and tolerate
``git`` not being on PATH or the target not being a git repo.

Findings emitted:

- ``unsigned_commits`` — recent commits are mostly unsigned. Medium severity,
  ``security_posture``. Threshold: signing coverage < 0.2 over the last
  ``GIT_LOG_WINDOW`` commits and at least 5 commits exist.
- ``missing_codeowners`` — no ``CODEOWNERS`` file at any conventional path.
  Low severity, ``architecture_design``.
- ``bus_factor_low`` — fewer than two contributors hold ≥5% of commits over
  the analyzed window. Severity escalates with concentration: ``high`` when
  ``bus_factor == 1``, ``medium`` when ``bus_factor in (2, 3)``.
"""

from __future__ import annotations

import shutil
import subprocess
from collections import Counter
from pathlib import Path

from sdlc_assessor.detectors.common import iter_repo_files
from sdlc_assessor.normalizer.findings import build_score_impact

GIT_LOG_WINDOW = 100
GIT_TIMEOUT_SECONDS = 10
SIGNING_LOW_COVERAGE_THRESHOLD = 0.2
BUS_FACTOR_AUTHOR_SHARE_THRESHOLD = 0.05

CODEOWNERS_CANDIDATES = (
    "CODEOWNERS",
    ".github/CODEOWNERS",
    "docs/CODEOWNERS",
)


def _run_git(repo_path: Path, *args: str) -> str | None:
    """Run ``git`` with a hard timeout. Return stdout or None on any failure."""
    git = shutil.which("git")
    if git is None:
        return None
    try:
        result = subprocess.run(
            [git, "-C", str(repo_path), *args],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _is_git_repo(repo_path: Path) -> bool:
    if not (repo_path / ".git").exists():
        # Some checkouts use worktrees / submodules where .git is a file.
        return (repo_path / ".git").is_file()
    return True


def _commit_window(repo_path: Path) -> list[dict]:
    """Return the last GIT_LOG_WINDOW commits as a list of dicts."""
    fmt = "%H%x09%G?%x09%aN"
    out = _run_git(
        repo_path,
        "log",
        f"-n{GIT_LOG_WINDOW}",
        f"--pretty=format:{fmt}",
    )
    if out is None:
        return []
    commits: list[dict] = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        sha, sig, author = parts
        commits.append({"sha": sha, "signature_status": sig, "author": author.strip() or "unknown"})
    return commits


def _signing_coverage(commits: list[dict]) -> tuple[int, float]:
    """Return (signed_count, coverage_ratio) for ``commits``."""
    if not commits:
        return 0, 0.0
    signed = sum(1 for c in commits if c["signature_status"] in {"G", "U", "X", "Y"})
    return signed, signed / len(commits)


def _bus_factor(commits: list[dict]) -> tuple[int, list[dict]]:
    """Return (bus_factor, top_authors_with_share) over ``commits``.

    Bus factor here is the count of authors whose share of commits is at least
    ``BUS_FACTOR_AUTHOR_SHARE_THRESHOLD``. It's a proxy, not a true graph
    analysis, but it discriminates "one person commits 95% of the code" from
    "five people share roughly evenly."
    """
    if not commits:
        return 0, []
    counter = Counter(c["author"] for c in commits)
    total = sum(counter.values())
    ranked = counter.most_common()
    top = []
    bus_factor = 0
    for name, count in ranked:
        share = count / total
        top.append({"name": name, "commit_count": count, "share": round(share, 3)})
        if share >= BUS_FACTOR_AUTHOR_SHARE_THRESHOLD:
            bus_factor += 1
    return bus_factor, top[:10]


def _codeowners_coverage(repo_path: Path) -> tuple[Path | None, float]:
    """Return (codeowners_path or None, source-file coverage 0..1)."""
    located: Path | None = None
    for candidate in CODEOWNERS_CANDIDATES:
        path = repo_path / candidate
        if path.exists():
            located = path
            break
    if located is None:
        return None, 0.0
    try:
        text = located.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return located, 0.0
    patterns = [
        line.split()[0]
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not patterns:
        return located, 0.0
    # Coarse coverage: % of source files matched by at least one CODEOWNERS pattern.
    source_files = [p for p in iter_repo_files(repo_path)]
    if not source_files:
        return located, 0.0
    matched = 0
    for path in source_files:
        try:
            rel = path.relative_to(repo_path).as_posix()
        except ValueError:
            continue
        if any(_codeowners_match(rel, pat) for pat in patterns):
            matched += 1
    return located, matched / len(source_files)


def _codeowners_match(rel: str, pattern: str) -> bool:
    """Loose CODEOWNERS pattern match: handles `*`, leading `/`, and dir prefixes."""
    if pattern in {"*", "**"}:
        return True
    if pattern.startswith("/"):
        return rel == pattern.lstrip("/") or rel.startswith(pattern.lstrip("/"))
    if pattern.endswith("/"):
        return rel.startswith(pattern.rstrip("/") + "/")
    if "*" not in pattern and "?" not in pattern:
        return rel == pattern or rel.startswith(pattern + "/")
    # Treat as glob
    import fnmatch

    if fnmatch.fnmatch(rel, pattern):
        return True
    # Match directory descendants too
    return fnmatch.fnmatch(rel, pattern.rstrip("/") + "/*")


def collect_git_summary(repo_path: Path) -> dict | None:
    """Return the optional ``repo_meta.git_summary`` payload, or None if not a repo."""
    if not _is_git_repo(repo_path):
        return None

    commits = _commit_window(repo_path)
    signed_count, coverage = _signing_coverage(commits)
    bus_factor, top_authors = _bus_factor(commits)
    codeowners_path, codeowners_coverage = _codeowners_coverage(repo_path)

    return {
        "commits_analyzed": len(commits),
        "signed_commit_count": signed_count,
        "signing_coverage": round(coverage, 3),
        "bus_factor": bus_factor,
        "top_authors": top_authors,
        "codeowners_present": codeowners_path is not None,
        "codeowners_coverage": round(codeowners_coverage, 3),
    }


def run_git_history_detectors(repo_path: Path) -> list[dict]:
    findings: list[dict] = []
    if not _is_git_repo(repo_path):
        return findings

    commits = _commit_window(repo_path)
    if not commits:
        return findings

    signed_count, coverage = _signing_coverage(commits)
    if len(commits) >= 5 and coverage < SIGNING_LOW_COVERAGE_THRESHOLD:
        findings.append(
            {
                "category": "security_posture",
                "subcategory": "unsigned_commits",
                "severity": "medium",
                "statement": (
                    f"Commit-signing coverage is {coverage:.0%} over the last "
                    f"{len(commits)} commits ({signed_count} signed). "
                    "Without verified signatures, commit authorship is forgeable."
                ),
                "evidence": [
                    {
                        "path": ".git/log",
                        "match_type": "derived",
                        "count": len(commits),
                    }
                ],
                "confidence": "high",
                "applicability": "applicable",
                "score_impact": build_score_impact(
                    "medium",
                    rationale="Low signing coverage means committed history can be forged or altered without leaving a verifiable trail.",
                ),
                "detector_source": "git_history.unsigned_commits",
            }
        )

    bus_factor, top_authors = _bus_factor(commits)
    severity: str | None = None
    statement = ""
    if bus_factor == 1:
        severity = "high"
        statement = (
            f"Bus factor of 1 — one contributor authored ≥{BUS_FACTOR_AUTHOR_SHARE_THRESHOLD:.0%} "
            f"of the last {len(commits)} commits."
        )
    elif bus_factor in (2, 3):
        severity = "medium"
        statement = (
            f"Bus factor of {bus_factor} — only {bus_factor} contributors hold "
            f"≥{BUS_FACTOR_AUTHOR_SHARE_THRESHOLD:.0%} of the last {len(commits)} commits."
        )

    if severity is not None:
        findings.append(
            {
                "category": "architecture_design",
                "subcategory": "bus_factor_low",
                "severity": severity,
                "statement": statement,
                "evidence": [
                    {
                        "path": ".git/log",
                        "match_type": "derived",
                        "count": bus_factor,
                    }
                ],
                "confidence": "medium",
                "applicability": "applicable",
                "score_impact": build_score_impact(
                    severity,
                    rationale="Author concentration is a continuity risk; loss of a single contributor would stall the project.",
                ),
                "detector_source": "git_history.bus_factor_low",
                "tags": [f"top_author:{top_authors[0]['name']}" if top_authors else ""],
            }
        )

    codeowners_path, _coverage = _codeowners_coverage(repo_path)
    if codeowners_path is None:
        findings.append(
            {
                "category": "architecture_design",
                "subcategory": "missing_codeowners",
                "severity": "low",
                "statement": "No CODEOWNERS file found; PR review routing is unstructured.",
                "evidence": [{"path": ".github/CODEOWNERS", "match_type": "derived"}],
                "confidence": "high",
                "applicability": "applicable",
                "score_impact": build_score_impact(
                    "low",
                    rationale="CODEOWNERS makes review responsibility explicit and prevents hot files from going unreviewed.",
                ),
                "detector_source": "git_history.missing_codeowners",
            }
        )

    return findings


__all__ = [
    "run_git_history_detectors",
    "collect_git_summary",
    "GIT_LOG_WINDOW",
    "SIGNING_LOW_COVERAGE_THRESHOLD",
]
