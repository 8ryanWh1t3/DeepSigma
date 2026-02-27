"""Poll-based subscriber with ack lifecycle for FEEDS events."""

from __future__ import annotations

import json
import os
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List

from ..types import FeedTopic


class Subscriber:
    """Polls a topic inbox, processes events, and acks or routes to DLQ.

    Lifecycle per event:
        inbox/ -> processing/ -> ack/   (success)
        inbox/ -> processing/ -> dlq/   (handler exception)

    Multi-worker safety: ``os.rename()`` is atomic on POSIX; racing workers
    that lose the rename get ``FileNotFoundError`` and skip the event.
    """

    def __init__(self, topics_root: str | Path, topic: FeedTopic | str) -> None:
        self._root = Path(topics_root).resolve()
        self._topic = topic.value if isinstance(topic, FeedTopic) else topic
        self._base = self._root / self._topic

    @property
    def inbox(self) -> Path:
        return self._base / "inbox"

    @property
    def processing(self) -> Path:
        return self._base / "processing"

    @property
    def ack_dir(self) -> Path:
        return self._base / "ack"

    @property
    def dlq_dir(self) -> Path:
        return self._base / "dlq"

    def poll(
        self,
        handler: Callable[[Dict[str, Any]], None],
        batch_size: int = 10,
    ) -> int:
        """Poll inbox, process events through handler, ack or dlq.

        Args:
            handler: Callable that receives the parsed event dict.
                     Raising an exception routes the event to DLQ.
            batch_size: Maximum events to process in one poll cycle.

        Returns:
            Number of events successfully processed (acked).
        """
        files = sorted(self.inbox.glob("*.json"))[:batch_size]
        acked = 0

        for event_file in files:
            processing_path = self.processing / event_file.name
            try:
                os.rename(str(event_file), str(processing_path))
            except FileNotFoundError:
                # Another worker claimed it
                continue

            try:
                event = json.loads(processing_path.read_text(encoding="utf-8"))
                handler(event)
                # Success -> ack
                os.rename(str(processing_path), str(self.ack_dir / event_file.name))
                acked += 1
            except Exception as exc:
                # Failure -> dlq with error metadata
                self._move_to_dlq(processing_path, exc)

        return acked

    def list_inbox(self) -> List[Path]:
        """Return sorted list of event files in inbox."""
        return sorted(self.inbox.glob("*.json"))

    def _move_to_dlq(self, processing_path: Path, exc: Exception) -> None:
        """Move a failed event to DLQ and write error metadata alongside."""
        dlq_path = self.dlq_dir / processing_path.name
        os.rename(str(processing_path), str(dlq_path))

        error_meta = {
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "original_file": processing_path.name,
        }
        error_file = self.dlq_dir / f"{processing_path.stem}.error.json"
        error_file.write_text(
            json.dumps(error_meta, indent=2), encoding="utf-8"
        )
