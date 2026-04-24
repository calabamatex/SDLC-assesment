"""Repository classifier implementation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(slots=True)
class ClassificationResult:
    repo_archetype: str
    maturity_profile: str
    deployment_surface: str
    network_exposure: bool
    release_surface: str
    classification_confidence: float
    language_pack_selection: list[str]


def _has_any(repo: Path, names: set[str]) -> bool:
    lower_names = {n.lower() for n in names}
    return any(p.name.lower() in lower_names for p in repo.rglob("*") if p.is_file())


def _detect_language_packs(repo: Path) -> list[str]:
    packs = ["common"]
    has_py = any(repo.rglob("*.py"))
    has_tsjs = any(repo.rglob("*.ts")) or any(repo.rglob("*.tsx")) or any(repo.rglob("*.js")) or any(repo.rglob("*.jsx"))
    if has_py:
        packs.append("python")
    if has_tsjs:
        packs.append("typescript_javascript")
    return packs


def _classify_archetype(repo: Path) -> str:
    if (repo / "docker-compose.yml").exists() or (repo / "Dockerfile").exists():
        return "service"
    if any(repo.rglob("*.tf")):
        return "infrastructure"
    if (repo / "package.json").exists() and ((repo / "bin").exists() or (repo / "src" / "cli").exists()):
        return "cli"
    if (repo / "package.json").exists() or (repo / "pyproject.toml").exists():
        return "library"
    if _has_any(repo, {"paper.md", "experiment.py", "notebook.ipynb"}):
        return "research_repo"
    return "unknown"


def _classify_maturity(repo: Path) -> str:
    has_ci = (repo / ".github" / "workflows").exists()
    has_tests = (repo / "tests").exists() or any(repo.rglob("test_*.py"))
    if has_ci and has_tests:
        return "production"
    if _has_any(repo, {"paper.md", "experiments.md", "research.md"}):
        return "research"
    return "prototype"


def _deployment_surface(repo: Path) -> tuple[str, bool]:
    network_files = {"main.py", "app.py", "server.py", "api.ts", "server.ts"}
    if any(p.name in network_files for p in repo.rglob("*")):
        return "networked", True
    if (repo / "package.json").exists() or (repo / "pyproject.toml").exists():
        return "package_only", False
    return "local_only", False


def _release_surface(repo: Path, archetype: str) -> str:
    if archetype == "service":
        return "deployable_service"
    if archetype in {"library", "sdk", "cli"}:
        return "published_package"
    if archetype == "research_repo":
        return "research_only"
    return "internal_only"


def classify_repo(repo_target: str) -> dict:
    repo = Path(repo_target)
    if not repo.exists() or not repo.is_dir():
        raise ValueError(f"Repository path does not exist or is not a directory: {repo_target}")

    archetype = _classify_archetype(repo)
    maturity = _classify_maturity(repo)
    deployment_surface, network_exposure = _deployment_surface(repo)
    packs = _detect_language_packs(repo)

    confidence = 0.45
    if archetype != "unknown":
        confidence += 0.2
    if maturity != "prototype":
        confidence += 0.15
    if len(packs) > 1:
        confidence += 0.1
    confidence = min(confidence, 0.95)

    result = ClassificationResult(
        repo_archetype=archetype,
        maturity_profile=maturity,
        deployment_surface=deployment_surface,
        network_exposure=network_exposure,
        release_surface=_release_surface(repo, archetype),
        classification_confidence=round(confidence, 2),
        language_pack_selection=packs,
    )

    return {
        "repo_meta": {
            "name": repo.name,
            "default_branch": "main",
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "classification": asdict(result),
    }
