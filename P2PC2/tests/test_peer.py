from deep_sigma_p2pc2 import AuthorityEnvelope, MissionObject, PeerNode, Scope
from deep_sigma_p2pc2.transport import InMemoryTransport


def install_observe(node: PeerNode):
    node.install_authority(
        AuthorityEnvelope(
            authority_id=f"auth-{node.peer_id}",
            issuer="HQ",
            subject=node.peer_id,
            scopes={Scope.OBSERVE, Scope.ASSESS},
        )
    )


def test_peer_sync_and_conflict_detection():
    a = PeerNode("a")
    b = PeerNode("b")
    install_observe(a)
    install_observe(b)

    a.publish(MissionObject.observation(entity_id="e1", value="X", origin_peer="a", authority_id="auth-a"))
    b.publish(MissionObject.observation(entity_id="e1", value="Y", origin_peer="b", authority_id="auth-b"))

    t = InMemoryTransport()
    a.sync_to("b", t)
    b.sync_to("a", t)
    a.receive(t)
    b.receive(t)

    assert a.ledger.head_sequence == 2
    assert b.ledger.head_sequence == 2
    assert len(a.conflicts()) == 1
    assert len(b.conflicts()) == 1


def test_peer_publish_requires_authority():
    a = PeerNode("a")
    obj = MissionObject.observation(entity_id="e1", value="X", origin_peer="a", authority_id="missing")
    try:
        a.publish(obj)
    except PermissionError:
        pass
    else:
        raise AssertionError("expected PermissionError")
