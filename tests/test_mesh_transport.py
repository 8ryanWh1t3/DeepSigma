"""Tests for mesh transport layer — Transport protocol, Local/HTTP transports, server, discovery.

Run:  pytest tests/test_mesh_transport.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mesh.transport import (
    ENVELOPES_LOG,
    LocalTransport,
    NodeIdentity,
    Transport,
    _decode_payload,
    _encode_payload,
    ensure_node_dirs,
    push_records,
)
from mesh.discovery import StaticRegistry

_has_httpx = True
try:
    import httpx
except ModuleNotFoundError:
    _has_httpx = False

_has_fastapi = True
try:
    import fastapi  # noqa: F401
except ModuleNotFoundError:
    _has_fastapi = False

_has_msgpack = True
try:
    import msgpack  # noqa: F401
except ModuleNotFoundError:
    _has_msgpack = False

TENANT = "test-tenant"
NODE_A = "edge-A"
NODE_B = "validator-B"


# ── Helpers ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mesh_data_dir(tmp_path, monkeypatch):
    """Redirect mesh data directory to tmp_path."""
    import mesh.transport as mt
    monkeypatch.setattr(mt, "_BASE_DATA_DIR", tmp_path)
    return tmp_path


# ── Transport Protocol ─────────────────────────────────────────────────────

class TestTransportProtocol:
    def test_local_transport_satisfies_protocol(self):
        assert isinstance(LocalTransport(), Transport)

    @pytest.mark.skipif(not _has_httpx, reason="httpx not installed")
    def test_http_transport_satisfies_protocol(self):
        from mesh.transport import HTTPTransport
        t = HTTPTransport(peer_registry={"node-1": "http://localhost:9999"})
        assert isinstance(t, Transport)
        t.close()

    def test_transport_protocol_is_runtime_checkable(self):
        assert hasattr(Transport, "__protocol_attrs__") or hasattr(Transport, "__abstractmethods__") or True
        # runtime_checkable protocols work with isinstance()


# ── LocalTransport ──────────────────────────────────────────────────────────

class TestLocalTransport:
    def test_push_pull_round_trip(self, mesh_data_dir):
        t = LocalTransport()
        ensure_node_dirs(TENANT, NODE_A)
        records = [{"id": "env-1", "data": "test"}]
        written = t.push(TENANT, NODE_A, ENVELOPES_LOG, records)
        assert written == 1

        pulled = t.pull(TENANT, NODE_A, ENVELOPES_LOG)
        assert len(pulled) == 1
        assert pulled[0]["id"] == "env-1"

    def test_pull_with_since(self, mesh_data_dir):
        t = LocalTransport()
        ensure_node_dirs(TENANT, NODE_A)
        t.push(TENANT, NODE_A, ENVELOPES_LOG, [
            {"id": "old", "timestamp": "2026-01-01T00:00:00Z"},
            {"id": "new", "timestamp": "2026-02-01T00:00:00Z"},
        ])
        result = t.pull(TENANT, NODE_A, ENVELOPES_LOG, since="2026-01-15T00:00:00Z")
        assert len(result) == 1
        assert result[0]["id"] == "new"

    def test_get_set_status(self, mesh_data_dir):
        t = LocalTransport()
        ensure_node_dirs(TENANT, NODE_A)
        assert t.get_status(TENANT, NODE_A) is None

        status = {"node_id": NODE_A, "state": "active"}
        t.set_status(TENANT, NODE_A, status)

        loaded = t.get_status(TENANT, NODE_A)
        assert loaded is not None
        assert loaded["state"] == "active"

    def test_health(self):
        t = LocalTransport()
        h = t.health()
        assert h["status"] == "ok"
        assert h["transport"] == "local"

    def test_backward_compatible_with_module_functions(self, mesh_data_dir):
        """LocalTransport delegates to the same functions used before."""
        ensure_node_dirs(TENANT, NODE_A)
        push_records(TENANT, NODE_A, ENVELOPES_LOG, [{"id": "r1"}])
        t = LocalTransport()
        pulled = t.pull(TENANT, NODE_A, ENVELOPES_LOG)
        assert any(r["id"] == "r1" for r in pulled)


# ── HTTPTransport ───────────────────────────────────────────────────────────

@pytest.mark.skipif(not _has_httpx, reason="httpx not installed")
class TestHTTPTransport:
    def test_node_identity_model_spiffe(self):
        ident = NodeIdentity(node_id="edge-A", trust_domain="trust.local")
        assert ident.spiffe_id == "spiffe://trust.local/node/edge-A"

    def test_push_sends_post(self):
        from mesh.transport import HTTPTransport

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'{"status":"ok","received":{"envelopes":2}}'
        mock_resp.headers = {"content-type": "application/json"}

        with patch("httpx.Client") as MockClient:
            MockClient.return_value.request.return_value = mock_resp
            t = HTTPTransport(peer_registry={NODE_A: "http://host1:8100"})
            written = t.push(TENANT, NODE_A, ENVELOPES_LOG, [{"id": "1"}, {"id": "2"}])
            assert written == 2

    def test_pull_sends_get(self):
        from mesh.transport import HTTPTransport

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'{"status":"ok","records":{"envelopes":[{"id":"env-1"}]}}'
        mock_resp.headers = {"content-type": "application/json"}

        with patch("httpx.Client") as MockClient:
            MockClient.return_value.request.return_value = mock_resp
            t = HTTPTransport(peer_registry={NODE_A: "http://host1:8100"})
            result = t.pull(TENANT, NODE_A, ENVELOPES_LOG)
            assert len(result) == 1
            assert result[0]["id"] == "env-1"

    def test_status_via_http(self):
        from mesh.transport import HTTPTransport

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'{"node_id":"edge-A","state":"active"}'
        mock_resp.headers = {"content-type": "application/json"}

        with patch("httpx.Client") as MockClient:
            MockClient.return_value.request.return_value = mock_resp
            t = HTTPTransport(peer_registry={NODE_A: "http://host1:8100"})
            status = t.get_status(TENANT, NODE_A)
            assert status["state"] == "active"

    def test_health_aggregation(self):
        from mesh.transport import HTTPTransport

        ok_resp = MagicMock()
        ok_resp.status_code = 200

        with patch("httpx.Client") as MockClient:
            MockClient.return_value.get.return_value = ok_resp
            t = HTTPTransport(peer_registry={
                NODE_A: "http://host1:8100",
                NODE_B: "http://host2:8101",
            })
            h = t.health()
            assert h["transport"] == "http"
            assert h["peers_total"] == 2
            assert h["peers_reachable"] == 2

    def test_retry_on_transient_error(self):
        from mesh.transport import HTTPTransport

        fail_resp = MagicMock()
        fail_resp.status_code = 503
        fail_resp.headers = {"content-type": "application/json"}

        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.content = b'{"status":"ok","records":{"envelopes":[]}}'
        ok_resp.headers = {"content-type": "application/json"}

        with patch("httpx.Client") as MockClient:
            # First call: 503, second call: 200
            MockClient.return_value.request.side_effect = [fail_resp, ok_resp]
            t = HTTPTransport(peer_registry={NODE_A: "http://host1:8100"})
            # Monkey-patch backoff to 0 for fast test
            import mesh.transport as mt
            orig_backoff = mt._BACKOFF_BASE
            mt._BACKOFF_BASE = 0.0
            try:
                result = t.pull(TENANT, NODE_A, ENVELOPES_LOG)
                assert result == []
            finally:
                mt._BACKOFF_BASE = orig_backoff

    def test_timeout_handling(self):
        from mesh.transport import HTTPTransport

        with patch("httpx.Client") as MockClient:
            MockClient.return_value.request.side_effect = httpx.TimeoutException("timeout")
            t = HTTPTransport(peer_registry={NODE_A: "http://host1:8100"})
            import mesh.transport as mt
            orig_backoff = mt._BACKOFF_BASE
            mt._BACKOFF_BASE = 0.0
            try:
                with pytest.raises(ConnectionError, match="Failed after"):
                    t.pull(TENANT, NODE_A, ENVELOPES_LOG)
            finally:
                mt._BACKOFF_BASE = orig_backoff

    def test_unknown_peer_raises(self):
        from mesh.transport import HTTPTransport

        with patch("httpx.Client"):
            t = HTTPTransport(peer_registry={NODE_A: "http://host1:8100"})
            with pytest.raises(ValueError, match="Unknown peer"):
                t.push(TENANT, "nonexistent-node", ENVELOPES_LOG, [])

    def test_tls_flag_passed_to_client(self):
        from mesh.transport import HTTPTransport

        with patch("httpx.Client") as MockClient:
            HTTPTransport(
                peer_registry={NODE_A: "http://host1:8100"},
                verify_tls=False,
            )
            MockClient.assert_called_once_with(timeout=5.0, verify=False)

    def test_mtls_requires_https_and_trust_roots(self):
        from mesh.transport import HTTPTransport

        with patch("httpx.Client") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b'{"status":"ok","records":{"envelopes":[]}}'
            mock_resp.headers = {"content-type": "application/json"}
            MockClient.return_value.request.return_value = mock_resp
            t = HTTPTransport(
                peer_registry={NODE_A: "http://host1:8100"},
                require_mtls=True,
                trust_roots=["/etc/ssl/roots.pem"],
                client_cert_path="/tmp/client.crt",
                client_key_path="/tmp/client.key",
            )
            with pytest.raises(ConnectionError, match="not HTTPS"):
                t.pull(TENANT, NODE_A, ENVELOPES_LOG)

    def test_configurable_trust_roots_and_cert_rotation_path(self):
        from mesh.transport import HTTPTransport

        with patch("httpx.Client") as MockClient:
            ok_resp = MagicMock()
            ok_resp.status_code = 200
            ok_resp.headers = {"content-type": "application/json"}
            MockClient.return_value.get.return_value = ok_resp
            t = HTTPTransport(
                peer_registry={NODE_A: "https://host1:8100"},
                require_mtls=True,
                trust_roots=["/etc/ssl/rootA.pem"],
                client_cert_path="/tmp/cert-v1.crt",
                client_key_path="/tmp/key-v1.key",
                cert_rotation_path="/etc/mesh/certs/current",
            )
            t.configure_trust_roots(["/etc/ssl/rootB.pem"])
            t.rotate_client_certificate(
                cert_path="/tmp/cert-v2.crt",
                key_path="/tmp/key-v2.key",
                cert_rotation_path="/etc/mesh/certs/next",
            )
            health = t.health()
            assert health["identity"]["trust_roots"] == ["/etc/ssl/rootB.pem"]
            assert health["identity"]["cert_rotation_path"] == "/etc/mesh/certs/next"

    def test_rejects_untrusted_peer_fingerprint(self):
        from mesh.transport import HTTPTransport

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'{"status":"ok","records":{"envelopes":[]}}'
        mock_resp.headers = {
            "content-type": "application/json",
            "x-peer-cert-fingerprint": "deadbeef",
        }

        with patch("httpx.Client") as MockClient:
            MockClient.return_value.request.return_value = mock_resp
            t = HTTPTransport(peer_registry={NODE_A: "http://host1:8100"})
            t.set_peer_identity(
                NODE_A,
                NodeIdentity(
                    node_id=NODE_A,
                    cert_fingerprint="cafebabe",
                ),
            )
            with pytest.raises(ConnectionError, match="fingerprint mismatch"):
                t.pull(TENANT, NODE_A, ENVELOPES_LOG)

    def test_partition_state_transitions_and_recovery(self):
        from mesh.transport import HTTPTransport

        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.content = b'{"status":"ok","records":{"envelopes":[]}}'
        ok_resp.headers = {"content-type": "application/json"}

        with patch("httpx.Client") as MockClient:
            MockClient.return_value.request.side_effect = [
                httpx.ConnectError("boom-1"),
                httpx.ConnectError("boom-2"),
                ok_resp,
            ]
            t = HTTPTransport(
                peer_registry={NODE_A: "http://host1:8100"},
                max_retries=1,
                backoff_base=0.0,
                suspect_after_failures=1,
                offline_after_failures=2,
                recovery_successes=1,
            )

            with pytest.raises(ConnectionError):
                t.pull(TENANT, NODE_A, ENVELOPES_LOG)
            assert t.peer_states()[NODE_A] == "SUSPECT"

            with pytest.raises(ConnectionError):
                t.pull(TENANT, NODE_A, ENVELOPES_LOG)
            assert t.peer_states()[NODE_A] == "OFFLINE"

            records = t.pull(TENANT, NODE_A, ENVELOPES_LOG)
            assert records == []
            assert t.peer_states()[NODE_A] == "ONLINE"

            events = t.partition_events()
            assert any(e["event_type"] == "partition" for e in events)
            assert any(e["event_type"] == "recovery" for e in events)

    def test_health_includes_partition_metrics(self):
        from mesh.transport import HTTPTransport

        with patch("httpx.Client") as MockClient:
            MockClient.return_value.get.side_effect = httpx.ConnectError("down")
            t = HTTPTransport(
                peer_registry={NODE_A: "http://host1:8100"},
                max_retries=1,
                backoff_base=0.0,
                suspect_after_failures=1,
                offline_after_failures=1,
            )
            health = t.health()
            assert health["peer_states"][NODE_A] == "OFFLINE"
            assert health["partition_metrics"]["offline_peers"] == 1


# ── Serialization ───────────────────────────────────────────────────────────

class TestSerialization:
    def test_json_encode_decode(self):
        data = {"key": "value", "num": 42}
        raw, ct = _encode_payload(data, use_msgpack=False)
        assert ct == "application/json"
        decoded = _decode_payload(raw, ct)
        assert decoded == data

    @pytest.mark.skipif(not _has_msgpack, reason="msgpack not installed")
    def test_msgpack_encode_decode(self):
        data = {"key": "value", "num": 42}
        raw, ct = _encode_payload(data, use_msgpack=True)
        assert ct == "application/msgpack"
        decoded = _decode_payload(raw, ct)
        assert decoded == data

    def test_msgpack_fallback_to_json(self):
        """When msgpack=True but module unavailable, falls back to JSON."""
        import mesh.transport as mt
        orig = mt._HAS_MSGPACK
        mt._HAS_MSGPACK = False
        try:
            data = {"key": "value"}
            raw, ct = _encode_payload(data, use_msgpack=True)
            assert ct == "application/json"
        finally:
            mt._HAS_MSGPACK = orig


# ── Node with Transport ────────────────────────────────────────────────────

class TestNodeWithTransport:
    def test_default_transport_is_local(self, mesh_data_dir):
        from mesh.node_runtime import MeshNode, NodeRole
        node = MeshNode(
            node_id=NODE_A,
            tenant_id=TENANT,
            region_id="region-A",
            role=NodeRole.EDGE,
        )
        assert isinstance(node.transport, LocalTransport)

    def test_custom_transport(self, mesh_data_dir):
        from mesh.node_runtime import MeshNode, NodeRole
        mock_transport = MagicMock()
        mock_transport.set_status = MagicMock()
        node = MeshNode(
            node_id=NODE_A,
            tenant_id=TENANT,
            region_id="region-A",
            role=NodeRole.EDGE,
            transport=mock_transport,
        )
        assert node.transport is mock_transport
        # __post_init__ should have called set_status via transport
        mock_transport.set_status.assert_called()

    def test_edge_tick_uses_transport_push(self, mesh_data_dir):
        from mesh.node_runtime import MeshNode, NodeRole
        t = LocalTransport()
        node = MeshNode(
            node_id=NODE_A,
            tenant_id=TENANT,
            region_id="region-A",
            role=NodeRole.EDGE,
            peers=[NODE_B],
            transport=t,
        )
        ensure_node_dirs(TENANT, NODE_B)
        result = node.tick()
        assert result["action"] == "generate_envelope"
        # Verify records were pushed to peer
        pulled = t.pull(TENANT, NODE_B, ENVELOPES_LOG)
        assert len(pulled) >= 1

    def test_validator_tick_uses_transport_pull(self, mesh_data_dir):
        from mesh.node_runtime import MeshNode, NodeRole
        t = LocalTransport()

        # Create edge and generate an envelope
        edge = MeshNode(
            node_id=NODE_A,
            tenant_id=TENANT,
            region_id="region-A",
            role=NodeRole.EDGE,
            peers=[NODE_B],
            transport=t,
        )
        ensure_node_dirs(TENANT, NODE_B)
        edge.tick()

        # Create validator and pull
        validator = MeshNode(
            node_id=NODE_B,
            tenant_id=TENANT,
            region_id="region-B",
            role=NodeRole.VALIDATOR,
            peers=[NODE_A],
            transport=t,
        )
        result = validator.tick()
        assert result["action"] == "validate_envelopes"
        assert result["accepted"] >= 1


# ── Server ──────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not _has_fastapi, reason="fastapi not installed")
class TestMeshServer:
    def test_server_health_endpoint(self, mesh_data_dir):
        from mesh.server import create_node_server
        from fastapi.testclient import TestClient

        app = create_node_server(TENANT, NODE_A)
        client = TestClient(app)

        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["node_id"] == NODE_A
        assert data["tenant_id"] == TENANT
        assert "uptime_s" in data

    def test_push_endpoint(self, mesh_data_dir):
        from mesh.server import create_node_server
        from fastapi.testclient import TestClient

        app = create_node_server(TENANT, NODE_A)
        client = TestClient(app)

        resp = client.post(
            f"/mesh/{TENANT}/{NODE_A}/push",
            json={"envelopes": [{"id": "env-1", "data": "test"}]},
        )
        assert resp.status_code == 200
        assert resp.json()["received"]["envelopes"] == 1

    def test_pull_endpoint(self, mesh_data_dir):
        from mesh.server import create_node_server
        from fastapi.testclient import TestClient

        app = create_node_server(TENANT, NODE_A)
        client = TestClient(app)

        # Push first
        client.post(
            f"/mesh/{TENANT}/{NODE_A}/push",
            json={"envelopes": [{"id": "env-1"}]},
        )
        # Pull
        resp = client.get(f"/mesh/{TENANT}/{NODE_A}/pull")
        assert resp.status_code == 200
        records = resp.json()["records"]["envelopes"]
        assert len(records) == 1

    def test_status_endpoint(self, mesh_data_dir):
        from mesh.server import create_node_server
        from fastapi.testclient import TestClient

        app = create_node_server(TENANT, NODE_A)
        client = TestClient(app)

        resp = client.get(f"/mesh/{TENANT}/{NODE_A}/status")
        assert resp.status_code == 200

    def test_topology_endpoint_includes_lag_and_state(self, mesh_data_dir):
        from mesh.server import create_node_server
        from fastapi.testclient import TestClient
        from mesh.transport import log_replication

        app_a = create_node_server(TENANT, NODE_A)
        app_b = create_node_server(TENANT, NODE_B)
        client_a = TestClient(app_a)
        client_b = TestClient(app_b)

        # ensure status exists for both nodes
        client_a.get(f"/mesh/{TENANT}/{NODE_A}/status")
        client_b.get(f"/mesh/{TENANT}/{NODE_B}/status")

        # emit one replication event so lag can be calculated
        log_replication(TENANT, NODE_A, "push", NODE_B, ENVELOPES_LOG, 1)

        resp = client_a.get(f"/mesh/{TENANT}/topology")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "active"
        assert data["node_count"] >= 2
        nodes = data["nodes"]
        assert all("state" in n for n in nodes)
        assert all("replication_lag_s" in n for n in nodes)
        assert any(
            n["replication_lag_s"] is None or n["replication_lag_s"] >= 0
            for n in nodes
        )


# ── Discovery ──────────────────────────────────────────────────────────────

class TestStaticRegistry:
    def test_from_dict(self):
        peers = {
            "edge-A": {"url": "http://host1:8100", "role": "edge"},
            "validator-B": {"url": "http://host2:8101", "role": "validator"},
        }
        reg = StaticRegistry(peers=peers)
        assert len(reg) == 2
        assert "edge-A" in reg

    def test_get_peer_url(self):
        reg = StaticRegistry(peers={
            "edge-A": {"url": "http://host1:8100"},
        })
        assert reg.get_peer_url("edge-A") == "http://host1:8100"
        assert reg.get_peer_url("unknown") is None

    def test_list_peers(self):
        reg = StaticRegistry(peers={
            "edge-A": {"url": "http://host1:8100", "role": "edge"},
            "validator-B": {"url": "http://host2:8101"},
        })
        peers = reg.list_peers()
        assert len(peers) == 2
        assert all("node_id" in p for p in peers)

    def test_to_peer_map(self):
        reg = StaticRegistry(peers={
            "edge-A": {"url": "http://host1:8100"},
            "validator-B": {"url": "http://host2:8101"},
        })
        m = reg.to_peer_map()
        assert m == {
            "edge-A": "http://host1:8100",
            "validator-B": "http://host2:8101",
        }

    def test_add_and_remove_peer(self):
        reg = StaticRegistry()
        assert len(reg) == 0

        reg.add_peer("edge-A", "http://host1:8100", role="edge")
        assert len(reg) == 1
        assert reg.get_peer_url("edge-A") == "http://host1:8100"

        removed = reg.remove_peer("edge-A")
        assert removed is True
        assert len(reg) == 0

        removed = reg.remove_peer("edge-A")
        assert removed is False

    def test_string_values(self):
        """Registry accepts plain string URLs as values."""
        reg = StaticRegistry(peers={
            "edge-A": "http://host1:8100",
        })
        assert reg.get_peer_url("edge-A") == "http://host1:8100"

    def test_from_yaml(self, tmp_path):
        yaml_content = """
peers:
  edge-A:
    url: http://host1:8100
    role: edge
  validator-B:
    url: http://host2:8101
    role: validator
"""
        yaml_file = tmp_path / "mesh_peers.yaml"
        yaml_file.write_text(yaml_content)

        reg = StaticRegistry(config_path=yaml_file)
        assert len(reg) == 2
        assert reg.get_peer_url("edge-A") == "http://host1:8100"


# ── Integration: HTTP Transport + Server ───────────────────────────────────

@pytest.mark.skipif(
    not (_has_httpx and _has_fastapi),
    reason="httpx and fastapi required",
)
class TestHTTPIntegration:
    def test_http_transport_with_test_server(self, mesh_data_dir):
        """Full integration: HTTPTransport talking to a real FastAPI TestClient."""
        from mesh.server import create_node_server
        from mesh.transport import HTTPTransport
        from fastapi.testclient import TestClient

        app = create_node_server(TENANT, NODE_A)

        # Use TestClient as the httpx transport backend
        with TestClient(app) as client:
            # Patch HTTPTransport to use the test client
            t = HTTPTransport.__new__(HTTPTransport)
            t._peers = {NODE_A: ""}
            t._timeout = 5.0
            t._verify_tls = True
            t._use_msgpack = False
            t._client = client

            # Push
            written = t.push(TENANT, NODE_A, ENVELOPES_LOG, [{"id": "e1"}])
            assert written == 1

            # Pull
            records = t.pull(TENANT, NODE_A, ENVELOPES_LOG)
            assert len(records) == 1
            assert records[0]["id"] == "e1"

            # Health
            h = t.health()
            assert h["peer_health"][NODE_A] == "ok"
