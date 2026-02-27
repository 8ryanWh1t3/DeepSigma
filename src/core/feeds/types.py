"""FEEDS type enums — topics, record types, and classification tokens."""

from __future__ import annotations

from enum import Enum


class FeedTopic(str, Enum):
    """The six canonical FEEDS topics."""

    TRUTH_SNAPSHOT = "truth_snapshot"
    AUTHORITY_SLICE = "authority_slice"
    DECISION_LINEAGE = "decision_lineage"
    DRIFT_SIGNAL = "drift_signal"
    CANON_ENTRY = "canon_entry"
    PACKET_INDEX = "packet_index"


class RecordType(str, Enum):
    """Record type codes carried in every feed envelope."""

    TS = "TS"
    ALS = "ALS"
    DLR = "DLR"
    DS = "DS"
    CE = "CE"
    MANIFEST = "MANIFEST"


class Classification(str, Enum):
    """Generic classification tokens (GPE-safe)."""

    LEVEL_0 = "LEVEL_0"
    LEVEL_1 = "LEVEL_1"
    LEVEL_2 = "LEVEL_2"
    LEVEL_3 = "LEVEL_3"
    LEVEL_4 = "LEVEL_4"
    LEVEL_5 = "LEVEL_5"
    LEVEL_6 = "LEVEL_6"
    OTHER = "OTHER"


# Canonical mapping: topic -> record type
TOPIC_TO_RECORD: dict[FeedTopic, RecordType] = {
    FeedTopic.TRUTH_SNAPSHOT: RecordType.TS,
    FeedTopic.AUTHORITY_SLICE: RecordType.ALS,
    FeedTopic.DECISION_LINEAGE: RecordType.DLR,
    FeedTopic.DRIFT_SIGNAL: RecordType.DS,
    FeedTopic.CANON_ENTRY: RecordType.CE,
    FeedTopic.PACKET_INDEX: RecordType.MANIFEST,
}
