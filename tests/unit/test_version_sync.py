"""Assert sdlc_assessor.__version__ matches pyproject.toml [project].version (SDLC-035)."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import sdlc_assessor

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def test_pyproject_version_matches_package_version() -> None:
    with PYPROJECT.open("rb") as fh:
        data = tomllib.load(fh)
    pyproject_version = data["project"]["version"]
    assert sdlc_assessor.__version__ == pyproject_version, (
        f"Version drift: sdlc_assessor.__version__={sdlc_assessor.__version__!r} but "
        f"pyproject.toml [project].version={pyproject_version!r}. Update both in the same commit."
    )


def test_version_is_pep440() -> None:
    parts = sdlc_assessor.__version__.split(".")
    assert len(parts) >= 3
    for part in parts[:3]:
        assert part.split("+")[0].split("-")[0].isdigit(), (
            f"Non-numeric component in version: {sdlc_assessor.__version__}"
        )


def test_python_version_is_3_12_or_newer() -> None:
    """Detects accidentally-installed environments running on too-old a Python."""
    assert sys.version_info >= (3, 12), (
        f"sdlc-assessor declares requires-python>=3.12 but is running on {sys.version}"
    )
