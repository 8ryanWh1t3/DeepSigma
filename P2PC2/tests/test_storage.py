from pathlib import Path

from deep_sigma_p2pc2 import AuthorityEnvelope, MissionObject, PeerNode, SQLiteStore, Scope


def test_sqlite_roundtrip(tmp_path: Path):
    db = tmp_path / "peer.sqlite"
    store = SQLiteStore(db)
    peer = PeerNode("a", store=store)
    peer.install_authority(AuthorityEnvelope(authority_id="auth-a", issuer="HQ", subject="a", scopes={Scope.OBSERVE}))
    peer.publish(MissionObject.observation(entity_id="e", value="X", origin_peer="a", authority_id="auth-a"))
    store.close()

    store2 = SQLiteStore(db)
    restored = PeerNode("a", store=store2)
    assert restored.world.current("e") == "X"
    store2.close()
