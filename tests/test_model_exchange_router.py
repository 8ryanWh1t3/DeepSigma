"""Tests for core.model_exchange.router — packet routing to adapters."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.model_exchange.registry import AdapterRegistry  # noqa: E402
from core.model_exchange.router import AdapterRouter  # noqa: E402
from core.model_exchange.adapters.mock_adapter import MockAdapter  # noqa: E402
from core.model_exchange.adapters.apex_adapter import ApexAdapter  # noqa: E402
from core.model_exchange.models import ReasoningResult  # noqa: E402


def _sample_packet():
    return {
        "request_id": "REQ-TEST-001",
        "topic": "test",
        "question": "Is the system healthy?",
        "evidence": ["ev-1", "ev-2"],
    }


class TestAdapterRouter:
    def test_route_single(self):
        reg = AdapterRegistry()
        reg.register("mock", MockAdapter())
        router = AdapterRouter(reg)
        results = router.route(_sample_packet(), ["mock"])
        assert len(results) == 1
        assert isinstance(results[0], ReasoningResult)
        assert results[0].adapter_name == "mock"

    def test_route_multiple(self):
        reg = AdapterRegistry()
        reg.register("mock", MockAdapter())
        reg.register("apex", ApexAdapter())
        router = AdapterRouter(reg)
        results = router.route(_sample_packet(), ["mock", "apex"])
        assert len(results) == 2
        names = {r.adapter_name for r in results}
        assert names == {"mock", "apex"}

    def test_route_missing_adapter_raises(self):
        reg = AdapterRegistry()
        router = AdapterRouter(reg)
        with pytest.raises(KeyError, match="not registered"):
            router.route(_sample_packet(), ["nonexistent"])

    def test_route_empty_names_raises(self):
        reg = AdapterRegistry()
        router = AdapterRouter(reg)
        with pytest.raises(ValueError, match="must not be empty"):
            router.route(_sample_packet(), [])

    def test_route_preserves_request_id(self):
        reg = AdapterRegistry()
        reg.register("mock", MockAdapter())
        router = AdapterRouter(reg)
        results = router.route(_sample_packet(), ["mock"])
        assert results[0].request_id == "REQ-TEST-001"

    def test_route_all_results_have_claims(self):
        reg = AdapterRegistry()
        reg.register("mock", MockAdapter())
        reg.register("apex", ApexAdapter())
        router = AdapterRouter(reg)
        results = router.route(_sample_packet(), ["mock", "apex"])
        for r in results:
            assert len(r.claims) > 0

    def test_route_all_results_have_model_meta(self):
        reg = AdapterRegistry()
        reg.register("mock", MockAdapter())
        router = AdapterRouter(reg)
        results = router.route(_sample_packet(), ["mock"])
        assert results[0].model_meta.provider == "local"
