from deep_sigma_p2pc2 import AuthorityEnvelope, MissionObject, PeerNode, Scope
from deep_sigma_p2pc2.transport import InMemoryTransport


a = PeerNode("alpha")
b = PeerNode("bravo")
transport = InMemoryTransport()

for peer in (a, b):
    peer.install_authority(
        AuthorityEnvelope(
            authority_id=f"auth-{peer.peer_id}",
            issuer="HQ",
            subject=peer.peer_id,
            scopes={Scope.OBSERVE, Scope.ASSESS},
        )
    )

a.publish(MissionObject.observation(
    entity_id="track-001",
    value="UNKNOWN",
    origin_peer="alpha",
    confidence=0.55,
    authority_id="auth-alpha",
))

b.publish(MissionObject.observation(
    entity_id="track-001",
    value="FRIENDLY",
    origin_peer="bravo",
    confidence=0.72,
    authority_id="auth-bravo",
))

a.sync_to("bravo", transport)
b.sync_to("alpha", transport)
a.receive(transport)
b.receive(transport)

print("alpha conflicts:", len(a.conflicts()))
print("bravo conflicts:", len(b.conflicts()))
