"""Credibility Engine — Runtime Module.

Maintains live claim state, persists drift events, calculates
Credibility Index, writes canonical artifacts, and exposes API endpoints.

Multi-tenant: each tenant gets isolated state and persistence.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from importlib.metadata import version as _pkg_version, PackageNotFoundError

try:
    __version__ = _pkg_version("deepsigma")
except PackageNotFoundError:
    # Fallback: read from pyproject.toml when running from source without pip install
    import re as _re
    from pathlib import Path as _Path
    _pyproject = _Path(__file__).resolve().parent.parent.parent.parent / "pyproject.toml"
    _m = _re.search(r'^version\s*=\s*"([^"]+)"', _pyproject.read_text()) if _pyproject.exists() else None
    __version__ = _m.group(1) + "-dev" if _m else "0.0.0-dev"

from credibility_engine.constants import DEFAULT_TENANT_ID
from credibility_engine.engine import CredibilityEngine
from credibility_engine.index import calculate_index
from credibility_engine.models import (
    Claim,
    CorrelationCluster,
    DriftEvent,
    Snapshot,
    SyncRegion,
)
from credibility_engine.packet import (
    generate_credibility_packet,
    seal_credibility_packet,
)
from credibility_engine.store import CredibilityStore

__all__ = [
    "DEFAULT_TENANT_ID",
    "CredibilityEngine",
    "CredibilityStore",
    "calculate_index",
    "generate_credibility_packet",
    "seal_credibility_packet",
    "Claim",
    "CorrelationCluster",
    "DriftEvent",
    "Snapshot",
    "SyncRegion",
]
