"""Dependency graph extractor (SDLC-036).

Parses the manifest and lockfile formats commonly found in Python, JavaScript,
Rust, and Go projects, and emits a structured ``inventory.dependency_graph``
object plus simple count fields used by the scorer.

The parsers are intentionally small and tolerant — they extract enough to
populate the schema's ``dependency_entry`` shape without trying to fully
resolve transitive trees. Anything that can't be parsed cleanly is skipped
rather than raising, so a malformed manifest never breaks the pipeline.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

ECOSYSTEMS = {"pip", "poetry", "uv", "npm", "yarn", "pnpm", "cargo", "go"}


# ---------------------------------------------------------------------------
# Manifest parsers (declared dependencies)
# ---------------------------------------------------------------------------

_REQ_LINE_RE = re.compile(r"^\s*([A-Za-z0-9_.\-]+)(\s*[<>=!~][^;#\s]+)?")


def _parse_requirements_txt(path: Path, ecosystem: str = "pip") -> list[dict]:
    entries: list[dict] = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return entries
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith(("-r ", "--requirement ", "-e ", "--editable", "-c ", "--constraint")):
            continue
        match = _REQ_LINE_RE.match(line)
        if not match:
            continue
        name = match.group(1)
        constraint = (match.group(2) or "").strip()
        entries.append(
            {
                "name": name,
                "version_constraint": constraint or None,
                "ecosystem": ecosystem,
                "source_manifest": str(path.name),
            }
        )
    return entries


def _parse_pyproject(path: Path) -> tuple[list[dict], list[dict]]:
    runtime: list[dict] = []
    dev: list[dict] = []
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return runtime, dev

    project = data.get("project") or {}
    for raw in project.get("dependencies", []) or []:
        if not isinstance(raw, str):
            continue
        match = _REQ_LINE_RE.match(raw)
        if not match:
            continue
        runtime.append(
            {
                "name": match.group(1),
                "version_constraint": (match.group(2) or "").strip() or None,
                "ecosystem": "pip",
                "source_manifest": "pyproject.toml",
            }
        )
    optional = project.get("optional-dependencies") or {}
    for extra_name, items in optional.items():
        bucket = dev if extra_name in {"dev", "tests", "test", "lint", "doc", "docs"} else runtime
        for raw in items or []:
            if not isinstance(raw, str):
                continue
            match = _REQ_LINE_RE.match(raw)
            if not match:
                continue
            bucket.append(
                {
                    "name": match.group(1),
                    "version_constraint": (match.group(2) or "").strip() or None,
                    "ecosystem": "pip",
                    "source_manifest": f"pyproject.toml [optional-dependencies.{extra_name}]",
                }
            )

    poetry = data.get("tool", {}).get("poetry", {}) if isinstance(data.get("tool"), dict) else {}
    if poetry:
        for name, spec in (poetry.get("dependencies") or {}).items():
            if name == "python":
                continue
            constraint = spec if isinstance(spec, str) else (spec.get("version") if isinstance(spec, dict) else None)
            runtime.append(
                {
                    "name": name,
                    "version_constraint": constraint,
                    "ecosystem": "poetry",
                    "source_manifest": "pyproject.toml [tool.poetry.dependencies]",
                }
            )
        for group_name, group in (poetry.get("group") or {}).items():
            for name, spec in (group.get("dependencies") or {}).items():
                constraint = spec if isinstance(spec, str) else (spec.get("version") if isinstance(spec, dict) else None)
                dev.append(
                    {
                        "name": name,
                        "version_constraint": constraint,
                        "ecosystem": "poetry",
                        "source_manifest": f"pyproject.toml [tool.poetry.group.{group_name}.dependencies]",
                    }
                )

    return runtime, dev


def _parse_package_json(path: Path) -> tuple[list[dict], list[dict]]:
    runtime: list[dict] = []
    dev: list[dict] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, json.JSONDecodeError):
        return runtime, dev
    for name, version in (data.get("dependencies") or {}).items():
        if not isinstance(name, str):
            continue
        runtime.append(
            {
                "name": name,
                "version_constraint": version if isinstance(version, str) else None,
                "ecosystem": "npm",
                "source_manifest": "package.json",
            }
        )
    for name, version in (data.get("devDependencies") or {}).items():
        if not isinstance(name, str):
            continue
        dev.append(
            {
                "name": name,
                "version_constraint": version if isinstance(version, str) else None,
                "ecosystem": "npm",
                "source_manifest": "package.json",
            }
        )
    return runtime, dev


def _parse_cargo_toml(path: Path) -> tuple[list[dict], list[dict]]:
    runtime: list[dict] = []
    dev: list[dict] = []
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return runtime, dev
    for name, spec in (data.get("dependencies") or {}).items():
        constraint = spec if isinstance(spec, str) else (spec.get("version") if isinstance(spec, dict) else None)
        runtime.append(
            {
                "name": name,
                "version_constraint": constraint,
                "ecosystem": "cargo",
                "source_manifest": "Cargo.toml",
            }
        )
    for name, spec in (data.get("dev-dependencies") or {}).items():
        constraint = spec if isinstance(spec, str) else (spec.get("version") if isinstance(spec, dict) else None)
        dev.append(
            {
                "name": name,
                "version_constraint": constraint,
                "ecosystem": "cargo",
                "source_manifest": "Cargo.toml",
            }
        )
    return runtime, dev


_GO_REQUIRE_RE = re.compile(r"^\s*([\w./\-]+)\s+(v[\w.\-+]+)\s*$")


def _parse_go_mod(path: Path) -> list[dict]:
    entries: list[dict] = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return entries
    in_require_block = False
    for raw in text.splitlines():
        line = raw.split("//", 1)[0].rstrip()
        if not line:
            continue
        if line.strip() == "require (":
            in_require_block = True
            continue
        if in_require_block:
            if line.strip() == ")":
                in_require_block = False
                continue
            match = _GO_REQUIRE_RE.match(line)
            if match:
                entries.append(
                    {
                        "name": match.group(1),
                        "version_constraint": match.group(2),
                        "ecosystem": "go",
                        "source_manifest": "go.mod",
                    }
                )
        elif line.startswith("require "):
            stripped = line[len("require "):]
            match = _GO_REQUIRE_RE.match(stripped)
            if match:
                entries.append(
                    {
                        "name": match.group(1),
                        "version_constraint": match.group(2),
                        "ecosystem": "go",
                        "source_manifest": "go.mod",
                    }
                )
    return entries


# ---------------------------------------------------------------------------
# Lockfile detection
# ---------------------------------------------------------------------------

LOCKFILES = (
    ("requirements.lock", "pip"),
    ("requirements-lock.txt", "pip"),
    ("pip.lock", "pip"),
    ("Pipfile.lock", "pip"),
    ("poetry.lock", "poetry"),
    ("uv.lock", "uv"),
    ("package-lock.json", "npm"),
    ("yarn.lock", "yarn"),
    ("pnpm-lock.yaml", "pnpm"),
    ("Cargo.lock", "cargo"),
    ("go.sum", "go"),
)


def _find_lockfiles(repo_path: Path) -> list[dict]:
    out: list[dict] = []
    for filename, ecosystem in LOCKFILES:
        candidate = repo_path / filename
        if candidate.exists():
            out.append({"path": filename, "ecosystem": ecosystem})
    return out


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------


def extract_dependency_graph(repo_path: Path) -> dict:
    """Return the ``inventory.dependency_graph`` payload for ``repo_path``."""
    runtime: list[dict] = []
    dev: list[dict] = []

    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists():
        rt, dv = _parse_pyproject(pyproject)
        runtime.extend(rt)
        dev.extend(dv)

    for req in repo_path.glob("requirements*.txt"):
        if "lock" in req.name:
            continue
        is_dev = any(token in req.stem.lower() for token in ("dev", "test", "lint", "doc"))
        bucket = dev if is_dev else runtime
        bucket.extend(_parse_requirements_txt(req))

    package_json = repo_path / "package.json"
    if package_json.exists():
        rt, dv = _parse_package_json(package_json)
        runtime.extend(rt)
        dev.extend(dv)

    cargo_toml = repo_path / "Cargo.toml"
    if cargo_toml.exists():
        rt, dv = _parse_cargo_toml(cargo_toml)
        runtime.extend(rt)
        dev.extend(dv)

    go_mod = repo_path / "go.mod"
    if go_mod.exists():
        runtime.extend(_parse_go_mod(go_mod))

    lockfiles = _find_lockfiles(repo_path)

    return {
        "runtime": runtime,
        "dev": dev,
        "lockfiles": lockfiles,
        "total_packages": len(runtime) + len(dev),
    }


__all__ = [
    "extract_dependency_graph",
    "ECOSYSTEMS",
    "LOCKFILES",
]
