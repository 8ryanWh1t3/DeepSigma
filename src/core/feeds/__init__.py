"""FEEDS — Federated Event Envelope Distribution Surface.

Event-driven layer connecting governance primitives (TS, ALS, DLR, DS, CE)
via a file-based pub/sub bus with manifest-first ingest.
"""

from .types import Classification, FeedTopic, RecordType, TOPIC_TO_RECORD
from .envelope import build_envelope, compute_payload_hash
from .validate import validate_feed_event
from .bus import DLQManager, Publisher, Subscriber, init_topic_layout
from .ingest import IngestOrchestrator, IngestResult
from .consumers import (
    AuthorityGateConsumer,
    EvidenceCheckConsumer,
    TriageEntry,
    TriageState,
    TriageStore,
)
from .canon import CanonStore, ClaimValidator, MGWriter

__all__ = [
    "AuthorityGateConsumer",
    "CanonStore",
    "ClaimValidator",
    "Classification",
    "DLQManager",
    "EvidenceCheckConsumer",
    "FeedTopic",
    "IngestOrchestrator",
    "IngestResult",
    "MGWriter",
    "Publisher",
    "RecordType",
    "Subscriber",
    "TOPIC_TO_RECORD",
    "TriageEntry",
    "TriageState",
    "TriageStore",
    "build_envelope",
    "compute_payload_hash",
    "init_topic_layout",
    "validate_feed_event",
]
