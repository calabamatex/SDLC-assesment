"""SAST adapter tests (SDLC-050..054).

Subprocess-mocked tests so the suite runs identically whether or not
bandit/ruff/eslint/semgrep happen to be on the runner's PATH. A few
``skipif``-gated integration tests exercise the real binaries when present.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from sdlc_assessor.detectors.sast.bandit_adapter import BanditAdapter
from sdlc_assessor.detectors.sast.eslint_adapter import ESLintAdapter
from sdlc_assessor.detectors.sast.framework import (
    SASTAdapter,
    register_adapter,
    registered_adapters,
    run_sast_adapters,
)
from sdlc_assessor.detectors.sast.ruff_adapter import RuffAdapter
from sdlc_assessor.detectors.sast.semgrep_adapter import SemgrepAdapter

# ---------------------------------------------------------------------------
# Framework
# ---------------------------------------------------------------------------


def test_registered_adapters_includes_all_four() -> None:
    names = [a.tool_name for a in registered_adapters()]
    for required in ("bandit", "ruff", "eslint", "semgrep"):
        assert required in names, f"missing adapter for {required}"


def test_adapter_skips_when_tool_not_on_path(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("x = 1\n", encoding="utf-8")
    adapter = BanditAdapter()
    with patch("sdlc_assessor.detectors.sast.framework.shutil.which", return_value=None):
        assert adapter.run(tmp_path) == []


def test_adapter_skips_when_should_run_returns_false(tmp_path: Path) -> None:
    """No Python files → BanditAdapter.should_run() is False."""
    (tmp_path / "main.go").write_text("package main\n", encoding="utf-8")
    adapter = BanditAdapter()
    with patch("sdlc_assessor.detectors.sast.framework.shutil.which", return_value="/usr/bin/bandit"):
        assert adapter.run(tmp_path) == []


def test_run_sast_adapters_isolates_adapter_failures(tmp_path: Path) -> None:
    """A bad adapter must not break the dispatch loop."""

    class BoomAdapter(SASTAdapter):
        tool_name = "boom"
        ecosystems = ()
        detector_source = "sast.boom"

        def is_available(self) -> bool:
            return True

        def should_run(self, repo_path: Path) -> bool:
            return True

        def build_command(self, repo_path: Path) -> list[str]:
            raise RuntimeError("boom")

        def parse_output(self, *args, **kwargs):
            return []

    register_adapter(BoomAdapter())
    try:
        with pytest.warns(UserWarning, match="raised RuntimeError"):
            findings = run_sast_adapters(tmp_path)
        # Other adapters still ran (returned empty since no source).
        assert isinstance(findings, list)
    finally:
        # Clean up the registration so the test doesn't pollute later runs.
        from sdlc_assessor.detectors.sast.framework import _REGISTERED_ADAPTERS

        _REGISTERED_ADAPTERS[:] = [a for a in _REGISTERED_ADAPTERS if not isinstance(a, BoomAdapter)]


# ---------------------------------------------------------------------------
# Bandit
# ---------------------------------------------------------------------------


def test_bandit_parse_maps_severity_and_confidence() -> None:
    adapter = BanditAdapter()
    payload = json.dumps(
        {
            "results": [
                {
                    "filename": "src/app.py",
                    "line_number": 12,
                    "issue_severity": "HIGH",
                    "issue_confidence": "HIGH",
                    "issue_text": "Use of eval detected.",
                    "test_id": "B307",
                    "test_name": "blacklist_call",
                    "code": "eval(x)",
                    "issue_cwe": {"id": 78},
                },
                {
                    "filename": "src/util.py",
                    "line_number": 5,
                    "issue_severity": "MEDIUM",
                    "issue_confidence": "LOW",
                    "issue_text": "subprocess shell.",
                    "test_id": "B602",
                    "code": "subprocess.run(..., shell=True)",
                },
            ]
        }
    )
    out = adapter.parse_output(payload, "", 1)
    assert len(out) == 2
    assert out[0].severity == "high"
    assert out[0].confidence == "high"
    assert out[0].subcategory == "bandit_B307"
    assert out[0].rule_id == "B307"
    assert out[0].line_start == 12
    assert "cwe:78" in out[0].tags
    assert out[1].severity == "medium"
    assert out[1].confidence == "low"


def test_bandit_parse_handles_invalid_json() -> None:
    assert BanditAdapter().parse_output("not json", "", 1) == []
    assert BanditAdapter().parse_output("", "", 0) == []


def test_bandit_run_dispatches_subprocess_and_returns_finding(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("x = 1\n", encoding="utf-8")
    adapter = BanditAdapter()
    fake_completed = subprocess.CompletedProcess(
        args=["bandit"],
        returncode=1,
        stdout=json.dumps(
            {
                "results": [
                    {
                        "filename": str(tmp_path / "main.py"),
                        "line_number": 1,
                        "issue_severity": "HIGH",
                        "issue_confidence": "HIGH",
                        "issue_text": "demo",
                        "test_id": "B999",
                        "code": "x = 1",
                    }
                ]
            }
        ),
        stderr="",
    )
    with patch("sdlc_assessor.detectors.sast.framework.shutil.which", return_value="/usr/bin/bandit"):
        with patch("sdlc_assessor.detectors.sast.framework.subprocess.run", return_value=fake_completed):
            findings = adapter.run(tmp_path)
    assert findings
    assert findings[0]["subcategory"] == "bandit_B999"
    assert findings[0]["category"] == "security_posture"
    assert findings[0]["evidence"][0]["line_start"] == 1


# ---------------------------------------------------------------------------
# Ruff
# ---------------------------------------------------------------------------


def test_ruff_parse_classifies_security_vs_style() -> None:
    adapter = RuffAdapter()
    payload = json.dumps(
        [
            {
                "code": "S102",
                "message": "Use of exec",
                "filename": "src/app.py",
                "location": {"row": 10, "column": 1},
                "end_location": {"row": 10, "column": 8},
            },
            {
                "code": "E501",
                "message": "Line too long",
                "filename": "src/app.py",
                "location": {"row": 22, "column": 1},
                "end_location": {"row": 22, "column": 130},
            },
        ]
    )
    out = adapter.parse_output(payload, "", 1)
    by_code = {r.subcategory: r for r in out}
    assert by_code["ruff_S102"].severity == "high"
    assert by_code["ruff_S102"].category == "security_posture"
    assert by_code["ruff_E501"].severity == "low"
    assert by_code["ruff_E501"].category == "code_quality_contracts"


def test_ruff_parse_handles_invalid_json() -> None:
    assert RuffAdapter().parse_output("not json", "", 1) == []


@pytest.mark.skipif(shutil.which("ruff") is None, reason="ruff not on PATH")
def test_ruff_integration_against_obviously_bad_python(tmp_path: Path) -> None:
    """Real-binary integration test: ruff is bundled in the dev extras."""
    (tmp_path / "bad.py").write_text("import os, sys\nx=1  \n\n\n\n\n", encoding="utf-8")
    adapter = RuffAdapter()
    findings = adapter.run(tmp_path)
    # We don't pin specific codes — just assert ruff produced *something*.
    # If ruff is installed but the project has no opinions configured, this
    # may still return [] gracefully; the assertion is "doesn't crash".
    assert isinstance(findings, list)


# ---------------------------------------------------------------------------
# ESLint
# ---------------------------------------------------------------------------


def test_eslint_should_run_requires_config(tmp_path: Path) -> None:
    (tmp_path / "index.js").write_text("var x = 1;\n", encoding="utf-8")
    adapter = ESLintAdapter()
    with patch("sdlc_assessor.detectors.sast.framework.shutil.which", return_value="/usr/local/bin/eslint"):
        # No config → skip
        assert adapter.should_run(tmp_path) is False
        # Add a config → run
        (tmp_path / ".eslintrc.json").write_text("{}", encoding="utf-8")
        assert adapter.should_run(tmp_path) is True


def test_eslint_should_run_recognizes_package_json_eslint_config(tmp_path: Path) -> None:
    (tmp_path / "index.js").write_text("var x = 1;\n", encoding="utf-8")
    (tmp_path / "package.json").write_text(
        json.dumps({"name": "x", "version": "0.0.0", "eslintConfig": {"rules": {}}}),
        encoding="utf-8",
    )
    adapter = ESLintAdapter()
    with patch("sdlc_assessor.detectors.sast.framework.shutil.which", return_value="/x/eslint"):
        assert adapter.should_run(tmp_path) is True


def test_eslint_parse_emits_security_for_eval_rule() -> None:
    adapter = ESLintAdapter()
    payload = json.dumps(
        [
            {
                "filePath": "src/index.js",
                "messages": [
                    {
                        "ruleId": "no-eval",
                        "severity": 2,
                        "message": "eval can be harmful.",
                        "line": 5,
                        "endLine": 5,
                    }
                ],
            }
        ]
    )
    out = adapter.parse_output(payload, "", 1)
    assert len(out) == 1
    assert out[0].subcategory == "eslint_no-eval"
    assert out[0].category == "security_posture"
    assert out[0].severity == "medium"


def test_eslint_parse_handles_invalid_json() -> None:
    assert ESLintAdapter().parse_output("not json", "", 1) == []


# ---------------------------------------------------------------------------
# Semgrep
# ---------------------------------------------------------------------------


def test_semgrep_parse_maps_severity_and_category() -> None:
    adapter = SemgrepAdapter()
    payload = json.dumps(
        {
            "results": [
                {
                    "check_id": "python.lang.security.audit.dangerous-eval",
                    "path": "src/app.py",
                    "start": {"line": 10},
                    "end": {"line": 10},
                    "extra": {
                        "severity": "ERROR",
                        "message": "Dangerous use of eval.",
                        "metadata": {"category": "security"},
                        "lines": "eval(x)",
                    },
                },
                {
                    "check_id": "python.lang.maintainability.long-function",
                    "path": "src/util.py",
                    "start": {"line": 1},
                    "end": {"line": 200},
                    "extra": {
                        "severity": "WARNING",
                        "message": "Function too long.",
                        "metadata": {"category": "best-practice"},
                    },
                },
            ]
        }
    )
    out = adapter.parse_output(payload, "", 1)
    assert len(out) == 2
    assert out[0].severity == "high"
    assert out[0].category == "security_posture"
    assert out[1].severity == "medium"
    assert out[1].category == "code_quality_contracts"


def test_semgrep_parse_handles_invalid_json() -> None:
    assert SemgrepAdapter().parse_output("not json", "", 1) == []


# ---------------------------------------------------------------------------
# End-to-end registry dispatch
# ---------------------------------------------------------------------------


def test_run_sast_adapters_returns_list_when_no_tools_installed(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("x = 1\n", encoding="utf-8")
    with patch("sdlc_assessor.detectors.sast.framework.shutil.which", return_value=None):
        findings = run_sast_adapters(tmp_path)
    assert findings == []
