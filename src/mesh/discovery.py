"""Mesh Discovery — Static peer registry for distributed mesh nodes.

Provides a StaticRegistry that maps node IDs to network addresses.
Used by HTTPTransport to route push/pull requests to the correct host.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class StaticRegistry:
    """Static peer registry backed by a config dict or YAML file.

    Registry format::

        {
            "edge-A": {"url": "http://host1:8100", "role": "edge", "region": "region-A"},
            "validator-B": {"url": "http://host2:8101", "role": "validator", "region": "region-B"},
        }

    Parameters
    ----------
    peers : dict[str, dict], optional
        Peer configuration dict. If not provided, load from ``config_path``.
    config_path : str or Path, optional
        Path to a YAML file containing the peer registry.
    """

    def __init__(
        self,
        peers: dict[str, dict[str, str]] | None = None,
        config_path: str | Path | None = None,
    ) -> None:
        if peers is not None:
            self._peers = dict(peers)
        elif config_path is not None:
            self._peers = self._load_yaml(Path(config_path))
        else:
            self._peers = {}

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, dict[str, str]]:
        """Load peer registry from a YAML file."""
        import yaml

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        # Support both flat {"node": {"url": ...}} and nested {"peers": {"node": ...}}
        if "peers" in data and isinstance(data["peers"], dict):
            return data["peers"]
        return data

    def get_peer_url(self, node_id: str) -> str | None:
        """Return the base URL for a peer node, or None if unknown."""
        entry = self._peers.get(node_id)
        if entry is None:
            return None
        if isinstance(entry, str):
            return entry
        return entry.get("url")

    def list_peers(self) -> list[dict[str, Any]]:
        """Return all peers as a list of dicts with node_id included."""
        result = []
        for node_id, entry in self._peers.items():
            if isinstance(entry, str):
                result.append({"node_id": node_id, "url": entry})
            else:
                result.append({"node_id": node_id, **entry})
        return result

    def to_peer_map(self) -> dict[str, str]:
        """Return a simplified {node_id: url} dict for HTTPTransport."""
        return {
            node_id: (entry if isinstance(entry, str) else entry.get("url", ""))
            for node_id, entry in self._peers.items()
        }

    def add_peer(self, node_id: str, url: str, **metadata: str) -> None:
        """Register a new peer."""
        self._peers[node_id] = {"url": url, **metadata}

    def remove_peer(self, node_id: str) -> bool:
        """Remove a peer. Returns True if the peer existed."""
        return self._peers.pop(node_id, None) is not None

    def __len__(self) -> int:
        return len(self._peers)

    def __contains__(self, node_id: str) -> bool:
        return node_id in self._peers
