"""Profile loader for use-case, maturity, and repo-type profiles."""

from __future__ import annotations

from pathlib import Path

from sdlc_assessor.core.io import read_json


DATA_DIR = Path(__file__).resolve().parent / "data"


def load_use_case_profiles() -> dict:
    return read_json(DATA_DIR / "use_case_profiles.json")


def load_maturity_profiles() -> dict:
    return read_json(DATA_DIR / "maturity_profiles.json")


def load_repo_type_profiles() -> dict:
    return read_json(DATA_DIR / "repo_type_profiles.json")
