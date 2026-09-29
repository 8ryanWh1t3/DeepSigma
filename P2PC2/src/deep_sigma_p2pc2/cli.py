from __future__ import annotations

import argparse
import json

from .models import AuthorityEnvelope, MissionObject, Scope
from .peer import PeerNode
from .transport import InMemoryTransport


def demo() -> dict:
    a = PeerNode("peer-a")
    b = PeerNode("peer-b")
    transport = InMemoryTransport()

    for node in (a, b):
        node.install_authority(
            AuthorityEnvelope(
                authority_id=f"auth-{node.peer_id}",
                issuer="HQ",
                subject=node.peer_id,
                scopes={Scope.OBSERVE, Scope.ASSESS},
            )
        )

    a.publish(
        MissionObject.observation(
            entity_id="entity-7",
            value="UNKNOWN",
            origin_peer="peer-a",
            confidence=0.60,
            authority_id="auth-peer-a",
        )
    )
    b.publish(
        MissionObject.observation(
            entity_id="entity-7",
            value="FRIENDLY",
            origin_peer="peer-b",
            confidence=0.80,
            authority_id="auth-peer-b",
        )
    )

    a.sync_to("peer-b", transport)
    b.sync_to("peer-a", transport)
    a.receive(transport)
    b.receive(transport)

    return {
        "peer_a_objects": a.ledger.head_sequence,
        "peer_b_objects": b.ledger.head_sequence,
        "peer_a_conflicts": len(a.conflicts()),
        "peer_b_conflicts": len(b.conflicts()),
        "peer_a_current": a.world.current("entity-7"),
        "peer_b_current": b.world.current("entity-7"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(prog="ds-p2pc2")
    parser.add_argument("command", choices=["demo"])
    args = parser.parse_args()
    if args.command == "demo":
        print(json.dumps(demo(), indent=2))


if __name__ == "__main__":
    main()
