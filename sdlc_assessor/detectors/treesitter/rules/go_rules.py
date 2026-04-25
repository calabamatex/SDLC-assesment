"""Go detector rules (SDLC-045).

Each rule is a tree-sitter S-expression query plus the schema metadata to
attach to the resulting finding. The framework runs all rules against every
``.go`` file in the assessed repo.
"""

from __future__ import annotations

from sdlc_assessor.detectors.treesitter.framework import TreeSitterRule

GO_SUFFIXES = (".go",)

GO_RULES: list[TreeSitterRule] = [
    TreeSitterRule(
        subcategory="go_panic_call",
        severity="high",
        category="code_quality_contracts",
        statement="`panic()` call detected — prefer returning an error.",
        rationale=(
            "panic terminates the goroutine; in library code it's a "
            "blunt instrument that callers can't catch idiomatically."
        ),
        query="""
            ((call_expression
                function: (identifier) @fn)
             (#eq? @fn "panic")) @match
        """,
    ),
    TreeSitterRule(
        subcategory="go_unsafe_pointer",
        severity="high",
        category="security_posture",
        statement="`unsafe.Pointer` usage detected.",
        rationale=(
            "`unsafe.Pointer` bypasses Go's memory-safety guarantees and "
            "is a common source of UB and CVEs."
        ),
        query="""
            ((selector_expression
                operand: (identifier) @pkg
                field: (field_identifier) @fld)
             (#eq? @pkg "unsafe")
             (#eq? @fld "Pointer")) @match
        """,
    ),
    TreeSitterRule(
        subcategory="go_exec_command_shell",
        severity="critical",
        category="security_posture",
        statement="`exec.Command(\"sh\", \"-c\", ...)` shell-out detected.",
        rationale=(
            "Routing user input through a shell is a command-injection "
            "vector; prefer `exec.Command(<bin>, <args>...)`."
        ),
        query="""
            ((call_expression
                function: (selector_expression
                    operand: (identifier) @pkg
                    field: (field_identifier) @fn)
                arguments: (argument_list (interpreted_string_literal) @first))
             (#eq? @pkg "exec")
             (#eq? @fn "Command")
             (#match? @first "^\\"(sh|bash|zsh|cmd|powershell)\\"$")) @match
        """,
    ),
    TreeSitterRule(
        subcategory="go_fmt_println",
        severity="low",
        category="code_quality_contracts",
        statement="`fmt.Println` in module code — prefer a structured logger.",
        rationale=(
            "Direct stdout writes bypass any logger config; adopt log/slog "
            "or zap for structured, leveled logging."
        ),
        query="""
            ((call_expression
                function: (selector_expression
                    operand: (identifier) @pkg
                    field: (field_identifier) @fn))
             (#eq? @pkg "fmt")
             (#match? @fn "^Print(ln|f)?$")) @match
        """,
    ),
    TreeSitterRule(
        subcategory="go_recover_without_repanic",
        severity="medium",
        category="code_quality_contracts",
        statement="`recover()` without subsequent re-panic — masks crashes.",
        rationale=(
            "Recovering from a panic and continuing silently obscures a "
            "real failure; either rethrow or log + degrade explicitly."
        ),
        query="""
            ((call_expression
                function: (identifier) @fn)
             (#eq? @fn "recover")) @match
        """,
    ),
    TreeSitterRule(
        subcategory="go_init_with_side_effects",
        severity="low",
        category="architecture_design",
        statement="`init()` function present — implicit module-load side effect.",
        rationale=(
            "init() runs at import time before tests or callers can "
            "intervene; explicit setup functions are easier to reason about."
        ),
        query="""
            ((function_declaration
                name: (identifier) @fn)
             (#eq? @fn "init")) @match
        """,
    ),
    TreeSitterRule(
        subcategory="go_todo_or_fixme",
        severity="info",
        category="documentation_truthfulness",
        statement="`TODO` or `FIXME` left in source.",
        rationale="Open work items should be tracked in an issue tracker, not embedded in code.",
        query="""
            ((comment) @c
             (#match? @c "(TODO|FIXME|XXX|HACK)")) @match
        """,
    ),
]


__all__ = ["GO_RULES", "GO_SUFFIXES"]
