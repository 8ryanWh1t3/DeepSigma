"""JRM extension hooks — registries for enterprise and custom extensions."""

from __future__ import annotations

from .registry import (
    get_cli_hooks,
    get_drift_detectors,
    get_packet_validators,
    get_stream_connectors,
    register_cli_hook,
    register_drift_detector,
    register_packet_validator,
    register_stream_connector,
)

__all__ = [
    "get_cli_hooks",
    "get_drift_detectors",
    "get_packet_validators",
    "get_stream_connectors",
    "register_cli_hook",
    "register_drift_detector",
    "register_packet_validator",
    "register_stream_connector",
]
