from sdlc_assessor.classifier.engine import classify_repo
from sdlc_assessor.collector.engine import collect_evidence
from sdlc_assessor.core.io import write_json
from sdlc_assessor.detectors.registry import DetectorRegistry


def _classification_file(tmp_path, repo: str) -> str:
    payload = classify_repo(repo)
    out = tmp_path / "classification.json"
    write_json(out, payload)
    return str(out)


def test_collector_assembles_evidence_shape(tmp_path) -> None:
    classification = _classification_file(tmp_path, "tests/fixtures/fixture_python_basic")
    evidence = collect_evidence("tests/fixtures/fixture_python_basic", classification)
    assert set(evidence.keys()) == {
        "repo_meta",
        "classification",
        "inventory",
        "findings",
        "scoring",
        "hard_blockers",
    }


def test_collector_inventory_has_non_negative_core_fields(tmp_path) -> None:
    classification = _classification_file(tmp_path, "tests/fixtures/fixture_python_basic")
    evidence = collect_evidence("tests/fixtures/fixture_python_basic", classification)
    inv = evidence["inventory"]
    assert inv["source_files"] >= 1
    assert inv["source_loc"] >= 1
    assert inv["test_files"] >= 0


def test_evidence_detector_registry_plumbing_returns_list() -> None:
    registry = DetectorRegistry()
    assert isinstance(registry.registered(), list)
    assert "common" in registry.registered()
    findings = registry.run("tests/fixtures/fixture_python_basic")
    assert isinstance(findings, list)
