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
