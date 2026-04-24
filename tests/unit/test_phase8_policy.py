from sdlc_assessor.scorer.engine import score_evidence


def test_phase8_policy_override_changes_threshold_behavior() -> None:
    evidence = {
        "repo_meta": {},
        "classification": {},
        "inventory": {},
        "findings": [],
        "scoring": {},
        "hard_blockers": [],
    }

    baseline = score_evidence(evidence, "engineering_triage", "prototype", "cli")
    overridden = score_evidence(
        evidence,
        "engineering_triage",
        "prototype",
        "cli",
        policy_overrides={"use_case_profile": {"distinction_threshold": 101}},
    )

    assert baseline["scoring"]["overall_score"] == overridden["scoring"]["overall_score"]
    assert overridden["scoring"]["effective_profile"]["policy_overrides_applied"] is True
