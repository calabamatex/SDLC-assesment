from pathlib import Path

import pytest

from sdlc_assessor.detectors.registry import DetectorRegistry
from sdlc_assessor.detectors.tsjs_pack import run_tsjs_detectors

_TS_DEPS_OK = True
try:
    import tree_sitter  # noqa: F401
    import tree_sitter_language_pack  # noqa: F401
except ImportError:
    _TS_DEPS_OK = False


def test_detectors_registry_lists_registered_detectors() -> None:
    registry = DetectorRegistry()
    assert registry.registered() == [
        "common",
        "python_pack",
        "tsjs_pack",
        "go_pack",
        "rust_pack",
        "dependency_hygiene",
        "git_history",
        "sast",
    ]


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


# SDLC-048: Python pack expansion (6 new subcategories).


def _python_subcats_in(tmp_path: Path) -> set[str]:
    from sdlc_assessor.detectors.python_pack import run_python_detectors

    return {f["subcategory"] for f in run_python_detectors(tmp_path)}


def test_python_eval_or_exec_finding(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        "x = eval('1+1')\nexec('y = 2')\n", encoding="utf-8"
    )
    assert "eval_or_exec" in _python_subcats_in(tmp_path)


def test_python_eval_in_string_is_not_a_finding(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        'doc = "use eval() carefully"\n', encoding="utf-8"
    )
    assert "eval_or_exec" not in _python_subcats_in(tmp_path)


def test_python_pickle_loads_finding(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        "import pickle\npickle.loads(b'')\n", encoding="utf-8"
    )
    assert "pickle_load_untrusted" in _python_subcats_in(tmp_path)


def test_python_os_system_finding(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        "import os\nos.system('ls')\n", encoding="utf-8"
    )
    assert "os_system_call" in _python_subcats_in(tmp_path)


def test_python_requests_verify_false_finding(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        "import requests\nrequests.get('https://x', verify=False)\n",
        encoding="utf-8",
    )
    assert "requests_verify_false" in _python_subcats_in(tmp_path)


def test_python_mutable_default_finding(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        "def f(items=[]):\n    items.append(1)\n    return items\n",
        encoding="utf-8",
    )
    assert "mutable_default_argument" in _python_subcats_in(tmp_path)


def test_python_immutable_default_is_not_a_finding(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        "def f(items=None):\n    return items or []\n", encoding="utf-8"
    )
    assert "mutable_default_argument" not in _python_subcats_in(tmp_path)


def test_python_unsafe_sql_finding(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        "def q(c, n):\n    c.execute('SELECT * WHERE n=' + n)\n",
        encoding="utf-8",
    )
    assert "unsafe_sql_string" in _python_subcats_in(tmp_path)


def test_python_parametrized_sql_is_not_a_finding(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        "def q(c, n):\n    c.execute('SELECT * WHERE n=?', (n,))\n",
        encoding="utf-8",
    )
    assert "unsafe_sql_string" not in _python_subcats_in(tmp_path)


def test_python_module_level_assert_finding(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        "X = 1\nassert X == 1\n", encoding="utf-8"
    )
    assert "module_level_assert" in _python_subcats_in(tmp_path)


def test_python_assert_in_test_file_is_not_a_finding(tmp_path: Path) -> None:
    (tmp_path / "test_something.py").write_text(
        "X = 1\nassert X == 1\n", encoding="utf-8"
    )
    assert "module_level_assert" not in _python_subcats_in(tmp_path)


# SDLC-044/045/046/047: tree-sitter framework + Go + Rust + TS/JS migration.


@pytest.mark.skipif(not _TS_DEPS_OK, reason="tree-sitter not installed")
def test_go_pack_detects_panic(tmp_path: Path) -> None:
    from sdlc_assessor.detectors.treesitter.go_pack import run_go_detectors

    (tmp_path / "main.go").write_text(
        'package main\nfunc f() { panic("x") }\n', encoding="utf-8"
    )
    findings = run_go_detectors(tmp_path)
    assert "go_panic_call" in {f["subcategory"] for f in findings}


@pytest.mark.skipif(not _TS_DEPS_OK, reason="tree-sitter not installed")
def test_go_pack_detects_unsafe_pointer(tmp_path: Path) -> None:
    from sdlc_assessor.detectors.treesitter.go_pack import run_go_detectors

    (tmp_path / "main.go").write_text(
        'package main\nimport "unsafe"\nvar x int\nvar p = unsafe.Pointer(&x)\n',
        encoding="utf-8",
    )
    assert "go_unsafe_pointer" in {f["subcategory"] for f in run_go_detectors(tmp_path)}


@pytest.mark.skipif(not _TS_DEPS_OK, reason="tree-sitter not installed")
def test_go_pack_detects_exec_command_shell(tmp_path: Path) -> None:
    from sdlc_assessor.detectors.treesitter.go_pack import run_go_detectors

    (tmp_path / "main.go").write_text(
        'package main\nimport "os/exec"\nfunc f() { exec.Command("sh", "-c", "ls") }\n',
        encoding="utf-8",
    )
    assert "go_exec_command_shell" in {f["subcategory"] for f in run_go_detectors(tmp_path)}


@pytest.mark.skipif(not _TS_DEPS_OK, reason="tree-sitter not installed")
def test_go_pack_no_findings_on_clean_file(tmp_path: Path) -> None:
    from sdlc_assessor.detectors.treesitter.go_pack import run_go_detectors

    (tmp_path / "main.go").write_text(
        "package main\nfunc Add(a, b int) int { return a + b }\n", encoding="utf-8"
    )
    assert run_go_detectors(tmp_path) == []


@pytest.mark.skipif(not _TS_DEPS_OK, reason="tree-sitter not installed")
def test_rust_pack_detects_unsafe_block(tmp_path: Path) -> None:
    from sdlc_assessor.detectors.treesitter.rust_pack import run_rust_detectors

    (tmp_path / "lib.rs").write_text(
        "fn f() { unsafe { let _ = 1; } }\n", encoding="utf-8"
    )
    assert "rust_unsafe_block" in {f["subcategory"] for f in run_rust_detectors(tmp_path)}


@pytest.mark.skipif(not _TS_DEPS_OK, reason="tree-sitter not installed")
def test_rust_pack_detects_unwrap_and_expect(tmp_path: Path) -> None:
    from sdlc_assessor.detectors.treesitter.rust_pack import run_rust_detectors

    (tmp_path / "lib.rs").write_text(
        "fn f(x: Option<i32>) -> i32 { x.unwrap() }\n"
        "fn g(x: Option<i32>) -> i32 { x.expect(\"ok\") }\n",
        encoding="utf-8",
    )
    subcats = {f["subcategory"] for f in run_rust_detectors(tmp_path)}
    assert "rust_unwrap_call" in subcats
    assert "rust_expect_call" in subcats


@pytest.mark.skipif(not _TS_DEPS_OK, reason="tree-sitter not installed")
def test_rust_pack_detects_transmute(tmp_path: Path) -> None:
    from sdlc_assessor.detectors.treesitter.rust_pack import run_rust_detectors

    (tmp_path / "lib.rs").write_text(
        "fn f() { let _: u32 = unsafe { std::mem::transmute::<f32, u32>(1.0) }; }\n",
        encoding="utf-8",
    )
    assert "rust_transmute_call" in {f["subcategory"] for f in run_rust_detectors(tmp_path)}


@pytest.mark.skipif(not _TS_DEPS_OK, reason="tree-sitter not installed")
def test_tsjs_treesitter_detects_eval_and_function_constructor(tmp_path: Path) -> None:
    from sdlc_assessor.detectors.treesitter.tsjs_pack import run_tsjs_detectors

    (tmp_path / "x.js").write_text(
        "eval('1');\nconst fn = new Function('return 1');\n", encoding="utf-8"
    )
    subcats = {f["subcategory"] for f in run_tsjs_detectors(tmp_path)}
    assert "eval_usage" in subcats
    assert "function_constructor" in subcats


@pytest.mark.skipif(not _TS_DEPS_OK, reason="tree-sitter not installed")
def test_tsjs_treesitter_detects_inner_html(tmp_path: Path) -> None:
    from sdlc_assessor.detectors.treesitter.tsjs_pack import run_tsjs_detectors

    (tmp_path / "x.js").write_text("document.body.innerHTML = userInput;\n", encoding="utf-8")
    assert "inner_html_assignment" in {f["subcategory"] for f in run_tsjs_detectors(tmp_path)}


@pytest.mark.skipif(not _TS_DEPS_OK, reason="tree-sitter not installed")
def test_tsjs_treesitter_detects_dangerously_set_inner_html(tmp_path: Path) -> None:
    from sdlc_assessor.detectors.treesitter.tsjs_pack import run_tsjs_detectors

    (tmp_path / "App.tsx").write_text(
        'function A() { return <div dangerouslySetInnerHTML={{__html: ""}} />; }\n',
        encoding="utf-8",
    )
    assert "dangerously_set_inner_html" in {f["subcategory"] for f in run_tsjs_detectors(tmp_path)}


@pytest.mark.skipif(not _TS_DEPS_OK, reason="tree-sitter not installed")
def test_tsjs_treesitter_preserves_v0_2_signals(tmp_path: Path) -> None:
    """SDLC-047: existing as-any / console / empty-catch / exec / execSync still fire."""
    from sdlc_assessor.detectors.treesitter.tsjs_pack import run_tsjs_detectors

    (tmp_path / "x.ts").write_text(
        "const v: any = (1 as any);\nconsole.log(v);\ntry { } catch {}\nexec('x');\nexecSync('y');\n",
        encoding="utf-8",
    )
    subcats = {f["subcategory"] for f in run_tsjs_detectors(tmp_path)}
    for required in ("as_any", "console_usage", "empty_catch", "exec_usage", "exec_sync_usage"):
        assert required in subcats, f"missing {required}"


def test_treesitter_framework_no_op_when_deps_missing(monkeypatch, tmp_path: Path) -> None:
    """Framework must not crash when tree-sitter isn't installed."""
    import sdlc_assessor.detectors.treesitter.framework as fw

    monkeypatch.setattr(fw, "_DEPS_AVAILABLE", False)
    (tmp_path / "main.go").write_text("package main\n", encoding="utf-8")
    findings = fw.run_treesitter_pack(
        tmp_path,
        language="go",
        suffixes=(".go",),
        rules=[],
        detector_source="x",
    )
    assert findings == []
