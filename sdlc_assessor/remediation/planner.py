"""Remediation planner (SDLC-024).

Produces patch-safe tasks with realistic ``phase``, ``change_type``,
``verification_commands``, ``effort``, and ``expected_score_delta`` derived
from the finding subcategory and severity. Replaces the v0.1 implementation
that hardcoded everything to ``phase_1_safety`` / ``modify_block`` /
``["pytest -q"]``.
"""

from __future__ import annotations

from collections import defaultdict

# Allowlist from docs/remediation_planner_spec.md §Change types.
ALLOWED_CHANGE_TYPES = {
    "create_file",
    "update_docs",
    "add_workflow",
    "modify_block",
    "modify_symbol",
    "tighten_validation",
    "replace_unsafe_pattern",
    "remove_artifact",
    "rename_path",
}

ALLOWED_PHASES = {
    "phase_1_security",
    "phase_2_contracts",
    "phase_3_tests",
    "phase_4_ci",
    "phase_5_docs",
}

# (change_type, phase, default_test_requirements, default_verification_commands)
SUBCATEGORY_RULES: dict[str, tuple[str, str, list[str], list[str]]] = {
    "probable_secrets": (
        "tighten_validation",
        "phase_1_security",
        [
            "Add a test that asserts the suspect literal is no longer present in source.",
            "Add a regression test that loads the secret from environment instead.",
        ],
        [
            "git grep -nE '(api[_-]?key|secret|token|password)\\s*[:=]'",
            "pytest -q",
        ],
    ),
    "committed_credential": (
        "remove_artifact",
        "phase_1_security",
        ["Add a CI check that fails if a key/credential file appears in the tree."],
        [
            "test ! -f <path>",
            "git log --all -- <path>",
        ],
    ),
    "subprocess_shell_true": (
        "replace_unsafe_pattern",
        "phase_1_security",
        ["Cover the command-execution path with an arg-array test."],
        ["pytest -q -k subprocess", "ruff check <module>"],
    ),
    "exec_usage": (
        "replace_unsafe_pattern",
        "phase_1_security",
        ["Add a test asserting input is sanitized before exec()."],
        ["npm test", "node --check <module>"],
    ),
    "exec_sync_usage": (
        "replace_unsafe_pattern",
        "phase_1_security",
        ["Add a test asserting input is sanitized before execSync()."],
        ["npm test", "node --check <module>"],
    ),
    "any_usage": (
        "tighten_validation",
        "phase_2_contracts",
        ["Add a typed test that exercises the now-narrowed signature."],
        ["mypy <module>", "pytest -q"],
    ),
    "type_ignore": (
        "tighten_validation",
        "phase_2_contracts",
        ["Add a type-checked test for the previously-ignored path."],
        ["mypy <module>"],
    ),
    "missing_strict_mode": (
        "tighten_validation",
        "phase_2_contracts",
        ["Add a tsc --strict run as a test step."],
        ["npx tsc --noEmit"],
    ),
    "json_parse": (
        "tighten_validation",
        "phase_2_contracts",
        ["Add a parse-failure test for malformed input."],
        ["pytest -q"],
    ),
    "bare_except": (
        "modify_symbol",
        "phase_2_contracts",
        ["Add a unit test for the specific exception type now caught."],
        ["pytest -q"],
    ),
    "broad_except_exception": (
        "modify_symbol",
        "phase_2_contracts",
        ["Add a test exercising the narrowed exception class."],
        ["pytest -q"],
    ),
    "empty_catch": (
        "modify_block",
        "phase_2_contracts",
        ["Add a test that asserts the error is logged or rethrown."],
        ["pytest -q"],
    ),
    "print_usage": (
        "modify_block",
        "phase_2_contracts",
        ["Add a test that asserts the structured logger receives the message."],
        ["pytest -q"],
    ),
    "console_usage": (
        "modify_block",
        "phase_2_contracts",
        ["Add a test that asserts logger usage instead of console."],
        ["pytest -q"],
    ),
    "missing_ci": (
        "add_workflow",
        "phase_4_ci",
        ["Workflow YAML linted by yamllint and runs on a sample push."],
        ["yamllint .github/workflows/", "gh workflow list"],
    ),
    "missing_readme": (
        "update_docs",
        "phase_5_docs",
        ["Wordcount or section presence test in CI."],
        ["test -f README.md", "wc -l README.md"],
    ),
    "missing_security_md": (
        "create_file",
        "phase_5_docs",
        ["File-existence smoke test."],
        ["test -f SECURITY.md"],
    ),
    "committed_artifacts": (
        "remove_artifact",
        "phase_4_ci",
        ["CI check that fails if artifact suffixes return on disk."],
        ["test ! -f <path>"],
    ),
    "large_files": (
        "remove_artifact",
        "phase_4_ci",
        ["CI check that fails the build if files exceed the size threshold."],
        ["du -h <path>"],
    ),
}

DEFAULT_RULE = (
    "modify_block",
    "phase_2_contracts",
    ["Add a regression test reproducing the finding."],
    ["pytest -q"],
)


EFFORT_BY_CHANGE_TYPE = {
    "create_file": "S",
    "update_docs": "S",
    "remove_artifact": "XS",
    "rename_path": "S",
    "add_workflow": "M",
    "modify_block": "S",
    "modify_symbol": "M",
    "replace_unsafe_pattern": "M",
    "tighten_validation": "M",
}


SEVERITY_BASE_DELTA = {
    "info": 0.5,
    "low": 1.0,
    "medium": 2.5,
    "high": 5.0,
    "critical": 9.0,
}

CONFIDENCE_FACTOR = {"high": 1.0, "medium": 0.85, "low": 0.65}

MATURITY_FACTOR = {"production": 1.2, "prototype": 0.95, "research": 0.9, "unknown": 1.0}


def _expected_score_delta(finding: dict, maturity: str) -> float:
    sev = SEVERITY_BASE_DELTA.get(finding.get("severity", "low"), 1.0)
    conf = CONFIDENCE_FACTOR.get(finding.get("confidence", "medium"), 0.85)
    mat = MATURITY_FACTOR.get(maturity, 1.0)
    mag = float(finding.get("score_impact", {}).get("magnitude", 5)) / 10.0
    delta = sev * conf * mat * (0.6 + 0.4 * mag)
    # Round to nearest 0.5.
    return round(delta * 2) / 2


def _maturity_from_scored(scored: dict) -> str:
    return (
        scored.get("scoring", {}).get("effective_profile", {}).get("maturity", "unknown")
    )


def _task_from_finding(index: int, finding: dict, maturity: str) -> dict:
    subcat = finding.get("subcategory", "")
    rule = SUBCATEGORY_RULES.get(subcat, DEFAULT_RULE)
    change_type, phase, test_reqs, verif_cmds = rule

    evidence = finding.get("evidence", []) or []
    target_paths = [ev.get("path", "unknown") for ev in evidence if ev.get("path")]
    if not target_paths:
        target_paths = ["unknown"]

    severity = finding.get("severity", "low")
    priority = "high" if severity in {"high", "critical"} else "medium" if severity == "medium" else "low"

    return {
        "id": f"R-{index:03d}",
        "phase": phase,
        "priority": priority,
        "linked_finding_ids": [finding.get("id", f"F-{index:04d}")],
        "target_paths": target_paths,
        "anchor_guidance": finding.get("statement", "Refer to the linked finding for context."),
        "change_type": change_type,
        "rationale": finding.get("score_impact", {}).get("rationale")
        or finding.get("statement", "Address the finding to reduce its scoring impact."),
        "implementation_steps": _implementation_steps(finding, change_type),
        "test_requirements": test_reqs,
        "verification_commands": verif_cmds,
        "effort": EFFORT_BY_CHANGE_TYPE.get(change_type, "M"),
        "expected_score_delta": _expected_score_delta(finding, maturity),
    }


def _implementation_steps(finding: dict, change_type: str) -> list[str]:
    statement = finding.get("statement", "the underlying finding")
    paths = ", ".join(
        ev.get("path", "")
        for ev in (finding.get("evidence", []) or [])
        if ev.get("path")
    ) or "n/a"
    if change_type == "create_file":
        return [
            f"Create the missing file at {paths}.",
            "Populate it with the canonical content for this artifact.",
            "Reference it from the project README.",
        ]
    if change_type == "update_docs":
        return [
            f"Update or add documentation at {paths}.",
            "Cite the finding in CHANGELOG.md under the relevant section.",
        ]
    if change_type == "add_workflow":
        return [
            f"Add a GitHub Actions workflow that addresses {statement}.",
            "Pin actions and runner versions; avoid `@latest`.",
            "Run the workflow on push and pull_request.",
        ]
    if change_type == "remove_artifact":
        return [
            f"Remove {paths} from the working tree.",
            "Add a `.gitignore` rule to prevent re-introduction.",
            "If needed, rewrite git history to expunge any committed copies.",
        ]
    if change_type == "tighten_validation":
        return [
            f"Inspect {paths} for the unsafe-by-default pattern.",
            "Replace the loose validation/cast with an explicit, narrowly typed alternative.",
            "Add or extend a unit test that exercises the now-validated branch.",
        ]
    if change_type == "replace_unsafe_pattern":
        return [
            f"Identify the unsafe call(s) in {paths}.",
            "Replace with the safe argument-array equivalent (no shell interpretation).",
            "Add a regression test that asserts the safe behaviour.",
        ]
    if change_type == "modify_symbol":
        return [
            f"Locate the offending symbol in {paths}.",
            "Narrow the symbol's contract or exception type.",
            "Update tests to match the new contract.",
        ]
    if change_type == "rename_path":
        return [
            f"Rename {paths} to a clearer / safer alternative.",
            "Search-replace all references.",
            "Add a deprecation note if the old name was previously importable.",
        ]
    # default: modify_block
    return [
        f"Locate the offending block in {paths}.",
        "Apply the minimal targeted change.",
        "Confirm behaviour remains correct via existing or new tests.",
    ]


def build_remediation_plan(scored: dict) -> dict:
    findings = scored.get("findings", [])
    maturity = _maturity_from_scored(scored)

    # Sort: critical first, then by severity weight desc, then by category for stability.
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    sorted_findings = sorted(
        findings,
        key=lambda f: (sev_order.get(f.get("severity", "low"), 5), f.get("category", "")),
    )

    tasks = [_task_from_finding(i + 1, f, maturity) for i, f in enumerate(sorted_findings)]

    blockers = scored.get("hard_blockers", [])

    by_phase: dict[str, list[dict]] = defaultdict(list)
    for task in tasks:
        by_phase[task["phase"]].append(task)
    phase_summary = {
        phase: {
            "task_count": len(by_phase.get(phase, [])),
            "expected_score_delta": round(
                sum(t.get("expected_score_delta", 0) for t in by_phase.get(phase, [])), 1
            ),
        }
        for phase in ALLOWED_PHASES
    }

    summary = {
        "phase_count": sum(1 for p in phase_summary.values() if p["task_count"] > 0),
        "task_count": len(tasks),
        "blocker_count": len(blockers),
        "expected_score_delta": round(sum(t.get("expected_score_delta", 0) for t in tasks), 1),
        "per_phase": phase_summary,
    }

    return {
        "summary": summary,
        "tasks": tasks,
        "phases": [
            {"phase": phase, "tasks": [t["id"] for t in by_phase.get(phase, [])]}
            for phase in [
                "phase_1_security",
                "phase_2_contracts",
                "phase_3_tests",
                "phase_4_ci",
                "phase_5_docs",
            ]
            if by_phase.get(phase)
        ],
        "verification_checklist": [
            "Run the full test suite (`pytest -q`).",
            "Run `ruff check .` and `mypy sdlc_assessor/`.",
            "Run `python scripts/calibration_check.py`.",
            "Apply each task's `verification_commands` before marking it complete.",
        ],
    }


__all__ = [
    "ALLOWED_CHANGE_TYPES",
    "ALLOWED_PHASES",
    "SUBCATEGORY_RULES",
    "build_remediation_plan",
]
