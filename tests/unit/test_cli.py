"""CLI integration tests covering SDLC-017 default-profile resolution."""

from __future__ import annotations

from pathlib import Path

from sdlc_assessor.cli import _resolve_profile_defaults, main


def test_resolve_profile_defaults_uses_classifier_when_omitted(capfd) -> None:
    classification = {"maturity_profile": "prototype", "repo_archetype": "cli"}
    maturity, repo_type = _resolve_profile_defaults(
        classification, maturity=None, repo_type=None
    )
    assert maturity == "prototype"
    assert repo_type == "cli"
    err = capfd.readouterr().err
    assert "from classifier" in err


def test_resolve_profile_defaults_respects_explicit_args(capfd) -> None:
    classification = {"maturity_profile": "prototype", "repo_archetype": "cli"}
    maturity, repo_type = _resolve_profile_defaults(
        classification, maturity="production", repo_type="service"
    )
    assert maturity == "production"
    assert repo_type == "service"
    err = capfd.readouterr().err
    assert "from classifier" not in err


def test_resolve_profile_defaults_falls_back_when_unknown() -> None:
    classification = {"maturity_profile": "unknown", "repo_archetype": "unknown"}
    maturity, repo_type = _resolve_profile_defaults(
        classification, maturity=None, repo_type=None, log=False
    )
    assert maturity == "prototype"
    assert repo_type == "internal_tool"


def test_run_subcommand_works_without_explicit_profile_args(tmp_path: Path) -> None:
    rc = main(
        [
            "run",
            "tests/fixtures/fixture_python_basic",
            "--use-case",
            "engineering_triage",
            "--out-dir",
            str(tmp_path),
        ]
    )
    assert rc == 0
    for name in ("classification.json", "evidence.json", "scored.json", "report.md", "remediation.md"):
        assert (tmp_path / name).exists(), f"missing artifact {name}"
