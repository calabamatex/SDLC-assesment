"""Cross-detector dedupe tests (SDLC-062)."""

from __future__ import annotations

from sdlc_assessor.normalizer.dedupe import deduplicate_findings, family_for


def _f(
    *,
    subcat: str,
    category: str = "security_posture",
    severity: str = "high",
    path: str = "src/app.py",
    line: int | None = 10,
    detector: str = "x",
    statement: str = "demo",
    confidence: str = "high",
    tags: list[str] | None = None,
) -> dict:
    return {
        "id": f"F-{subcat}",
        "category": category,
        "subcategory": subcat,
        "severity": severity,
        "statement": statement,
        "evidence": [
            {
                "path": path,
                "line_start": line,
                "line_end": line,
                "snippet": "x = 1",
                "match_type": "exact",
                "count": 1,
            }
        ],
        "confidence": confidence,
        "applicability": "applicable",
        "score_impact": {"direction": "negative", "magnitude": 7},
        "detector_source": detector,
        "tags": list(tags) if tags else [],
    }


def test_family_for_classifies_known_subcategories() -> None:
    assert family_for(_f(subcat="eval_or_exec")) == "code_eval"
    assert family_for(_f(subcat="bandit_B307")) == "code_eval"
    assert family_for(_f(subcat="probable_secrets")) == "hardcoded_secret"
    assert family_for(_f(subcat="bandit_B105")) == "hardcoded_secret"
    assert family_for(_f(subcat="totally_unknown_thing")) is None


def test_dedupe_passes_through_findings_with_no_family() -> None:
    findings = [
        _f(subcat="kotlin_println_call"),
        _f(subcat="csharp_dynamic_type"),
    ]
    out = deduplicate_findings(findings)
    assert len(out) == 2
    # Order is preserved for untouched findings.
    assert {f["subcategory"] for f in out} == {"kotlin_println_call", "csharp_dynamic_type"}


def test_dedupe_merges_same_family_same_path_line() -> None:
    """Native eval finding + bandit B307 + ruff S307 on the same line collapse."""
    findings = [
        _f(subcat="eval_or_exec", severity="critical", detector="python_pack.eval_or_exec"),
        _f(subcat="bandit_B307", severity="high", detector="sast.bandit"),
        _f(subcat="ruff_S307", severity="high", detector="sast.ruff"),
    ]
    out = deduplicate_findings(findings)
    assert len(out) == 1
    merged = out[0]
    # Strongest severity wins.
    assert merged["severity"] == "critical"
    # detector_source becomes merged:<sorted-sources>.
    assert merged["detector_source"].startswith("merged:")
    assert "python_pack.eval_or_exec" in merged["detector_source"]
    assert "sast.bandit" in merged["detector_source"]
    # Tags include each contributing detector.
    detector_tags = [t for t in merged.get("tags", []) if t.startswith("detector:")]
    assert {"detector:python_pack.eval_or_exec", "detector:sast.bandit", "detector:sast.ruff"} <= set(detector_tags)
    # Statement is annotated with the agreement count.
    assert "3 detectors agreed" in merged["statement"]


def test_dedupe_does_not_merge_different_lines() -> None:
    findings = [
        _f(subcat="eval_or_exec", line=10),
        _f(subcat="bandit_B307", line=12),
    ]
    out = deduplicate_findings(findings)
    assert len(out) == 2
    assert {f["subcategory"] for f in out} == {"eval_or_exec", "bandit_B307"}


def test_dedupe_does_not_merge_different_paths() -> None:
    findings = [
        _f(subcat="eval_or_exec", path="src/a.py"),
        _f(subcat="bandit_B307", path="src/b.py"),
    ]
    out = deduplicate_findings(findings)
    assert len(out) == 2


def test_dedupe_merge_combines_evidence_uniquely() -> None:
    findings = [
        _f(subcat="eval_or_exec", line=10),
        _f(subcat="bandit_B307", line=10),
    ]
    # Add a different evidence path on the second finding to verify combining.
    findings[1]["evidence"].append(
        {"path": "extra/aux.py", "line_start": 1, "snippet": "alt", "match_type": "exact", "count": 1}
    )
    out = deduplicate_findings(findings)
    assert len(out) == 1
    paths = [ev.get("path") for ev in out[0]["evidence"]]
    assert "src/app.py" in paths
    assert "extra/aux.py" in paths


def test_dedupe_shell_exec_family_unifies_native_and_sast() -> None:
    findings = [
        _f(
            subcat="subprocess_shell_true",
            severity="high",
            detector="python_pack.subprocess_shell_true",
        ),
        _f(subcat="bandit_B602", severity="high", detector="sast.bandit"),
    ]
    out = deduplicate_findings(findings)
    assert len(out) == 1
    assert "python_pack" in out[0]["detector_source"]
    assert "bandit" in out[0]["detector_source"]


def test_dedupe_idempotent() -> None:
    findings = [
        _f(subcat="eval_or_exec"),
        _f(subcat="bandit_B307"),
        _f(subcat="kotlin_println_call"),
    ]
    once = deduplicate_findings(findings)
    twice = deduplicate_findings(once)
    # Running dedupe twice is a no-op (idempotent).
    assert len(once) == len(twice)
