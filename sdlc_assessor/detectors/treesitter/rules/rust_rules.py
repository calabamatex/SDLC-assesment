"""Rust detector rules (SDLC-046)."""

from __future__ import annotations

from sdlc_assessor.detectors.treesitter.framework import TreeSitterRule

RUST_SUFFIXES = (".rs",)

RUST_RULES: list[TreeSitterRule] = [
    TreeSitterRule(
        subcategory="rust_unsafe_block",
        severity="high",
        category="security_posture",
        statement="`unsafe` block detected — bypass of Rust's safety guarantees.",
        rationale=(
            "Each unsafe block invites memory-safety bugs and CVEs; "
            "every one needs a documented invariant explaining why "
            "the surrounding code is sound."
        ),
        query="""
            (unsafe_block) @match
        """,
    ),
    TreeSitterRule(
        subcategory="rust_unwrap_call",
        severity="medium",
        category="code_quality_contracts",
        statement="`.unwrap()` call detected — panics on `None`/`Err`.",
        rationale=(
            "`.unwrap()` converts a recoverable error path into a process "
            "abort. Prefer `?`, `.expect(\"...\")` with rationale, or "
            "explicit error propagation."
        ),
        query="""
            ((call_expression
                function: (field_expression
                    field: (field_identifier) @fn))
             (#eq? @fn "unwrap")) @match
        """,
    ),
    TreeSitterRule(
        subcategory="rust_expect_call",
        severity="low",
        category="code_quality_contracts",
        statement="`.expect()` call detected — panics on `None`/`Err`.",
        rationale=(
            "`.expect()` at least documents the failure mode, but still "
            "panics. Acceptable in main()/binary entry; suspect in libraries."
        ),
        query="""
            ((call_expression
                function: (field_expression
                    field: (field_identifier) @fn))
             (#eq? @fn "expect")) @match
        """,
    ),
    TreeSitterRule(
        subcategory="rust_panic_macro",
        severity="high",
        category="code_quality_contracts",
        statement="`panic!()` macro detected.",
        rationale=(
            "panic!() aborts the thread; library code should return "
            "a `Result` instead and let callers decide."
        ),
        query="""
            ((macro_invocation
                macro: (identifier) @m)
             (#eq? @m "panic")) @match
        """,
    ),
    TreeSitterRule(
        subcategory="rust_dbg_macro",
        severity="low",
        category="code_quality_contracts",
        statement="`dbg!()` macro left in source.",
        rationale=(
            "`dbg!()` is intended for temporary inspection during "
            "development; shipping it pollutes stderr in production."
        ),
        query="""
            ((macro_invocation
                macro: (identifier) @m)
             (#eq? @m "dbg")) @match
        """,
    ),
    TreeSitterRule(
        subcategory="rust_println_macro",
        severity="info",
        category="code_quality_contracts",
        statement="`println!`/`eprintln!` macro in source — adopt structured logging.",
        rationale=(
            "Direct stdout/stderr writes bypass any logger config; "
            "adopt `tracing` or `log` for structured output."
        ),
        query="""
            ((macro_invocation
                macro: (identifier) @m)
             (#match? @m "^(println|eprintln|print|eprint)$")) @match
        """,
    ),
    TreeSitterRule(
        subcategory="rust_transmute_call",
        severity="critical",
        category="security_posture",
        statement="`mem::transmute` call detected — reinterpret-cast bypass.",
        rationale=(
            "transmute reinterprets memory layout without checks; one of "
            "the most dangerous operations in Rust. Almost always wrong."
        ),
        # Two forms: `mem::transmute(x)` (scoped_identifier) and
        # `mem::transmute::<A,B>(x)` (generic_function wrapping scoped_identifier).
        query="""
            (call_expression
                function: [
                    (scoped_identifier
                        name: (identifier) @fn)
                    (generic_function
                        function: (scoped_identifier
                            name: (identifier) @fn))
                ]
                (#eq? @fn "transmute")) @match
        """,
    ),
]


__all__ = ["RUST_RULES", "RUST_SUFFIXES"]
