"""Tests for core.model_exchange.registry — adapter registration and lookup."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.model_exchange.registry import AdapterRegistry  # noqa: E402
from core.model_exchange.adapters.mock_adapter import MockAdapter  # noqa: E402
from core.model_exchange.adapters.apex_adapter import ApexAdapter  # noqa: E402
from core.model_exchange.base_adapter import BaseModelAdapter  # noqa: E402


class TestAdapterRegistry:
    def test_register_and_get(self):
        reg = AdapterRegistry()
        adapter = MockAdapter()
        reg.register("mock", adapter)
        assert reg.get("mock") is adapter

    def test_get_missing_raises(self):
        reg = AdapterRegistry()
        with pytest.raises(KeyError, match="not registered"):
            reg.get("nonexistent")

    def test_list_adapters_empty(self):
        reg = AdapterRegistry()
        assert reg.list_adapters() == []

    def test_list_adapters_sorted(self):
        reg = AdapterRegistry()
        reg.register("beta", MockAdapter())
        reg.register("alpha", ApexAdapter())
        assert reg.list_adapters() == ["alpha", "beta"]

    def test_register_overwrites(self):
        reg = AdapterRegistry()
        first = MockAdapter()
        second = MockAdapter()
        reg.register("mock", first)
        reg.register("mock", second)
        assert reg.get("mock") is second

    def test_register_rejects_non_adapter(self):
        reg = AdapterRegistry()
        with pytest.raises(TypeError, match="BaseModelAdapter"):
            reg.register("bad", "not an adapter")  # type: ignore[arg-type]

    def test_multiple_adapters(self):
        reg = AdapterRegistry()
        reg.register("apex", ApexAdapter())
        reg.register("mock", MockAdapter())
        assert len(reg.list_adapters()) == 2

    def test_get_error_message_includes_available(self):
        reg = AdapterRegistry()
        reg.register("mock", MockAdapter())
        with pytest.raises(KeyError, match="mock"):
            reg.get("missing")
