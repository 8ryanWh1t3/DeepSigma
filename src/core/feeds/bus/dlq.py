"""Dead-letter queue manager for FEEDS bus."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from ..types import FeedTopic


class DLQManager:
    """Manages dead-letter queue events for a single FEEDS topic.

    Supports listing, replaying (dlq -> inbox), and purging.
    """

    def __init__(self, topics_root: str | Path, topic: FeedTopic | str) -> None:
        self._root = Path(topics_root).resolve()
        self._topic = topic.value if isinstance(topic, FeedTopic) else topic
        self._base = self._root / self._topic

    @property
    def dlq_dir(self) -> Path:
        return self._base / "dlq"

    @property
    def inbox(self) -> Path:
        return self._base / "inbox"

    def list_events(self) -> List[Path]:
        """Return sorted list of event files in DLQ (excludes .error.json)."""
        return sorted(
            f for f in self.dlq_dir.glob("*.json") if not f.name.endswith(".error.json")
        )

    def replay(self, event_id: str | None = None) -> int:
        """Replay DLQ events back to inbox.

        Args:
            event_id: If provided, replay only this event. Otherwise replay all.

        Returns:
            Number of events replayed.
        """
        if event_id is not None:
            target = self.dlq_dir / f"{event_id}.json"
            if not target.exists():
                return 0
            os.rename(str(target), str(self.inbox / target.name))
            # Clean up error metadata if present
            error_file = self.dlq_dir / f"{event_id}.error.json"
            if error_file.exists():
                error_file.unlink()
            return 1

        events = self.list_events()
        replayed = 0
        for event_file in events:
            os.rename(str(event_file), str(self.inbox / event_file.name))
            error_file = self.dlq_dir / f"{event_file.stem}.error.json"
            if error_file.exists():
                error_file.unlink()
            replayed += 1
        return replayed

    def purge(self) -> int:
        """Delete all events and error metadata from DLQ.

        Returns:
            Number of files removed.
        """
        removed = 0
        for f in self.dlq_dir.glob("*.json"):
            f.unlink()
            removed += 1
        return removed
