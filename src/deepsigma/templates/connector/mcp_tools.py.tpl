"""MCP tool stubs for {{ connector_class }}."""

from __future__ import annotations


def tool_list_records(arguments: dict) -> dict:
    """Stub: wire this to your connector's list_records()."""
    return {"status": "todo", "tool": "list_records", "args": arguments}


def tool_get_record(arguments: dict) -> dict:
    """Stub: wire this to your connector's get_record()."""
    return {"status": "todo", "tool": "get_record", "args": arguments}
