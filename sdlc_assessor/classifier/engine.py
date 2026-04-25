"""Classifier engine — infers archetype, maturity, network exposure, release surface.

SDLC-014: a single ignore-aware traversal replaces the per-language ``rglob``
hack so JS-only and TSX-only repos correctly trigger the TS/JS pack and
vendored ``node_modules`` is ignored.

SDLC-016: every field is computed from concrete signals; ``unknown`` is only
used when no signal exists.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

# Directories that should never count as part of the assessed repo's own code.
DEFAULT_EXCLUDES = frozenset(
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

LANGUAGE_SUFFIXES: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript_javascript",
    ".tsx": "typescript_javascript",
    ".js": "typescript_javascript",
    ".jsx": "typescript_javascript",
    ".mjs": "typescript_javascript",
    ".cjs": "typescript_javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".cs": "csharp",
    ".kt": "kotlin",
    ".kts": "kotlin",
}

NETWORK_PATTERNS = re.compile(
    r"\b(fastapi|flask|django|express|actix-web|axum|gin\.Default|"
    r"http\.ListenAndServe|app\.listen|server\.listen|socket\.bind)\b",
    re.IGNORECASE,
)

NOTEBOOK_DIR_HINTS = ("notebooks", "experiments")
INFRA_FILES = ("terraform", "ansible", "helm", "kustomization.yaml")
INFRA_SUFFIXES = (".tf",)


@dataclass(slots=True)
class ClassificationResult:
    repo_archetype: str
    maturity_profile: str
    deployment_surface: str
    network_exposure: bool
    release_surface: str
    classification_confidence: float
    language_pack_selection: list[str]
    rationale: list[str] = field(default_factory=list)


def _iter_source_files(repo_path: Path, *, max_size: int = 5_000_000):
    """Yield text-like files in ``repo_path`` skipping ``DEFAULT_EXCLUDES``."""
    for entry in repo_path.rglob("*"):
        if not entry.is_file():
            continue
        if any(part in DEFAULT_EXCLUDES for part in entry.parts):
            continue
        suffix = entry.suffix.lower()
        if suffix in BINARY_SUFFIXES:
            continue
        try:
            if entry.stat().st_size > max_size:
                continue
        except OSError:
            continue
        yield entry


def _detect_language_packs(language_counts: dict[str, int]) -> list[str]:
    packs = ["common"]
    pack_names = set()
    for suffix, pack in LANGUAGE_SUFFIXES.items():
        if language_counts.get(suffix, 0) > 0:
            pack_names.add(pack)
    # Only include packs that are actually implemented today.
    if "python" in pack_names:
        packs.append("python")
    if "typescript_javascript" in pack_names:
        packs.append("typescript_javascript")
    return packs


def _scan_for_signals(repo_path: Path) -> dict:
    """Single-pass walk recording archetype/network/maturity signals."""
    language_counts: dict[str, int] = {}
    network_hit_paths: list[str] = []
    notebook_count = 0
    infra_hits: list[str] = []
    has_dockerfile = False
    has_compose = False
    has_serverless = False
    has_helm = False

    for path in _iter_source_files(repo_path):
        rel = path.relative_to(repo_path).as_posix()
        suffix = path.suffix.lower()
        if suffix in LANGUAGE_SUFFIXES:
            language_counts[suffix] = language_counts.get(suffix, 0) + 1
        if suffix == ".ipynb":
            notebook_count += 1
        if suffix in INFRA_SUFFIXES or any(part == hint for part in path.parts for hint in INFRA_FILES):
            infra_hits.append(rel)
        name = path.name.lower()
        if name == "dockerfile":
            has_dockerfile = True
        if name in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"):
            has_compose = True
        if name == "serverless.yml" or name == "serverless.yaml":
            has_serverless = True
        if "helm" in path.parts or name == "chart.yaml":
            has_helm = True
        # Read text files for network signal scanning.
        if suffix in {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".go", ".rs", ".java", ".cs", ".kt"}:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if NETWORK_PATTERNS.search(text):
                network_hit_paths.append(rel)

    has_pyproject = (repo_path / "pyproject.toml").exists()
    has_setup_cfg = (repo_path / "setup.cfg").exists()
    has_package_json = (repo_path / "package.json").exists()
    has_cargo = (repo_path / "Cargo.toml").exists()
    workflows = repo_path / ".github" / "workflows"
    has_ci = workflows.exists() and any(workflows.glob("*.y*ml"))
    has_release_workflow = workflows.exists() and any(
        (workflows / name).exists() for name in ("release.yml", "release.yaml", "publish.yml", "publish.yaml")
    )
    has_readme = any(
        (repo_path / candidate).exists()
        for candidate in (
            "README.md", "Readme.md", "readme.md", "README", "README.rst",
            "README.txt", "docs/README.md", ".github/README.md",
        )
    )
    has_tests_dir = (repo_path / "tests").exists() or (repo_path / "test").exists()
    has_src_layout = (repo_path / "src").is_dir()
    has_notebooks_dir = any((repo_path / hint).is_dir() for hint in NOTEBOOK_DIR_HINTS)

    # Multiple subdir manifests → monorepo signal
    sub_manifests = 0
    for candidate in repo_path.rglob("pyproject.toml"):
        if any(part in DEFAULT_EXCLUDES for part in candidate.parts):
            continue
        if candidate.parent != repo_path:
            sub_manifests += 1
    for candidate in repo_path.rglob("package.json"):
        if any(part in DEFAULT_EXCLUDES for part in candidate.parts):
            continue
        if candidate.parent != repo_path:
            sub_manifests += 1

    pyproject_text = ""
    has_project_scripts = False
    has_project_name_version = False
    if has_pyproject:
        try:
            pyproject_text = (repo_path / "pyproject.toml").read_text(encoding="utf-8", errors="ignore")
        except OSError:
            pyproject_text = ""
        has_project_scripts = "[project.scripts]" in pyproject_text
        has_project_name_version = (
            re.search(r"^\s*name\s*=", pyproject_text, re.MULTILINE) is not None
            and re.search(r"^\s*version\s*=", pyproject_text, re.MULTILINE) is not None
        )

    package_json_text = ""
    if has_package_json:
        import contextlib

        with contextlib.suppress(OSError):
            package_json_text = (repo_path / "package.json").read_text(encoding="utf-8", errors="ignore")

    package_json_publishable = False
    if package_json_text:
        try:
            data = json.loads(package_json_text)
            package_json_publishable = (
                isinstance(data.get("name"), str)
                and isinstance(data.get("version"), str)
                and not data.get("private", False)
            )
        except json.JSONDecodeError:
            package_json_publishable = False

    return {
        "language_counts": language_counts,
        "network_hits": network_hit_paths,
        "network_exposure": bool(network_hit_paths),
        "notebook_count": notebook_count,
        "infra_hits": infra_hits,
        "has_dockerfile": has_dockerfile,
        "has_compose": has_compose,
        "has_serverless": has_serverless,
        "has_helm": has_helm,
        "has_pyproject": has_pyproject,
        "has_setup_cfg": has_setup_cfg,
        "has_package_json": has_package_json,
        "has_cargo": has_cargo,
        "has_ci": has_ci,
        "has_release_workflow": has_release_workflow,
        "has_readme": has_readme,
        "has_tests_dir": has_tests_dir,
        "has_src_layout": has_src_layout,
        "has_notebooks_dir": has_notebooks_dir,
        "sub_manifests": sub_manifests,
        "has_project_scripts": has_project_scripts,
        "has_project_name_version": has_project_name_version,
        "package_json_publishable": package_json_publishable,
    }


def _infer_archetype(signals: dict) -> tuple[str, list[str]]:
    rationale: list[str] = []

    if signals["sub_manifests"] >= 2:
        rationale.append(f"{signals['sub_manifests']} sub-package manifests → monorepo")
        return "monorepo", rationale

    notebook_total = signals["notebook_count"]
    py_total = signals["language_counts"].get(".py", 0)
    if notebook_total > 0 and (notebook_total >= py_total or signals["has_notebooks_dir"]):
        rationale.append(f"{notebook_total} notebooks present → research_repo")
        return "research_repo", rationale

    if signals["infra_hits"] or signals["has_helm"]:
        rationale.append(f"infrastructure manifests present ({len(signals['infra_hits'])} hits)")
        return "infrastructure", rationale

    has_service_manifests = signals["has_dockerfile"] or signals["has_compose"] or signals["has_serverless"]
    if has_service_manifests and signals["network_exposure"]:
        rationale.append("service manifests + network-exposing imports → service")
        return "service", rationale

    if signals["has_project_scripts"] and not signals["network_exposure"]:
        rationale.append("[project.scripts] present and no server-framework imports → cli")
        return "cli", rationale

    if signals["has_project_name_version"] and not signals["has_project_scripts"]:
        rationale.append("pyproject [project] name+version, no scripts → library")
        return "library", rationale

    if signals["package_json_publishable"]:
        rationale.append("publishable package.json → library (npm)")
        return "library", rationale

    if signals["has_pyproject"] or signals["has_package_json"] or signals["has_cargo"]:
        rationale.append("project manifest present, no clear archetype signal → internal_tool")
        return "internal_tool", rationale

    rationale.append("no archetype signal detected")
    return "unknown", rationale


def _infer_release_surface(archetype: str, signals: dict) -> str:
    if archetype == "research_repo":
        return "research_only"
    if signals["has_dockerfile"] or signals["has_compose"] or signals["has_serverless"]:
        return "deployable_service"
    if signals["has_project_name_version"] and signals["has_release_workflow"]:
        return "published_package"
    if signals["package_json_publishable"] and signals["has_release_workflow"]:
        return "published_package"
    if signals["has_project_name_version"] or signals["package_json_publishable"]:
        return "published_package"
    return "internal_only"


def _infer_maturity(signals: dict) -> str:
    notebook_total = signals["notebook_count"]
    py_total = signals["language_counts"].get(".py", 0)
    if notebook_total > 0 and notebook_total >= max(py_total, 1):
        return "research"
    if signals["has_ci"] and signals["has_tests_dir"] and signals["has_project_name_version"]:
        return "production"
    if signals["has_readme"] and not signals["has_ci"]:
        return "prototype"
    if signals["has_readme"]:
        return "prototype"
    return "unknown"


def _infer_deployment_surface(archetype: str, signals: dict) -> str:
    if signals["network_exposure"]:
        return "networked"
    if archetype == "library":
        return "package_only"
    if archetype == "cli":
        return "local_only"
    if archetype in {"service", "infrastructure"}:
        return "networked" if signals["network_exposure"] else "mixed"
    return "unknown"


def _confidence(signals: dict) -> float:
    agree = 0
    if signals["has_pyproject"] or signals["has_package_json"] or signals["has_cargo"]:
        agree += 1
    if signals["has_project_scripts"] or signals["package_json_publishable"]:
        agree += 1
    if signals["has_dockerfile"] or signals["has_compose"] or signals["has_serverless"]:
        agree += 1
    if signals["has_ci"]:
        agree += 1
    if signals["has_readme"]:
        agree += 1
    if signals["has_tests_dir"]:
        agree += 1
    if agree >= 3:
        return 0.9
    if agree == 2:
        return 0.6
    if agree == 1:
        return 0.3
    return 0.2


def _detect(repo_path: Path) -> ClassificationResult:
    signals = _scan_for_signals(repo_path)
    archetype, rationale = _infer_archetype(signals)
    rationale.extend(
        [
            f"language counts: {dict(sorted(signals['language_counts'].items()))}",
            f"network_exposure={signals['network_exposure']} ({len(signals['network_hits'])} hits)",
            f"has_ci={signals['has_ci']}, has_tests_dir={signals['has_tests_dir']}, has_readme={signals['has_readme']}",
        ]
    )
    release_surface = _infer_release_surface(archetype, signals)
    maturity = _infer_maturity(signals)
    deployment = _infer_deployment_surface(archetype, signals)
    confidence = _confidence(signals)
    packs = _detect_language_packs(signals["language_counts"])
    return ClassificationResult(
        repo_archetype=archetype,
        maturity_profile=maturity,
        deployment_surface=deployment,
        network_exposure=signals["network_exposure"],
        release_surface=release_surface,
        classification_confidence=confidence,
        language_pack_selection=packs,
        rationale=rationale,
    )


def classify_repo(repo_target: str) -> dict:
    repo_path = Path(repo_target)
    if not repo_path.exists() or not repo_path.is_dir():
        raise ValueError(f"Repository path does not exist or is not a directory: {repo_target}")

    result = _detect(repo_path)

    payload = {
        "repo_meta": {
            "name": repo_path.name,
            "default_branch": "unknown",
            "analysis_timestamp": datetime.now(UTC).isoformat(),
        },
        "classification": asdict(result),
    }
    return payload
