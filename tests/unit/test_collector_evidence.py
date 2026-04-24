from sdlc_assessor.collector.engine import collect_evidence
from sdlc_assessor.detectors.registry import DetectorRegistry


def test_collector_assembles_evidence_shape() -> None:
    evidence = collect_evidence(
        "tests/fixtures/fixture_python_basic",
        ".sdlc/classification.json",
    )
    assert set(evidence.keys()) == {
        "repo_meta",
        "classification",
        "inventory",
        "findings",
        "scoring",
        "hard_blockers",
    }


def test_collector_inventory_has_non_negative_core_fields() -> None:
    evidence = collect_evidence(
        "tests/fixtures/fixture_python_basic",
        ".sdlc/classification.json",
    )
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
