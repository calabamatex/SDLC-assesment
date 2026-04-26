"""SAST adapter framework (SDLC-050).

A small base layer that turns external static-analysis tools into another
detector pack. Each adapter inherits from :class:`SASTAdapter`, declares its
``tool_name`` and ``ecosystems``, and implements :meth:`build_command` and
:meth:`parse_output`. The framework handles:

- **Availability detection.** Tools missing from PATH cause the adapter to
  no-op silently (no crash, no warning spam).
- **Subprocess discipline.** Argument-array invocation (no shell), hard
  timeout, captured output, tolerated non-zero exits (most SAST tools
  return non-zero when they find something — that's signal, not failure).
- **Caching.** Results keyed on ``(tool_name, tool_version, repo_state_hash)``
  under ``.sdlc/sast-cache/<key>.json``. Re-running with no source changes
  is instant. Cache is opt-in via ``SDLC_SAST_CACHE=1`` so the default
  behaviour is fresh-on-every-run.
- **Schema mapping.** Adapters return raw findings in their tool's native
  shape; the framework runs them through ``build_score_impact`` and
  attaches the standard ``detector_source`` / ``confidence`` fields so the
  finding is shape-compatible with the rest of the pipeline.

A single :func:`run_sast_adapters` entry point dispatches all registered
adapters in order. The detector registry calls this once per pipeline run.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import warnings
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sdlc_assessor.detectors.common import iter_repo_files
from sdlc_assessor.normalizer.findings import build_score_impact

DEFAULT_TIMEOUT_SECONDS = 60
CACHE_DIR_NAME = "sast-cache"


@dataclass(slots=True)
class SASTResult:
    """A normalised raw finding produced by an adapter's ``parse_output``."""

    subcategory: str
    severity: str
    category: str
    statement: str
    path: str
    line_start: int | None = None
    line_end: int | None = None
    snippet: str | None = None
    rationale: str | None = None
    confidence: str = "high"
    rule_id: str | None = None
    tags: list[str] = field(default_factory=list)


class SASTAdapter(ABC):
    """Base class for an external SAST tool adapter.

    Subclasses set ``tool_name`` (the executable name on PATH) and
    ``ecosystems`` (which language families this adapter applies to —
    used by :meth:`should_run` for cheap pre-filtering).
    """

    tool_name: str = ""
    ecosystems: tuple[str, ...] = ()  # e.g. ("python",), ("javascript", "typescript")
    detector_source: str = ""
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS

    def is_available(self) -> bool:
        """Return True when the tool is on PATH."""
        return shutil.which(self.tool_name) is not None

    def tool_version(self) -> str | None:
        """Return a stable version string for cache keying. None on failure."""
        out = self._safe_run([self.tool_name, "--version"], timeout=5)
        if out is None:
            return None
        return out.strip().splitlines()[0] if out.strip() else None

    def should_run(self, repo_path: Path) -> bool:
        """Cheap precheck: only run when the repo has files in our ecosystems."""
        if not self.ecosystems:
            return True
        targets = self._ecosystem_suffixes()
        return any(p.suffix.lower() in targets for p in iter_repo_files(repo_path))

    def _ecosystem_suffixes(self) -> set[str]:
        mapping = {
            "python": {".py"},
            "javascript": {".js", ".jsx", ".mjs", ".cjs"},
            "typescript": {".ts", ".tsx"},
            "go": {".go"},
            "rust": {".rs"},
            "java": {".java"},
            "csharp": {".cs"},
        }
        out: set[str] = set()
        for eco in self.ecosystems:
            out |= mapping.get(eco, set())
        return out

    @abstractmethod
    def build_command(self, repo_path: Path) -> list[str]:
        """Return the argv that runs the tool against ``repo_path``."""

    @abstractmethod
    def parse_output(self, stdout: str, stderr: str, returncode: int) -> list[SASTResult]:
        """Parse the tool's output into normalized :class:`SASTResult`."""

    def run(self, repo_path: Path) -> list[dict]:
        """Run the adapter end-to-end. Returns schema-shaped findings."""
        if not self.is_available():
            return []
        if not self.should_run(repo_path):
            return []

        cache_key = self._cache_key(repo_path)
        cached = self._read_cache(repo_path, cache_key) if cache_key else None
        if cached is not None:
            return cached

        argv = self.build_command(repo_path)
        completed = self._run_subprocess(argv, cwd=repo_path)
        if completed is None:
            return []
        results = self.parse_output(completed["stdout"], completed["stderr"], completed["returncode"])
        findings = [self._to_finding(r) for r in results]

        if cache_key:
            self._write_cache(repo_path, cache_key, findings)
        return findings

    # ----- internal helpers ---------------------------------------------------

    def _safe_run(self, argv: list[str], *, timeout: int) -> str | None:
        try:
            result = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError):
            return None
        return result.stdout

    def _run_subprocess(self, argv: list[str], *, cwd: Path) -> dict | None:
        try:
            result = subprocess.run(
                argv,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            warnings.warn(
                f"SAST adapter {self.tool_name!r} exceeded {self.timeout_seconds}s timeout; "
                "skipping its findings for this run.",
                stacklevel=2,
            )
            return None
        except OSError as exc:
            warnings.warn(
                f"SAST adapter {self.tool_name!r} failed to launch: {exc}",
                stacklevel=2,
            )
            return None
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    def _cache_key(self, repo_path: Path) -> str | None:
        if os.environ.get("SDLC_SAST_CACHE") != "1":
            return None
        version = self.tool_version() or "unknown"
        sources_digest = self._fingerprint_sources(repo_path)
        digest = hashlib.sha256(
            f"{self.tool_name}|{version}|{sources_digest}".encode()
        ).hexdigest()[:16]
        return digest

    def _fingerprint_sources(self, repo_path: Path) -> str:
        """Quick fingerprint: sorted (path, mtime, size) over ecosystem files."""
        targets = self._ecosystem_suffixes() or None
        h = hashlib.sha256()
        for path in sorted(iter_repo_files(repo_path)):
            if targets and path.suffix.lower() not in targets:
                continue
            try:
                st = path.stat()
            except OSError:
                continue
            try:
                rel = path.relative_to(repo_path).as_posix()
            except ValueError:
                rel = str(path)
            h.update(f"{rel}|{st.st_mtime}|{st.st_size}".encode())
        return h.hexdigest()

    def _cache_path(self, repo_path: Path, key: str) -> Path:
        return repo_path / ".sdlc" / CACHE_DIR_NAME / f"{self.tool_name}-{key}.json"

    def _read_cache(self, repo_path: Path, key: str) -> list[dict] | None:
        path = self._cache_path(repo_path, key)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _write_cache(self, repo_path: Path, key: str, findings: list[dict]) -> None:
        path = self._cache_path(repo_path, key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(findings, sort_keys=True), encoding="utf-8")
        except OSError:
            pass

    def _to_finding(self, result: SASTResult) -> dict:
        evidence: dict[str, Any] = {
            "path": result.path,
            "match_type": "exact",
        }
        if result.line_start is not None:
            evidence["line_start"] = result.line_start
            evidence["line_end"] = result.line_end if result.line_end is not None else result.line_start
        if result.snippet is not None:
            evidence["snippet"] = result.snippet
        finding: dict[str, Any] = {
            "category": result.category,
            "subcategory": result.subcategory,
            "severity": result.severity,
            "statement": result.statement,
            "evidence": [evidence],
            "confidence": result.confidence,
            "applicability": "applicable",
            "score_impact": build_score_impact(
                result.severity,
                rationale=result.rationale or result.statement,
            ),
            "detector_source": self.detector_source or f"sast.{self.tool_name}",
        }
        tags = list(result.tags)
        if result.rule_id:
            tags.append(f"rule:{result.rule_id}")
        if tags:
            finding["tags"] = tags
        return finding


# Adapter registry — populated by per-tool modules at import time.
_REGISTERED_ADAPTERS: list[SASTAdapter] = []


def register_adapter(adapter: SASTAdapter) -> None:
    """Add ``adapter`` to the dispatch list."""
    _REGISTERED_ADAPTERS.append(adapter)


def registered_adapters() -> list[SASTAdapter]:
    return list(_REGISTERED_ADAPTERS)


def run_sast_adapters(repo_path: Path) -> list[dict]:
    """Dispatch every registered adapter and concatenate their findings."""
    findings: list[dict] = []
    for adapter in _REGISTERED_ADAPTERS:
        try:
            findings.extend(adapter.run(repo_path))
        except Exception as exc:  # belt-and-braces: never let a bad adapter break the pipeline
            warnings.warn(
                f"SAST adapter {adapter.tool_name!r} raised {type(exc).__name__}: {exc}",
                stacklevel=2,
            )
    return findings


__all__ = [
    "SASTAdapter",
    "SASTResult",
    "register_adapter",
    "registered_adapters",
    "run_sast_adapters",
]
