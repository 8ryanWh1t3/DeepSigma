from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ..models import SemanticPacket, Transcript


@dataclass(slots=True, frozen=True)
class AudioSource:
    path: Path
    source_id: str
    language: str = "en"


class ASRAdapter(Protocol):
    def transcribe(self, source: AudioSource) -> Transcript:
        """Convert audio to a transcript while preserving speaker/time provenance."""


class SemanticExtractor(Protocol):
    def extract(self, transcript: Transcript) -> SemanticPacket:
        """Convert a transcript into candidate semantic objects."""


class PacketPostProcessor(Protocol):
    def process(self, packet: SemanticPacket) -> SemanticPacket:
        """Apply deterministic downstream enrichment without changing source evidence."""
