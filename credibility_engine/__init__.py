"""Credibility Engine — Runtime Module.

Maintains live claim state, persists drift events, calculates
Credibility Index, writes canonical artifacts, and exposes API endpoints.

Multi-tenant: each tenant gets isolated state and persistence.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

__version__ = "0.9.0"

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
