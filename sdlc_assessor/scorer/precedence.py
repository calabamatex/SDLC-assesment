"""Profile precedence merge logic for scoring."""

from __future__ import annotations

from copy import deepcopy

from sdlc_assessor.profiles.loader import (
    load_maturity_profiles,
    load_repo_type_profiles,
    load_use_case_profiles,
)
from sdlc_assessor.scorer.policy import apply_policy_overrides


def build_effective_profile(
    use_case: str,
    maturity: str,
    repo_type: str,
    policy_overrides: dict | None = None,
) -> dict:
    use_cases = load_use_case_profiles()
    maturities = load_maturity_profiles()
    repo_types = load_repo_type_profiles()

    effective = {
        "use_case": use_case,
        "maturity": maturity,
        "repo_type": repo_type,
        "use_case_profile": deepcopy(use_cases[use_case]),
        "maturity_profile": deepcopy(maturities[maturity]),
        "repo_type_profile": deepcopy(repo_types[repo_type]),
    }
    return apply_policy_overrides(effective, policy_overrides)
