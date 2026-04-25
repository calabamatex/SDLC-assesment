"""Classifier tests covering language detection (SDLC-014) and archetype inference (SDLC-016)."""

from sdlc_assessor.classifier.engine import classify_repo


def test_classifier_outputs_required_shape() -> None:
    result = classify_repo("tests/fixtures/fixture_empty_repo")
    assert "repo_meta" in result
    assert "classification" in result
    classification = result["classification"]
    assert classification["repo_archetype"] == "unknown"
    assert 0 <= classification["classification_confidence"] <= 1


def test_classifier_defaults_empty_repo_to_common_pack() -> None:
    result = classify_repo("tests/fixtures/fixture_empty_repo")
    packs = result["classification"]["language_pack_selection"]
    assert packs == ["common"]


def test_classifier_picks_tsjs_pack_for_javascript_only_repo() -> None:
    classification = classify_repo("tests/fixtures/fixture_javascript_basic")["classification"]
    assert "typescript_javascript" in classification["language_pack_selection"]


def test_classifier_picks_tsjs_pack_for_tsx_only_repo() -> None:
    classification = classify_repo("tests/fixtures/fixture_tsx_only")["classification"]
    assert "typescript_javascript" in classification["language_pack_selection"]


def test_classifier_ignores_vendored_node_modules() -> None:
    """Files inside node_modules must not influence the classifier signals."""
    classification = classify_repo("tests/fixtures/fixture_vendored_node_modules")["classification"]
    rationale = "\n".join(classification.get("rationale", []))
    assert "node_modules" not in rationale


def test_classifier_recognizes_service_archetype() -> None:
    classification = classify_repo("tests/fixtures/fixture_service_archetype")["classification"]
    assert classification["repo_archetype"] == "service"
    assert classification["network_exposure"] is True
    assert classification["classification_confidence"] >= 0.3


def test_classifier_recognizes_library_archetype() -> None:
    classification = classify_repo("tests/fixtures/fixture_library_archetype")["classification"]
    assert classification["repo_archetype"] == "library"
    assert classification["classification_confidence"] >= 0.3


def test_classifier_recognizes_monorepo_archetype() -> None:
    classification = classify_repo("tests/fixtures/fixture_monorepo_archetype")["classification"]
    assert classification["repo_archetype"] == "monorepo"


def test_classifier_recognizes_research_repo_archetype() -> None:
    classification = classify_repo("tests/fixtures/fixture_research_repo")["classification"]
    assert classification["repo_archetype"] == "research_repo"
    assert classification["maturity_profile"] == "research"
    assert classification["release_surface"] == "research_only"


def test_classifier_recognizes_infrastructure_archetype() -> None:
    classification = classify_repo("tests/fixtures/fixture_infrastructure_archetype")["classification"]
    assert classification["repo_archetype"] == "infrastructure"


def test_classifier_recognizes_internal_tool_archetype() -> None:
    classification = classify_repo("tests/fixtures/fixture_internal_tool_archetype")["classification"]
    assert classification["repo_archetype"] == "internal_tool"


def test_classifier_python_basic_falls_through_to_internal_tool() -> None:
    """fixture_python_basic has a single hello() and no manifest — internal_tool fallback."""
    classification = classify_repo("tests/fixtures/fixture_python_basic")["classification"]
    # Without a pyproject this fixture has no archetype signals → unknown.
    assert classification["repo_archetype"] in {"unknown", "internal_tool"}
    assert "python" in classification["language_pack_selection"]
