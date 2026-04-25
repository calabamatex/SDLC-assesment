from pathlib import Path

from sdlc_assessor.detectors.registry import DetectorRegistry
from sdlc_assessor.detectors.tsjs_pack import run_tsjs_detectors


def test_detectors_registry_lists_phase3_detectors() -> None:
    registry = DetectorRegistry()
    assert registry.registered() == ["common", "python_pack", "tsjs_pack"]


def test_detectors_find_probable_secret_fixture_signal() -> None:
    registry = DetectorRegistry()
    findings = registry.run("tests/fixtures/fixture_probable_secret")
    subcats = {f["subcategory"] for f in findings}
    assert "probable_secrets" in subcats


def test_detectors_emit_finding_shape_fields() -> None:
    registry = DetectorRegistry()
    findings = registry.run("tests/fixtures/fixture_probable_secret")
    required = {
        "category",
        "subcategory",
        "severity",
        "statement",
        "evidence",
        "confidence",
        "applicability",
        "score_impact",
        "detector_source",
    }
    assert findings
    assert required.issubset(findings[0].keys())


def test_tsjs_detector_noop_when_no_tsjs_files(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("hello", encoding="utf-8")
    assert run_tsjs_detectors(tmp_path) == []


def test_tsjs_detector_handles_invalid_tsconfig_json(tmp_path: Path) -> None:
    (tmp_path / "index.ts").write_text("const x = 1;", encoding="utf-8")
    (tmp_path / "tsconfig.json").write_text("{invalid", encoding="utf-8")
    subcats = {f["subcategory"] for f in run_tsjs_detectors(tmp_path)}
    assert "missing_strict_mode" in subcats


def test_tsjs_detector_parses_strict_with_nonstandard_whitespace(tmp_path: Path) -> None:
    (tmp_path / "index.ts").write_text("const x = 1;", encoding="utf-8")
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions":{"strict":true}}', encoding="utf-8"
    )
    subcats = {f["subcategory"] for f in run_tsjs_detectors(tmp_path)}
    assert "missing_strict_mode" not in subcats


# SDLC-019 / SDLC-020 / SDLC-021: false-positive and false-negative coverage.

def _python_subcats(repo: Path) -> set[str]:
    from sdlc_assessor.detectors.python_pack import run_python_detectors

    return {f["subcategory"] for f in run_python_detectors(repo)}


def test_python_print_in_comment_is_not_a_finding(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        "# print(x) inside a comment\nx = 1\n", encoding="utf-8"
    )
    assert "print_usage" not in _python_subcats(tmp_path)


def test_python_pprint_call_is_not_print_usage(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        "from pprint import pprint\npprint({'a': 1})\n", encoding="utf-8"
    )
    assert "print_usage" not in _python_subcats(tmp_path)


def test_python_print_emits_count_for_multiple_calls(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        "print(1)\nprint(2)\nprint(3)\n", encoding="utf-8"
    )
    from sdlc_assessor.detectors.python_pack import run_python_detectors

    findings = [f for f in run_python_detectors(tmp_path) if f["subcategory"] == "print_usage"]
    assert findings
    assert findings[0]["evidence"][0]["count"] == 3
    assert findings[0]["evidence"][0]["line_start"] == 1


def test_python_shell_true_inside_string_is_not_a_finding(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        'doc = "shell=True is dangerous"\n', encoding="utf-8"
    )
    assert "subprocess_shell_true" not in _python_subcats(tmp_path)


def test_python_bare_except_detected(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        "try:\n    pass\nexcept:\n    pass\n", encoding="utf-8"
    )
    subcats = _python_subcats(tmp_path)
    assert "bare_except" in subcats


def test_python_any_in_string_is_not_a_finding(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        'doc = "Many people use Anyone"\nx = 1\n', encoding="utf-8"
    )
    assert "any_usage" not in _python_subcats(tmp_path)


def test_tsjs_execa_is_not_exec_usage(tmp_path: Path) -> None:
    (tmp_path / "index.js").write_text(
        'import execa from "execa";\nexeca("ls");\n', encoding="utf-8"
    )
    subcats = {f["subcategory"] for f in run_tsjs_detectors(tmp_path)}
    assert "exec_usage" not in subcats


def test_tsjs_empty_catch_with_param_detected(tmp_path: Path) -> None:
    (tmp_path / "index.js").write_text(
        "try { f(); } catch (e) {}\n", encoding="utf-8"
    )
    subcats = {f["subcategory"] for f in run_tsjs_detectors(tmp_path)}
    assert "empty_catch" in subcats


def test_tsjs_strict_inherited_via_extends_is_respected(tmp_path: Path) -> None:
    (tmp_path / "tsconfig.base.json").write_text(
        '{"compilerOptions":{"strict":true}}', encoding="utf-8"
    )
    (tmp_path / "tsconfig.json").write_text(
        '{"extends":"./tsconfig.base.json"}', encoding="utf-8"
    )
    (tmp_path / "index.ts").write_text("const x = 1;\n", encoding="utf-8")
    subcats = {f["subcategory"] for f in run_tsjs_detectors(tmp_path)}
    assert "missing_strict_mode" not in subcats


def test_tsjs_jsonc_tsconfig_with_comments_parsed(tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text(
        '// comment\n{"compilerOptions":{"strict":true}, /*x*/}',
        encoding="utf-8",
    )
    (tmp_path / "index.ts").write_text("const x = 1;\n", encoding="utf-8")
    subcats = {f["subcategory"] for f in run_tsjs_detectors(tmp_path)}
    assert "missing_strict_mode" not in subcats


def test_common_secret_inside_node_modules_is_ignored(tmp_path: Path) -> None:
    from sdlc_assessor.detectors.common import run_common_detectors

    (tmp_path / "node_modules" / "leftpad").mkdir(parents=True)
    (tmp_path / "node_modules" / "leftpad" / "index.js").write_text(
        'const API_KEY = "actual-leak";\n', encoding="utf-8"
    )
    findings = run_common_detectors(tmp_path)
    secret_findings = [f for f in findings if f["subcategory"] == "probable_secrets"]
    assert secret_findings == []


def test_common_secret_with_line_number(tmp_path: Path) -> None:
    from sdlc_assessor.detectors.common import run_common_detectors

    (tmp_path / "config.py").write_text(
        '# header\nAPI_KEY = "abcdef-real-token-for-test"\n', encoding="utf-8"
    )
    findings = [f for f in run_common_detectors(tmp_path) if f["subcategory"] == "probable_secrets"]
    assert findings
    ev = findings[0]["evidence"][0]
    assert ev["line_start"] == 2
    assert ev["match_type"] == "pattern"


def test_common_security_md_under_dot_github_is_recognized(tmp_path: Path) -> None:
    from sdlc_assessor.detectors.common import run_common_detectors

    (tmp_path / "README.md").write_text("hi", encoding="utf-8")
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "SECURITY.md").write_text("disclosure", encoding="utf-8")
    subcats = {f["subcategory"] for f in run_common_detectors(tmp_path)}
    assert "missing_security_md" not in subcats


def test_common_skips_files_above_max_size(tmp_path: Path) -> None:
    from sdlc_assessor.detectors.common import DEFAULT_MAX_FILE_SIZE, run_common_detectors

    big = tmp_path / "blob.bin"
    big.write_bytes(b"\x00" * (DEFAULT_MAX_FILE_SIZE + 1))
    findings = run_common_detectors(tmp_path)
    secrets = [f for f in findings if f["subcategory"] == "probable_secrets"]
    assert secrets == []
    large = [f for f in findings if f["subcategory"] == "large_files"]
    assert large
    assert large[0]["evidence"][0]["path"].endswith("blob.bin")
