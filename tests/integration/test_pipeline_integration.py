from __future__ import annotations

import json
import subprocess
from pathlib import Path


FIXTURES = [
    "fixture_empty_repo",
    "fixture_python_basic",
    "fixture_typescript_basic",
    "fixture_no_ci",
    "fixture_probable_secret",
    "fixture_research_repo",
]


def _run(cmd: list[str], cwd: str = ".") -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def _assert_artifacts(out_dir: Path) -> None:
    expected = [
        "classification.json",
        "evidence.json",
        "scored.json",
        "report.md",
        "remediation.md",
    ]
    for name in expected:
        assert (out_dir / name).exists(), f"Missing artifact: {name}"


def test_full_pipeline_runs_on_all_fixtures() -> None:
    for fixture in FIXTURES:
        out_dir = Path(".sdlc") / f"integration_{fixture}"
        _run(
            [
                "python",
                "-m",
                "sdlc_assessor.cli",
                "run",
                f"tests/fixtures/{fixture}",
                "--use-case",
                "engineering_triage",
                "--maturity",
                "prototype",
                "--repo-type",
                "cli",
                "--out-dir",
                str(out_dir),
            ]
        )
        _assert_artifacts(out_dir)


def test_full_pipeline_runs_on_current_repo() -> None:
    out_dir = Path(".sdlc") / "integration_self"
    _run(
        [
            "python",
            "-m",
            "sdlc_assessor.cli",
            "run",
            ".",
            "--use-case",
            "engineering_triage",
            "--maturity",
            "prototype",
            "--repo-type",
            "cli",
            "--out-dir",
            str(out_dir),
        ]
    )
    _assert_artifacts(out_dir)


def test_install_and_console_script_help() -> None:
    _run(["python", "-m", "pip", "install", "-e", ".", "--no-build-isolation"])
    completed = subprocess.run(["sdlc", "--help"], check=True, capture_output=True, text=True)
    assert "SDLC assessor CLI" in completed.stdout


def test_scored_json_is_schema_shaped() -> None:
    scored_path = Path(".sdlc") / "integration_fixture_python_basic" / "scored.json"
    if scored_path.exists():
        data = json.loads(scored_path.read_text(encoding="utf-8"))
        assert "scoring" in data and "overall_score" in data["scoring"]
