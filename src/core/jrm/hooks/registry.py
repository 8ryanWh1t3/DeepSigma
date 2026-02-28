"""JRM extension hook registries.

Enterprise and custom extensions register here to add drift detectors,
packet validators, stream connectors, and CLI subcommands.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Type


# ── Drift detectors ─────────────────────────────────────────────
_DRIFT_DETECTORS: Dict[str, Type] = {}


def register_drift_detector(name: str, cls: Type) -> None:
    _DRIFT_DETECTORS[name] = cls


def get_drift_detectors() -> Dict[str, Type]:
    return dict(_DRIFT_DETECTORS)


# ── Packet validators ───────────────────────────────────────────
_PACKET_VALIDATORS: Dict[str, Callable] = {}


def register_packet_validator(name: str, fn: Callable) -> None:
    _PACKET_VALIDATORS[name] = fn


def get_packet_validators() -> Dict[str, Callable]:
    return dict(_PACKET_VALIDATORS)


# ── Stream connectors ───────────────────────────────────────────
_STREAM_CONNECTORS: Dict[str, Type] = {}


def register_stream_connector(name: str, cls: Type) -> None:
    _STREAM_CONNECTORS[name] = cls


def get_stream_connectors() -> Dict[str, Type]:
    return dict(_STREAM_CONNECTORS)


# ── CLI hooks ────────────────────────────────────────────────────
_CLI_HOOKS: List[Callable] = []


def register_cli_hook(fn: Callable) -> None:
    _CLI_HOOKS.append(fn)


def get_cli_hooks() -> List[Callable]:
    return list(_CLI_HOOKS)
