"""Dependency graph extractor + dependency-hygiene detector tests (SDLC-036)."""

from __future__ import annotations

from pathlib import Path

from sdlc_assessor.collector.dependencies import extract_dependency_graph
from sdlc_assessor.detectors.dependency_hygiene import (
    EXCESSIVE_RUNTIME_DEPS_THRESHOLD,
    run_dependency_hygiene,
)


def test_extract_pyproject_runtime_and_dev(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """[project]
name = "demo"
version = "0.1.0"
dependencies = ["requests>=2.0", "click==8.1.0"]

[project.optional-dependencies]
dev = ["pytest>=8", "ruff"]
docs = ["mkdocs>=1.5"]
""",
        encoding="utf-8",
    )
    graph = extract_dependency_graph(tmp_path)
    runtime_names = {entry["name"] for entry in graph["runtime"]}
    dev_names = {entry["name"] for entry in graph["dev"]}
    assert {"requests", "click"} <= runtime_names
    assert {"pytest", "ruff", "mkdocs"} <= dev_names
    # `docs` extra → dev bucket per the heuristic
    assert "mkdocs" in dev_names
    assert graph["total_packages"] == len(graph["runtime"]) + len(graph["dev"])


def test_extract_requirements_files(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("requests==2.31.0\nclick\n", encoding="utf-8")
    (tmp_path / "requirements-dev.txt").write_text("pytest>=8\n", encoding="utf-8")
    graph = extract_dependency_graph(tmp_path)
    assert any(e["name"] == "requests" for e in graph["runtime"])
    assert any(e["name"] == "pytest" for e in graph["dev"])


def test_extract_package_json(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        '{"name":"demo","version":"0.0.0","dependencies":{"react":"^18"},'
        '"devDependencies":{"jest":"^29"}}',
        encoding="utf-8",
    )
    graph = extract_dependency_graph(tmp_path)
    assert any(e["name"] == "react" for e in graph["runtime"])
    assert any(e["name"] == "jest" for e in graph["dev"])


def test_extract_cargo_toml(tmp_path: Path) -> None:
    (tmp_path / "Cargo.toml").write_text(
        """[package]
name = "demo"
version = "0.1.0"
[dependencies]
serde = "1.0"
[dev-dependencies]
proptest = "1.0"
""",
        encoding="utf-8",
    )
    graph = extract_dependency_graph(tmp_path)
    assert any(e["name"] == "serde" for e in graph["runtime"])
    assert any(e["name"] == "proptest" for e in graph["dev"])


def test_extract_go_mod(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text(
        """module example.com/demo
go 1.22
require (
    github.com/gin-gonic/gin v1.9.1
)
require github.com/stretchr/testify v1.8.4
""",
        encoding="utf-8",
    )
    graph = extract_dependency_graph(tmp_path)
    names = {e["name"] for e in graph["runtime"]}
    assert "github.com/gin-gonic/gin" in names
    assert "github.com/stretchr/testify" in names


def test_lockfile_detection(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="demo"\nversion="0"\ndependencies=["requests"]\n',
        encoding="utf-8",
    )
    (tmp_path / "uv.lock").write_text("# uv lock", encoding="utf-8")
    graph = extract_dependency_graph(tmp_path)
    assert {"path": "uv.lock", "ecosystem": "uv"} in graph["lockfiles"]


def test_lockfile_missing_finding_fires(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="demo"\nversion="0"\ndependencies=["requests"]\n',
        encoding="utf-8",
    )
    findings = run_dependency_hygiene(tmp_path)
    subcats = {f["subcategory"] for f in findings}
    assert "lockfile_missing" in subcats


def test_lockfile_missing_does_not_fire_when_lockfile_present(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="demo"\nversion="0"\ndependencies=["requests"]\n',
        encoding="utf-8",
    )
    (tmp_path / "uv.lock").write_text("# uv lock", encoding="utf-8")
    findings = run_dependency_hygiene(tmp_path)
    subcats = {f["subcategory"] for f in findings}
    assert "lockfile_missing" not in subcats


def test_excessive_runtime_deps_finding(tmp_path: Path) -> None:
    deps = "\n".join(f"pkg-{i}=={i}.0.0" for i in range(EXCESSIVE_RUNTIME_DEPS_THRESHOLD + 5))
    (tmp_path / "requirements.txt").write_text(deps + "\n", encoding="utf-8")
    findings = run_dependency_hygiene(tmp_path)
    subcats = {f["subcategory"] for f in findings}
    assert "excessive_runtime_deps" in subcats


def test_no_dependabot_finding_fires_when_deps_but_no_config(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        '{"name":"x","version":"0","dependencies":{"react":"^18"}}',
        encoding="utf-8",
    )
    findings = run_dependency_hygiene(tmp_path)
    assert "no_dependabot_or_renovate" in {f["subcategory"] for f in findings}


def test_no_dependabot_finding_silenced_when_config_present(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        '{"name":"x","version":"0","dependencies":{"react":"^18"}}',
        encoding="utf-8",
    )
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "dependabot.yml").write_text("version: 2", encoding="utf-8")
    findings = run_dependency_hygiene(tmp_path)
    assert "no_dependabot_or_renovate" not in {f["subcategory"] for f in findings}


def test_collector_inventory_includes_dependency_graph(tmp_path: Path) -> None:
    from sdlc_assessor.classifier.engine import classify_repo
    from sdlc_assessor.collector.engine import collect_evidence
    from sdlc_assessor.core.io import write_json

    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="demo"\nversion="0"\ndependencies=["requests"]\n',
        encoding="utf-8",
    )
    cls_path = tmp_path / "classification.json"
    write_json(cls_path, classify_repo(str(tmp_path)))
    evidence = collect_evidence(str(tmp_path), str(cls_path))
    assert "dependency_graph" in evidence["inventory"]
    assert evidence["inventory"]["runtime_dependencies"] >= 1
