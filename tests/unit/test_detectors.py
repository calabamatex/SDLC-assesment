from sdlc_assessor.detectors.registry import DetectorRegistry


def test_detectors_registry_lists_phase3_detectors() -> None:
    registry = DetectorRegistry()
    assert registry.registered() == ["common", "python_pack", "tsjs_pack"]


def test_detectors_find_probable_secret_fixture_signal() -> None:
    registry = DetectorRegistry()
    findings = registry.run("tests/fixtures/fixture_probable_secret")
    subcats = {f["subcategory"] for f in findings}
    assert "probable_secrets" in subcats


def test_detectors_emit_finding_shape_fields() -> None:
    registry = DetectorRegistry()
    findings = registry.run("tests/fixtures/fixture_probable_secret")
    required = {
        "category",
        "subcategory",
        "severity",
        "statement",
        "evidence",
        "confidence",
        "applicability",
        "score_impact",
        "detector_source",
    }
    assert findings
    assert required.issubset(findings[0].keys())
