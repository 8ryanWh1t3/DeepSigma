"""JRM enterprise test fixtures."""

from __future__ import annotations

import json
import zipfile
import pytest
from pathlib import Path


@pytest.fixture
def make_packet(tmp_path):
    """Factory to create a minimal valid JRM-X packet zip."""
    def _make(
        env: str = "TEST",
        part: int = 1,
        canon_entries: dict | None = None,
        mg_nodes: list | None = None,
    ):
        packet_name = f"JRM_X_PACKET_{env}_20260228T100000_20260228T101000_part{part:02d}"
        ce = canon_entries or {}
        mg = mg_nodes or []

        files = {
            "truth_snapshot.json": json.dumps({"environmentId": env, "eventCount": 10}).encode(),
            "authority_slice.json": json.dumps({"environmentId": env}).encode(),
            "decision_lineage.jsonl": b"",
            "drift_signal.jsonl": b"",
            "memory_graph.json": json.dumps({"nodesAdded": mg, "edgesAdded": []}).encode(),
            "canon_entry.json": json.dumps({"entries": ce, "environmentId": env}).encode(),
        }

        import hashlib
        file_hashes = {
            name: f"sha256:{hashlib.sha256(content).hexdigest()}"
            for name, content in files.items()
        }

        manifest = {
            "packetName": packet_name,
            "environmentId": env,
            "windowStart": "2026-02-28T10:00:00Z",
            "windowEnd": "2026-02-28T10:10:00Z",
            "part": part,
            "files": file_hashes,
            "eventCount": 10,
            "sizeBytes": sum(len(v) for v in files.values()),
            "createdAt": "2026-02-28T10:10:01Z",
        }

        zip_path = tmp_path / f"{packet_name}.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for name, content in files.items():
                zf.writestr(name, content)
            zf.writestr("manifest.json", json.dumps(manifest, indent=2).encode())

        return zip_path

    return _make
