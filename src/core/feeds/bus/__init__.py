"""FEEDS file-based pub/sub bus.

Topic layout::

    <topics_root>/
        truth_snapshot/{inbox,processing,ack,dlq}
        authority_slice/{inbox,processing,ack,dlq}
        ...
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

from ..types import FeedTopic

from .publisher import Publisher
from .subscriber import Subscriber
from .dlq import DLQManager

SUBDIRS = ("inbox", "processing", "ack", "dlq")


def init_topic_layout(
    topics_root: str | Path,
    topics: Optional[Sequence[FeedTopic]] = None,
) -> Path:
    """Create the folder structure for all (or specified) FEEDS topics.

    Idempotent — safe to call multiple times.

    Returns:
        The resolved topics_root path.
    """
    root = Path(topics_root).resolve()
    for topic in topics or FeedTopic:
        for sub in SUBDIRS:
            (root / topic.value / sub).mkdir(parents=True, exist_ok=True)
    return root


__all__ = [
    "DLQManager",
    "Publisher",
    "Subscriber",
    "init_topic_layout",
]
