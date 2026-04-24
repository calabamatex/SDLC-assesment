from sdlc_assessor.profiles.loader import (
    load_maturity_profiles,
    load_repo_type_profiles,
    load_use_case_profiles,
)


def test_profiles_loader_reads_use_case_profiles() -> None:
    profiles = load_use_case_profiles()
    assert "engineering_triage" in profiles


def test_profiles_loader_reads_maturity_profiles() -> None:
    profiles = load_maturity_profiles()
    assert "production" in profiles


def test_profiles_loader_reads_repo_type_profiles() -> None:
    profiles = load_repo_type_profiles()
    assert "service" in profiles
