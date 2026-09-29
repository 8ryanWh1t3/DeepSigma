from __future__ import annotations

from dataclasses import dataclass

from .authority import AuthorityEngine
from .cerpa import CerpaEngine
from .ledger import EventLedger
from .models import AuthorityEnvelope, MissionObject, MissionObjectKind, Scope
from .reconcile import Conflict, Reconciler
from .storage import SQLiteStore
from .transport import DeltaPacket, Transport
from .world import WorldModel


@dataclass(frozen=True, slots=True)
class SyncStatus:
    sent: int = 0
    received: int = 0
    conflicts: int = 0


class PeerNode:
    """Offline-first peer runtime.

    A PeerNode can ingest and reason over local mission state without a central
    service. Authority is checked locally from previously installed envelopes.
    """

    def __init__(self, peer_id: str, *, store: SQLiteStore | None = None) -> None:
        self.peer_id = peer_id
        self.authority = AuthorityEngine()
        self.ledger = EventLedger()
        self.world = WorldModel()
        self.reconciler = Reconciler()
        self.cerpa = CerpaEngine(self.authority)
        self.store = store
        if store:
            self._ingest_many(store.load_all(), persist=False)

    def install_authority(self, envelope: AuthorityEnvelope) -> None:
        self.authority.install(envelope)

    def publish(self, obj: MissionObject) -> MissionObject:
        required = {
            MissionObjectKind.OBSERVATION: Scope.OBSERVE,
            MissionObjectKind.ASSESSMENT: Scope.ASSESS,
            MissionObjectKind.DECISION: Scope.PROPOSE,
            MissionObjectKind.PATCH: Scope.APPLY,
        }.get(obj.kind)
        if obj.origin_peer != self.peer_id:
            raise PermissionError("peer may publish only objects it originates")
        if required is not None:
            decision = self.authority.decide(
                subject=self.peer_id,
                authority_id=obj.authority_id,
                required_scope=required,
                context={"entity_id": obj.entity_id, "field": obj.field},
            )
            if not decision.allowed:
                raise PermissionError(decision.reason)
        self._ingest(obj)
        return obj

    def _ingest(self, obj: MissionObject, *, persist: bool = True) -> None:
        self.ledger.append(obj)
        self.world.ingest(obj)
        if persist and self.store:
            self.store.put(obj)

    def _ingest_many(self, objects, *, persist: bool = True) -> None:
        for obj in objects:
            self._ingest(obj, persist=persist)

    def export_delta(self, after_sequence: int = 0) -> DeltaPacket:
        return DeltaPacket(self.peer_id, self.ledger.after(after_sequence))

    def merge_delta(self, packet: DeltaPacket) -> SyncStatus:
        received = 0
        for obj in packet.objects:
            if not self.ledger.contains(obj.object_id):
                self._ingest(obj)
                received += 1
        conflicts = len(self.reconciler.detect(self.world))
        return SyncStatus(received=received, conflicts=conflicts)

    def sync_to(self, target_peer: str, transport: Transport, *, after_sequence: int = 0) -> SyncStatus:
        packet = self.export_delta(after_sequence)
        transport.send(self.peer_id, target_peer, packet)
        return SyncStatus(sent=len(packet.objects))

    def receive(self, transport: Transport) -> SyncStatus:
        received = 0
        for packet in transport.receive(self.peer_id):
            received += self.merge_delta(packet).received
        return SyncStatus(received=received, conflicts=len(self.conflicts()))

    def conflicts(self) -> tuple[Conflict, ...]:
        return self.reconciler.detect(self.world)
