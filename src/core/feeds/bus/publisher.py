"""Atomic file-bus publisher for FEEDS events."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

from ..validate import validate_feed_event
from ..types import FeedTopic

logger = logging.getLogger(__name__)


class Publisher:
    """Publishes FEEDS events to topic inbox directories via atomic write.

    Write strategy: temp file + ``os.rename()`` (POSIX-atomic on same filesystem).
    """

    def __init__(self, topics_root: str | Path) -> None:
        self._root = Path(topics_root).resolve()

    def publish(self, topic: FeedTopic | str, event: Dict[str, Any]) -> Path:
        """Validate and atomically publish an event to a topic inbox.

        Args:
            topic: Target FEEDS topic.
            event: Complete FEEDS envelope dict.

        Returns:
            Path to the written event file.

        Raises:
            ValueError: If envelope validation fails.
            FileNotFoundError: If topic inbox directory does not exist.
        """
        result = validate_feed_event(event)
        if not result.valid:
            errors = "; ".join(e.message for e in result.errors)
            raise ValueError(f"Envelope validation failed: {errors}")

        topic_val = topic.value if isinstance(topic, FeedTopic) else topic
        inbox = self._root / topic_val / "inbox"
        if not inbox.is_dir():
            raise FileNotFoundError(f"Topic inbox not found: {inbox}")

        event_id = event["eventId"]
        subtype = event.get("subtype", "")
        target = inbox / f"{event_id}.json"
        tmp = inbox / f".tmp_{event_id}.json"

        data = json.dumps(event, indent=2, sort_keys=False)
        tmp.write_text(data, encoding="utf-8")
        os.rename(str(tmp), str(target))

        logger.debug(
            "Published event %s to %s (subtype=%s)",
            event_id, topic_val, subtype,
        )

        return target
