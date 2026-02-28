"""FEEDS event contracts — routing table and contract validation."""

from __future__ import annotations

from .loader import load_routing_table, RoutingTable

__all__ = ["RoutingTable", "load_routing_table"]
