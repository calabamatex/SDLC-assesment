"""Dependency-hygiene detector (SDLC-036).

Fires on the structural state of declared dependencies — these checks live
alongside the language packs because they apply uniformly across stacks and
read manifest data the collector already parses.

Findings emitted:

- ``lockfile_missing`` — manifest declares dependencies but no lockfile is
  present. Medium severity, ``dependency_release_hygiene``. Locks the
  install-time tree to prevent drift; missing lockfile means
  reproducibility is in the hands of whoever runs ``pip install`` at
  whichever moment.
- ``excessive_runtime_deps`` — declared runtime deps exceed a soft
  threshold (default 50). Low severity, ``dependency_release_hygiene``.
  A signal of supply-chain surface area, not a defect on its own.
- ``no_dependabot_or_renovate`` — no ``.github/dependabot.yml`` /
  ``renovate.json`` configuration found. Low severity,
  ``dependency_release_hygiene``. Worth flagging on production-maturity
  repos.
"""

from __future__ import annotations

from pathlib import Path

from sdlc_assessor.collector.dependencies import extract_dependency_graph
from sdlc_assessor.normalizer.findings import build_score_impact

LOCKFILE_BY_ECOSYSTEM = {
    "pip": ("Pipfile.lock", "requirements.lock", "requirements-lock.txt", "uv.lock"),
    "poetry": ("poetry.lock",),
    "uv": ("uv.lock",),
    "npm": ("package-lock.json",),
    "yarn": ("yarn.lock",),
    "pnpm": ("pnpm-lock.yaml",),
    "cargo": ("Cargo.lock",),
    "go": ("go.sum",),
}

EXCESSIVE_RUNTIME_DEPS_THRESHOLD = 50

DEPENDABOT_FILES = (".github/dependabot.yml", ".github/dependabot.yaml")
RENOVATE_FILES = ("renovate.json", ".github/renovate.json", ".renovaterc.json")


def _ecosystems_seen(graph: dict) -> set[str]:
    seen: set[str] = set()
    for entry in graph.get("runtime", []) + graph.get("dev", []):
        ecosystem = entry.get("ecosystem")
        if ecosystem:
            seen.add(ecosystem)
    return seen


def _lockfile_present_for(ecosystem: str, graph: dict) -> bool:
    expected = set(LOCKFILE_BY_ECOSYSTEM.get(ecosystem, ()))
    if not expected:
        return False
    seen = {entry.get("path") for entry in graph.get("lockfiles", [])}
    return bool(expected & seen)


def run_dependency_hygiene(repo_path: Path) -> list[dict]:
    findings: list[dict] = []
    graph = extract_dependency_graph(repo_path)

    runtime_count = len(graph.get("runtime", []))
    dev_count = len(graph.get("dev", []))

    ecosystems = _ecosystems_seen(graph)
    if ecosystems:
        missing_lockfile = [eco for eco in ecosystems if not _lockfile_present_for(eco, graph)]
        # Treat poetry/uv lockfiles as covering the pip ecosystem.
        if "pip" in missing_lockfile and (
            _lockfile_present_for("poetry", graph) or _lockfile_present_for("uv", graph)
        ):
            missing_lockfile.remove("pip")
        if missing_lockfile:
            findings.append(
                {
                    "category": "dependency_release_hygiene",
                    "subcategory": "lockfile_missing",
                    "severity": "medium",
                    "statement": f"Manifests declare dependencies but no lockfile is present for: {', '.join(sorted(missing_lockfile))}.",
                    "evidence": [
                        {
                            "path": "/".join(sorted({entry.get("source_manifest", "") for entry in graph.get("runtime", []) + graph.get("dev", []) if entry.get("ecosystem") in missing_lockfile})) or "(see manifests)",
                            "match_type": "derived",
                        }
                    ],
                    "confidence": "high",
                    "applicability": "applicable",
                    "score_impact": build_score_impact(
                        "medium",
                        rationale="Lockfile absence makes installs nondeterministic; reproducibility depends on whoever runs the resolver next.",
                    ),
                    "detector_source": "dependency_hygiene.lockfile_missing",
                }
            )

    if runtime_count > EXCESSIVE_RUNTIME_DEPS_THRESHOLD:
        findings.append(
            {
                "category": "dependency_release_hygiene",
                "subcategory": "excessive_runtime_deps",
                "severity": "low",
                "statement": (
                    f"{runtime_count} declared runtime dependencies "
                    f"exceeds the soft threshold of {EXCESSIVE_RUNTIME_DEPS_THRESHOLD}; "
                    "supply-chain surface area is large."
                ),
                "evidence": [{"path": "(aggregated)", "match_type": "inventory", "count": runtime_count}],
                "confidence": "medium",
                "applicability": "applicable",
                "score_impact": build_score_impact(
                    "low",
                    rationale="Each runtime dep is potential CVE surface and a transitive-tree resolution risk.",
                ),
                "detector_source": "dependency_hygiene.excessive_runtime_deps",
            }
        )

    has_dependabot = any((repo_path / candidate).exists() for candidate in DEPENDABOT_FILES)
    has_renovate = any((repo_path / candidate).exists() for candidate in RENOVATE_FILES)
    if (runtime_count + dev_count) > 0 and not (has_dependabot or has_renovate):
        findings.append(
            {
                "category": "dependency_release_hygiene",
                "subcategory": "no_dependabot_or_renovate",
                "severity": "low",
                "statement": "No Dependabot or Renovate configuration found; dependency upgrades are not automated.",
                "evidence": [{"path": ".github/dependabot.yml", "match_type": "derived"}],
                "confidence": "high",
                "applicability": "applicable",
                "score_impact": build_score_impact(
                    "low",
                    rationale="Without an automated upgrade tool, security advisories require manual triage.",
                ),
                "detector_source": "dependency_hygiene.no_dependabot_or_renovate",
            }
        )

    return findings


__all__ = ["run_dependency_hygiene", "EXCESSIVE_RUNTIME_DEPS_THRESHOLD"]
