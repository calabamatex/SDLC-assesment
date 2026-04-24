"""Core typed models for phase-0 contracts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RepoMeta:
    name: str
    default_branch: str
    analysis_timestamp: str
