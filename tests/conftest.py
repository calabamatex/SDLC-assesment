import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def classification_json_path(tmp_path: Path) -> Path:
    """Produce a classification.json for fixture_python_basic in tmp_path.

    Tests that feed a classification into collect_evidence should depend on this
    fixture rather than a hardcoded path under ``.sdlc/``. The hardcoded path
    relied on a side effect from a previously-run ``sdlc classify`` command and
    broke isolation on clean checkouts.
    """
    from sdlc_assessor.classifier.engine import classify_repo
    from sdlc_assessor.core.io import write_json

    payload = classify_repo("tests/fixtures/fixture_python_basic")
    out = tmp_path / "classification.json"
    write_json(out, payload)
    return out
