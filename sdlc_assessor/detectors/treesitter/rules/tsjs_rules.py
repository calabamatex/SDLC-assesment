"""TypeScript / JavaScript detector rules (SDLC-047).

Replaces the v0.2.0 regex-based ``tsjs_pack`` with real AST queries via
tree-sitter. Same set of patterns as before plus four new ones the regex
approach couldn't reliably catch:

- ``dangerouslySetInnerHTML`` (React XSS surface)
- ``innerHTML =`` assignments (DOM XSS surface)
- ``eval()`` calls
- ``Function()`` constructor used to compile strings into functions

The rules are split per language because tree-sitter grammars differ
slightly between ``typescript``, ``tsx``, and ``javascript``. Calling code
runs the appropriate set per file extension.
"""

from __future__ import annotations

from typing import Any

from sdlc_assessor.detectors.treesitter.framework import TreeSitterRule


def _is_empty_block(node: Any) -> bool:
    """A ``statement_block`` node with no statements (named children)."""
    return getattr(node, "named_child_count", 0) == 0

JS_SUFFIXES = (".js", ".jsx", ".mjs", ".cjs")
TS_SUFFIXES = (".ts",)
TSX_SUFFIXES = (".tsx",)


# Shared rule definitions (queries portable across TS/JS/TSX grammars).
def _shared_rules(*, allow_jsx: bool) -> list[TreeSitterRule]:
    rules: list[TreeSitterRule] = [
        TreeSitterRule(
            subcategory="empty_catch",
            severity="medium",
            category="code_quality_contracts",
            statement="Empty `catch` block detected — error swallowed.",
            rationale="An empty catch block silently absorbs failures; rethrow or log + degrade explicitly.",
            # The regex predicate `#match?` behaves inconsistently across
            # grammar versions for whitespace-only bodies; use a Python
            # post-filter instead, which directly inspects the AST node.
            query="""
                (catch_clause
                    body: (statement_block) @match)
            """,
            post_filter=_is_empty_block,
        ),
        TreeSitterRule(
            subcategory="console_usage",
            severity="low",
            category="code_quality_contracts",
            statement="`console.*` call detected — adopt a structured logger.",
            rationale="Direct console calls bypass any logger config and pollute production output.",
            query="""
                ((call_expression
                    function: (member_expression
                        object: (identifier) @obj
                        property: (property_identifier) @method))
                 (#eq? @obj "console")
                 (#match? @method "^(log|warn|error|info|debug|trace)$")) @match
            """,
        ),
        TreeSitterRule(
            subcategory="json_parse",
            severity="info",
            category="code_quality_contracts",
            statement="`JSON.parse` call (informational; check for unguarded usage).",
            rationale="Unchecked JSON.parse on untrusted input throws SyntaxError. Wrap with try/catch or validate first.",
            query="""
                ((call_expression
                    function: (member_expression
                        object: (identifier) @obj
                        property: (property_identifier) @method))
                 (#eq? @obj "JSON")
                 (#eq? @method "parse")) @match
            """,
        ),
        TreeSitterRule(
            subcategory="exec_usage",
            severity="high",
            category="security_posture",
            statement="`exec(` call detected — command-injection risk.",
            rationale="exec() invokes a shell with the given command; user-controlled input is a direct injection vector.",
            query="""
                ((call_expression
                    function: (identifier) @fn)
                 (#eq? @fn "exec")) @match
            """,
        ),
        TreeSitterRule(
            subcategory="exec_sync_usage",
            severity="high",
            category="security_posture",
            statement="`execSync(` call detected — command-injection risk.",
            rationale="execSync runs synchronously through the shell; same injection surface as exec().",
            query="""
                ((call_expression
                    function: (identifier) @fn)
                 (#eq? @fn "execSync")) @match
            """,
        ),
        TreeSitterRule(
            subcategory="eval_usage",
            severity="critical",
            category="security_posture",
            statement="`eval()` call detected — arbitrary code execution.",
            rationale="eval evaluates a string as JS in the local scope; one of the highest-risk APIs in the language.",
            query="""
                ((call_expression
                    function: (identifier) @fn)
                 (#eq? @fn "eval")) @match
            """,
        ),
        TreeSitterRule(
            subcategory="function_constructor",
            severity="high",
            category="security_posture",
            statement="`new Function(...)` constructor — compiles a string into code.",
            rationale="The Function constructor is functionally eval. User input here is an injection vector.",
            query="""
                ((new_expression
                    constructor: (identifier) @fn)
                 (#eq? @fn "Function")) @match
            """,
        ),
        TreeSitterRule(
            subcategory="inner_html_assignment",
            severity="high",
            category="security_posture",
            statement="`innerHTML =` assignment — DOM XSS sink.",
            rationale="Assigning to innerHTML parses a string as HTML; user input here is a DOM-XSS vector.",
            query="""
                (assignment_expression
                    left: (member_expression
                        property: (property_identifier) @prop)
                    (#eq? @prop "innerHTML")) @match
            """,
        ),
    ]
    if allow_jsx:
        rules.append(
            TreeSitterRule(
                subcategory="dangerously_set_inner_html",
                severity="high",
                category="security_posture",
                statement="`dangerouslySetInnerHTML` JSX attribute — React XSS sink.",
                rationale="dangerouslySetInnerHTML bypasses React's escaping; user input here is an XSS vector.",
                query="""
                    ((jsx_attribute
                        (property_identifier) @attr)
                     (#eq? @attr "dangerouslySetInnerHTML")) @match
                """,
            )
        )
    return rules


# TypeScript-specific (no JSX): "as any" cast.
TS_ONLY_RULES: list[TreeSitterRule] = [
    TreeSitterRule(
        subcategory="as_any",
        severity="medium",
        category="code_quality_contracts",
        statement="`as any` type cast detected — escape hatch from the type system.",
        rationale="`as any` disables type checking for the cast site; use `unknown` plus a real type guard.",
        query="""
            ((as_expression
                (predefined_type) @type)
             (#eq? @type "any")) @match
        """,
    ),
]


JS_RULES: list[TreeSitterRule] = _shared_rules(allow_jsx=False)
TS_RULES: list[TreeSitterRule] = _shared_rules(allow_jsx=False) + TS_ONLY_RULES
TSX_RULES: list[TreeSitterRule] = _shared_rules(allow_jsx=True) + TS_ONLY_RULES


__all__ = [
    "JS_RULES",
    "TS_RULES",
    "TSX_RULES",
    "JS_SUFFIXES",
    "TS_SUFFIXES",
    "TSX_SUFFIXES",
]
