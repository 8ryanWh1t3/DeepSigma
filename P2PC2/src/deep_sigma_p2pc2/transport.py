from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Protocol

from .models import MissionObject


@dataclass(frozen=True, slots=True)
class DeltaPacket:
    source_peer: str
    objects: tuple[MissionObject, ...]


class Transport(Protocol):
    def send(self, source_peer: str, target_peer: str, packet: DeltaPacket) -> None: ...
    def receive(self, peer_id: str) -> tuple[DeltaPacket, ...]: ...


class InMemoryTransport:
    """Simulation transport. Replace with an accredited bearer adapter in deployment."""

    def __init__(self) -> None:
        self._queues: dict[str, deque[DeltaPacket]] = defaultdict(deque)

    def send(self, source_peer: str, target_peer: str, packet: DeltaPacket) -> None:
        if packet.source_peer != source_peer:
            raise ValueError("packet source mismatch")
        self._queues[target_peer].append(packet)

    def receive(self, peer_id: str) -> tuple[DeltaPacket, ...]:
        q = self._queues[peer_id]
        packets = tuple(q)
        q.clear()
        return packets
