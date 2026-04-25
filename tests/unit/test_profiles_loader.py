from pathlib import Path

from sdlc_assessor.profiles.loader import (
    load_maturity_profiles,
    load_repo_type_profiles,
    load_use_case_profiles,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_profiles_loader_reads_use_case_profiles() -> None:
    profiles = load_use_case_profiles()
    assert "engineering_triage" in profiles


def test_profiles_loader_reads_maturity_profiles() -> None:
    profiles = load_maturity_profiles()
    assert "production" in profiles


def test_profiles_loader_reads_repo_type_profiles() -> None:
    profiles = load_repo_type_profiles()
    assert "service" in profiles
    assert "unknown" in profiles, "unknown archetype must have a profile entry (SDLC-016)"


def test_no_duplicate_profile_jsons() -> None:
    """SDLC-018: profile JSONs must live only at sdlc_assessor/profiles/data/."""
    for name in ("use_case_profiles.json", "maturity_profiles.json", "repo_type_profiles.json"):
        docs_path = REPO_ROOT / "docs" / name
        assert not docs_path.exists(), (
            f"Duplicate profile JSON at docs/{name}; canonical location is "
            f"sdlc_assessor/profiles/data/"
        )
        package_path = REPO_ROOT / "sdlc_assessor" / "profiles" / "data" / name
        assert package_path.exists(), f"Missing canonical profile JSON: {package_path}"
