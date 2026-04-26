"""LLM narrator tests (SDLC-066).

The Anthropic SDK isn't a hard dependency. Tests cover:

- Activation gates (env var, SDK presence, ``use_llm`` flag).
- Graceful no-op when any gate fails.
- Successful narration with a mocked SDK.
- Cache hit on identical input.
- Silent fallback when the SDK call raises.
- Scorer integration: ``score_evidence(use_llm_narrator=True)`` substitutes
  the deterministic summary when the narrator returns prose.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from sdlc_assessor.scorer import llm_narrator
from sdlc_assessor.scorer.llm_narrator import (
    DEFAULT_MODEL,
    llm_available,
    narrate_category,
    reset_cache,
)


def _fake_response(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


@pytest.fixture(autouse=True)
def _clean_cache():
    reset_cache()
    yield
    reset_cache()


# ---------------------------------------------------------------------------
# Activation gates
# ---------------------------------------------------------------------------


def test_returns_none_when_use_llm_false() -> None:
    assert (
        narrate_category(
            category="x",
            applicability="applicable",
            findings_in_cat=[],
            deduction_total=0.0,
            score=10,
            max_score=10,
            use_llm=False,
        )
        is None
    )


def test_returns_none_when_no_api_key(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert (
        narrate_category(
            category="x",
            applicability="applicable",
            findings_in_cat=[],
            deduction_total=0.0,
            score=10,
            max_score=10,
            use_llm=True,
        )
        is None
    )


def test_returns_none_when_sdk_missing(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    # Force an ImportError inside llm_available by removing the module from sys.modules
    # and patching its import.
    import sys

    monkeypatch.setitem(sys.modules, "anthropic", None)
    assert llm_available() is False


def test_llm_available_true_when_both_gates_open(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "stub")
    fake_module = MagicMock()
    import sys

    monkeypatch.setitem(sys.modules, "anthropic", fake_module)
    assert llm_available() is True


# ---------------------------------------------------------------------------
# Successful path with mocked SDK
# ---------------------------------------------------------------------------


def test_narrate_category_returns_text_when_all_gates_open(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "stub")

    fake_anthropic = MagicMock()
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _fake_response(
        "Security posture is acceptable: one medium finding from F-0001."
    )
    fake_anthropic.Anthropic.return_value = fake_client

    import sys

    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

    findings = [
        {
            "id": "F-0001",
            "subcategory": "probable_secrets",
            "severity": "medium",
            "confidence": "high",
            "statement": "secret",
            "evidence": [{"path": "src/app.py", "line_start": 12}],
        }
    ]
    out = narrate_category(
        category="security_posture",
        applicability="applicable",
        findings_in_cat=findings,
        deduction_total=2.5,
        score=15,
        max_score=20,
        use_llm=True,
    )
    assert out == "Security posture is acceptable: one medium finding from F-0001."
    fake_client.messages.create.assert_called_once()


def test_narrate_category_returns_none_when_sdk_raises(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "stub")
    fake_anthropic = MagicMock()
    fake_anthropic.Anthropic.side_effect = RuntimeError("boom")
    import sys

    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

    out = narrate_category(
        category="x",
        applicability="applicable",
        findings_in_cat=[],
        deduction_total=0.0,
        score=10,
        max_score=10,
        use_llm=True,
    )
    assert out is None


def test_narrate_category_caches_repeated_calls(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "stub")
    fake_anthropic = MagicMock()
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _fake_response("cached prose")
    fake_anthropic.Anthropic.return_value = fake_client
    import sys

    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

    findings = [
        {
            "id": "F-1",
            "subcategory": "x",
            "severity": "low",
            "confidence": "high",
            "statement": "y",
            "evidence": [{"path": "p", "line_start": 1}],
        }
    ]
    kwargs = {
        "category": "code_quality_contracts",
        "applicability": "applicable",
        "findings_in_cat": findings,
        "deduction_total": 1.0,
        "score": 12,
        "max_score": 15,
        "use_llm": True,
    }
    a = narrate_category(**kwargs)
    b = narrate_category(**kwargs)
    assert a == b == "cached prose"
    # Cache hit on the second call.
    assert fake_client.messages.create.call_count == 1


# ---------------------------------------------------------------------------
# Scorer integration
# ---------------------------------------------------------------------------


def test_score_evidence_uses_llm_narrative_when_enabled(monkeypatch) -> None:
    """When use_llm_narrator=True and the SDK works, summaries change."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "stub")
    fake_anthropic = MagicMock()
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _fake_response("LLM-NARRATIVE-MARKER")
    fake_anthropic.Anthropic.return_value = fake_client
    import sys

    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)
    reset_cache()

    import tempfile

    from sdlc_assessor.classifier.engine import classify_repo
    from sdlc_assessor.collector.engine import collect_evidence
    from sdlc_assessor.core.io import write_json
    from sdlc_assessor.scorer.engine import score_evidence
    with tempfile.TemporaryDirectory() as td:
        cls = classify_repo("tests/fixtures/fixture_python_basic")
        cls_path = f"{td}/c.json"
        write_json(cls_path, cls)
        evidence = collect_evidence("tests/fixtures/fixture_python_basic", cls_path)
        scored = score_evidence(
            evidence,
            "engineering_triage",
            "prototype",
            "cli",
            use_llm_narrator=True,
            llm_model=DEFAULT_MODEL,
        )
    summaries = [c["summary"] for c in scored["scoring"]["category_scores"]]
    # At least one category narrative should be the LLM marker (categories
    # without findings still hit the API per current logic; we accept either
    # all-LLM or some-LLM because the deterministic narrator still wins for
    # not_applicable categories).
    assert any("LLM-NARRATIVE-MARKER" in s for s in summaries)


def test_score_evidence_falls_back_to_deterministic_when_narrator_returns_none(monkeypatch) -> None:
    """When use_llm_narrator=True but the gate is closed, summaries are deterministic."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    reset_cache()

    import tempfile

    from sdlc_assessor.classifier.engine import classify_repo
    from sdlc_assessor.collector.engine import collect_evidence
    from sdlc_assessor.core.io import write_json
    from sdlc_assessor.scorer.engine import score_evidence
    with tempfile.TemporaryDirectory() as td:
        cls = classify_repo("tests/fixtures/fixture_python_basic")
        cls_path = f"{td}/c.json"
        write_json(cls_path, cls)
        evidence = collect_evidence("tests/fixtures/fixture_python_basic", cls_path)
        scored = score_evidence(
            evidence,
            "engineering_triage",
            "prototype",
            "cli",
            use_llm_narrator=True,
        )
    summaries = [c["summary"] for c in scored["scoring"]["category_scores"]]
    # No LLM marker; deterministic phrases ("No findings in this category" etc.) appear.
    assert not any("LLM-NARRATIVE-MARKER" in s for s in summaries)


def test_module_state_smoke() -> None:
    state = llm_narrator._module_state()
    assert state["max_findings_in_prompt"] >= 1
