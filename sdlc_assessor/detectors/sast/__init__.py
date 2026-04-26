"""SAST adapter pack (SDLC-050..054).

Importing this package self-registers the bundled adapters with the
framework. Use :func:`run_sast_adapters` (re-exported below) to dispatch
all of them in one call.
"""

from __future__ import annotations

# Order matters only for the order findings appear in the output. We list
# Python tools first (most users have them), then JS, then multi-language.
from sdlc_assessor.detectors.sast import bandit_adapter as bandit_adapter  # noqa: F401
from sdlc_assessor.detectors.sast import eslint_adapter as eslint_adapter  # noqa: F401
from sdlc_assessor.detectors.sast import ruff_adapter as ruff_adapter  # noqa: F401
from sdlc_assessor.detectors.sast import semgrep_adapter as semgrep_adapter  # noqa: F401
from sdlc_assessor.detectors.sast.framework import (
    SASTAdapter,
    SASTResult,
    register_adapter,
    registered_adapters,
    run_sast_adapters,
)

__all__ = [
    "SASTAdapter",
    "SASTResult",
    "register_adapter",
    "registered_adapters",
    "run_sast_adapters",
]
