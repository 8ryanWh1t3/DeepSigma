"""Adapter registry — discover and register JRM adapters."""

from __future__ import annotations

from typing import Dict, List, Type

from .base import AdapterBase

_ADAPTERS: Dict[str, Type[AdapterBase]] = {}


def register_adapter(name: str, cls: Type[AdapterBase]) -> None:
    """Register an adapter class under a given name."""
    _ADAPTERS[name] = cls


def get_adapter(name: str) -> Type[AdapterBase]:
    """Look up an adapter class by name.  Raises KeyError if not found."""
    if name not in _ADAPTERS:
        raise KeyError(
            f"Unknown adapter: {name!r}. Available: {sorted(_ADAPTERS)}"
        )
    return _ADAPTERS[name]


def list_adapters() -> List[str]:
    """Return sorted list of registered adapter names."""
    return sorted(_ADAPTERS.keys())


# ── Auto-register built-in adapters ─────────────────────────────

def _auto_register() -> None:
    from .suricata_eve import SuricataEVEAdapter
    from .snort_fastlog import SnortFastlogAdapter
    from .copilot_agent import CopilotAgentAdapter

    register_adapter("suricata_eve", SuricataEVEAdapter)
    register_adapter("snort_fastlog", SnortFastlogAdapter)
    register_adapter("copilot_agent", CopilotAgentAdapter)


_auto_register()
