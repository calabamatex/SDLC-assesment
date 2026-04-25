"""Common cross-language detectors (SDLC-021).

Single-pass walker with ignore-directory + binary-file discipline, ``.gitignore``
respect via ``pathspec`` when available, per-match line numbers for secrets,
widened README/SECURITY detection paths, and a 5 MB cap on file reads.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from sdlc_assessor.normalizer.findings import build_score_impact

DEFAULT_IGNORES = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        "site-packages",
        "build",
        "dist",
        ".eggs",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        ".next",
        "coverage",
        "target",
        ".tox",
        ".sdlc",
    }
)

BINARY_SUFFIXES = frozenset(
    {".exe", ".dll", ".so", ".dylib", ".class", ".jar", ".zip", ".tar", ".gz",
     ".bz2", ".xz", ".7z", ".rar", ".png", ".jpg", ".jpeg", ".gif", ".webp",
     ".pdf", ".mp3", ".mp4", ".mov", ".avi", ".woff", ".woff2", ".ttf", ".otf",
     ".ico", ".bin"}
)

ARTIFACT_SUFFIXES = frozenset(
    {".zip", ".jar", ".exe", ".dll", ".tar", ".gz", ".whl", ".pyc"}
)

CREDENTIAL_SUFFIXES = frozenset({".pem", ".key", ".p12", ".pfx"})
CREDENTIAL_BASENAMES = frozenset({"id_rsa", "id_dsa", "id_ed25519", "id_ecdsa"})

DEFAULT_MAX_FILE_SIZE = 5_000_000  # 5 MB

SECRET_PATTERN = re.compile(
    r"(?P<key>api[_-]?key|secret|token|password)\s*[:=]\s*['\"](?P<val>[^'\"]+)['\"]",
    re.IGNORECASE,
)

# Whitelist values that are obviously placeholders or templates.
SECRET_PLACEHOLDERS = re.compile(
    r"^(x|y|z|xxx+|placeholder|change[_-]?me|example|todo|null|none|undefined|"
    r"test|fake|dummy|\<.*\>|\$\{.*\}|0+|asdf+|qwerty)$",
    re.IGNORECASE,
)

README_CANDIDATES = (
    "README.md", "README.MD", "Readme.md", "readme.md",
    "README", "README.rst", "README.txt",
    "docs/README.md", ".github/README.md",
)

SECURITY_CANDIDATES = (
    "SECURITY.md", "security.md", ".github/SECURITY.md", "docs/SECURITY.md",
)


def _looks_binary(path: Path) -> bool:
    """Heuristic: read first 8 KB, return True if a NUL byte is present."""
    if path.suffix.lower() in BINARY_SUFFIXES:
        return True
    try:
        with path.open("rb") as fh:
            chunk = fh.read(8192)
    except OSError:
        return True
    return b"\x00" in chunk


def _load_gitignore(repo_path: Path):
    """Return a ``pathspec.PathSpec`` if ``pathspec`` is installed and a .gitignore exists."""
    gi = repo_path / ".gitignore"
    if not gi.exists():
        return None
    try:
        import pathspec
    except ImportError:
        return None
    try:
        with gi.open("r", encoding="utf-8", errors="ignore") as fh:
            spec = pathspec.PathSpec.from_lines("gitwildmatch", fh)
    except Exception:
        return None
    return spec


def iter_repo_files(
    repo_path: Path,
    *,
    ignore_dirs: frozenset[str] = DEFAULT_IGNORES,
    max_file_size: int = DEFAULT_MAX_FILE_SIZE,
    respect_gitignore: bool = True,
) -> Iterator[Path]:
    """Yield text-like files in ``repo_path`` honoring ignore-dirs + size cap.

    Files in ``ignore_dirs`` (any path component) and files exceeding
    ``max_file_size`` bytes are skipped. ``.gitignore`` is honored via
    ``pathspec`` when installed.
    """
    spec = _load_gitignore(repo_path) if respect_gitignore else None
    for entry in repo_path.rglob("*"):
        if not entry.is_file():
            continue
        if any(part in ignore_dirs for part in entry.parts):
            continue
        if spec is not None:
            try:
                rel = entry.relative_to(repo_path).as_posix()
            except ValueError:
                rel = entry.as_posix()
            if spec.match_file(rel):
                continue
        try:
            size = entry.stat().st_size
        except OSError:
            continue
        if size > max_file_size:
            continue
        yield entry


def _has_any(repo_path: Path, candidates) -> bool:
    return any((repo_path / candidate).exists() for candidate in candidates)


def run_common_detectors(repo_path: Path) -> list[dict]:
    findings: list[dict] = []

    # Single-pass walk.
    large_file_records: list[tuple[Path, int]] = []
    artifact_records: list[Path] = []
    credential_records: list[Path] = []

    for path in iter_repo_files(repo_path, max_file_size=10**12):  # bypass cap to find large files first
        try:
            size = path.stat().st_size
        except OSError:
            continue
        suffix = path.suffix.lower()
        if size > 100_000:
            large_file_records.append((path, size))
        if suffix in ARTIFACT_SUFFIXES:
            artifact_records.append(path)
        if suffix in CREDENTIAL_SUFFIXES or path.name.lower() in CREDENTIAL_BASENAMES:
            credential_records.append(path)

        if size > DEFAULT_MAX_FILE_SIZE:
            continue
        if _looks_binary(path):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for match in SECRET_PATTERN.finditer(text):
            value = match.group("val")
            if SECRET_PLACEHOLDERS.match(value or ""):
                continue
            line_start = text.count("\n", 0, match.start()) + 1
            snippet_line = text.splitlines()[line_start - 1] if line_start - 1 < len(text.splitlines()) else ""
            rel = path.relative_to(repo_path).as_posix() if path.is_absolute() else str(path)
            findings.append(
                {
                    "category": "security_posture",
                    "subcategory": "probable_secrets",
                    "severity": "high",
                    "statement": "Probable hardcoded secret detected.",
                    "evidence": [
                        {
                            "path": rel,
                            "line_start": line_start,
                            "line_end": line_start,
                            "snippet": snippet_line.rstrip(),
                            "match_type": "pattern",
                            "count": 1,
                        }
                    ],
                    "confidence": "medium",
                    "applicability": "applicable",
                    "score_impact": build_score_impact(
                        "high", rationale="Hardcoded credential exposed in repository contents."
                    ),
                    "detector_source": "common.probable_secrets",
                }
            )

    for path, size in large_file_records:
        rel = path.relative_to(repo_path).as_posix() if path.is_absolute() else str(path)
        findings.append(
            {
                "category": "maintainability_operability",
                "subcategory": "large_files",
                "severity": "low",
                "statement": "Large file detected in repository.",
                "evidence": [{"path": rel, "match_type": "inventory", "count": 1}],
                "confidence": "high",
                "applicability": "applicable",
                "score_impact": build_score_impact(
                    "low", rationale=f"File size {size} bytes exceeds 100KB threshold."
                ),
                "detector_source": "common.large_files",
            }
        )

    for path in artifact_records:
        rel = path.relative_to(repo_path).as_posix() if path.is_absolute() else str(path)
        findings.append(
            {
                "category": "dependency_release_hygiene",
                "subcategory": "committed_artifacts",
                "severity": "medium",
                "statement": "Committed binary/archive artifact detected.",
                "evidence": [{"path": rel, "match_type": "exact", "count": 1}],
                "confidence": "high",
                "applicability": "applicable",
                "score_impact": build_score_impact(
                    "medium", rationale="Binary artifacts inflate repo size and bypass dependency tracking."
                ),
                "detector_source": "common.committed_artifacts",
            }
        )

    for path in credential_records:
        rel = path.relative_to(repo_path).as_posix() if path.is_absolute() else str(path)
        findings.append(
            {
                "category": "security_posture",
                "subcategory": "committed_credential",
                "severity": "critical",
                "statement": "Credential-shaped file committed to the repository.",
                "evidence": [{"path": rel, "match_type": "exact", "count": 1}],
                "confidence": "high",
                "applicability": "applicable",
                "score_impact": build_score_impact(
                    "critical", rationale="Private-key or credential file present in repository tree."
                ),
                "detector_source": "common.committed_credential",
            }
        )

    workflows = repo_path / ".github" / "workflows"
    if not workflows.exists() or not any(workflows.glob("*.y*ml")):
        findings.append(
            {
                "category": "testing_quality_gates",
                "subcategory": "missing_ci",
                "severity": "medium",
                "statement": "No CI workflows detected.",
                "evidence": [{"path": ".github/workflows", "match_type": "derived"}],
                "confidence": "high",
                "applicability": "applicable",
                "score_impact": build_score_impact(
                    "medium", rationale="No automated test gate on commits or pull requests."
                ),
                "detector_source": "common.missing_ci",
            }
        )

    if not _has_any(repo_path, README_CANDIDATES):
        findings.append(
            {
                "category": "documentation_truthfulness",
                "subcategory": "missing_readme",
                "severity": "medium",
                "statement": "README file is missing.",
                "evidence": [{"path": "README.md", "match_type": "derived"}],
                "confidence": "high",
                "applicability": "applicable",
                "score_impact": build_score_impact(
                    "medium", rationale="No README means the project is undocumented at the entry point."
                ),
                "detector_source": "common.missing_readme",
            }
        )

    if not _has_any(repo_path, SECURITY_CANDIDATES):
        findings.append(
            {
                "category": "security_posture",
                "subcategory": "missing_security_md",
                "severity": "low",
                "statement": "SECURITY.md file is missing.",
                "evidence": [{"path": "SECURITY.md", "match_type": "derived"}],
                "confidence": "high",
                "applicability": "applicable",
                "score_impact": build_score_impact(
                    "low", rationale="No documented vulnerability disclosure path."
                ),
                "detector_source": "common.missing_security_md",
            }
        )

    return findings


__all__ = ["iter_repo_files", "run_common_detectors", "DEFAULT_IGNORES", "DEFAULT_MAX_FILE_SIZE"]
