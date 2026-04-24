"""Phase 1 classifier engine."""

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


def _detect_languages(repo_path: Path) -> list[str]:
    has_python = any(p.suffix == ".py" for p in repo_path.rglob("*.py"))
    has_ts = any(p.suffix in {".ts", ".tsx", ".js", ".jsx"} for p in repo_path.rglob("*.ts"))
    packs = ["common"]
    if has_python:
        packs.append("python")
    if has_ts:
        packs.append("typescript_javascript")
    return packs


def classify_repo(repo_target: str) -> dict:
    repo_path = Path(repo_target)
    if not repo_path.exists() or not repo_path.is_dir():
        raise ValueError(f"Repository path does not exist or is not a directory: {repo_target}")

    packs = _detect_languages(repo_path)
    result = ClassificationResult(
        repo_archetype="unknown",
        maturity_profile="unknown",
        deployment_surface="unknown",
        network_exposure=False,
        release_surface="unknown",
        classification_confidence=0.2,
        language_pack_selection=packs,
    )

    payload = {
        "repo_meta": {
            "name": repo_path.name,
            "default_branch": "unknown",
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "classification": asdict(result),
    }
    return payload
