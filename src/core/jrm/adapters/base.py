"""Base adapter interface for JRM event sources."""

from __future__ import annotations

import abc
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Iterator

from ..types import EventType, JRMEvent, Severity


class AdapterBase(abc.ABC):
    """Abstract adapter: parse raw input, emit normalized JRMEvent objects.

    Subclasses must implement ``parse_line``.  The base class provides
    ``parse_stream`` (iterate lines and yield events), ``hash_raw``
    (sha256 of raw bytes), and ``_make_malformed`` (wrap unparseable
    lines as MALFORMED events).
    """

    source_system: str = "unknown"
    default_environment_id: str = "default"

    @abc.abstractmethod
    def parse_line(self, line: str, line_number: int = 0) -> JRMEvent | None:
        """Parse a single line into a JRMEvent.

        Return ``None`` only when the line is blank/empty.
        For malformed input, use ``_make_malformed`` to preserve the raw data.
        """
        ...

    def parse_stream(
        self,
        lines: Iterator[str],
        environment_id: str | None = None,
    ) -> Iterator[JRMEvent]:
        """Parse a stream of lines, yielding JRMEvents."""
        env = environment_id or self.default_environment_id
        for i, line in enumerate(lines):
            line = line.rstrip("\n\r")
            if not line:
                continue
            event = self.parse_line(line, line_number=i)
            if event is not None:
                if event.environment_id == "default" and env != "default":
                    event.environment_id = env
                yield event

    @staticmethod
    def hash_raw(raw: str | bytes) -> str:
        """SHA-256 hash of raw input in ``sha256:<hex>`` format."""
        data = raw.encode("utf-8") if isinstance(raw, str) else raw
        return f"sha256:{hashlib.sha256(data).hexdigest()}"

    @staticmethod
    def _generate_event_id(prefix: str = "JRM") -> str:
        return f"{prefix}-{uuid.uuid4().hex[:12]}"

    def _make_malformed(
        self,
        line: str,
        line_number: int,
        error: str = "",
    ) -> JRMEvent:
        """Wrap an unparseable line as a MALFORMED event (lossless)."""
        raw_hash = self.hash_raw(line)
        return JRMEvent(
            event_id=self._generate_event_id("MAL"),
            source_system=self.source_system,
            event_type=EventType.MALFORMED,
            timestamp=datetime.now(timezone.utc).isoformat(),
            severity=Severity.INFO,
            actor={"type": "unknown", "id": "unknown"},
            object={"type": "raw_line", "id": f"line:{line_number}"},
            action="malformed_parse",
            confidence=0.0,
            evidence_hash=raw_hash,
            raw_pointer=f"inline:{raw_hash}",
            environment_id=self.default_environment_id,
            assumptions=[],
            raw_bytes=line.encode("utf-8", errors="replace"),
            metadata={"parse_error": error, "line_number": line_number},
        )
