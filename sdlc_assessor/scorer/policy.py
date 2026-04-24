"""Phase 8 policy override support."""

from __future__ import annotations

from copy import deepcopy


def apply_policy_overrides(effective_profile: dict, policy: dict | None) -> dict:
    merged = deepcopy(effective_profile)
    if not policy:
        return merged

    for key in ("use_case_profile", "maturity_profile", "repo_type_profile"):
        overrides = policy.get(key, {})
        if isinstance(overrides, dict):
            base = merged.get(key, {})
            if isinstance(base, dict):
                base.update(overrides)
                merged[key] = base
    return merged
