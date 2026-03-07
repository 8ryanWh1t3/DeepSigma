"""Tests for core.model_exchange.adapters — APEX, Mock, OpenAI, Claude, GGUF."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.model_exchange.models import ReasoningResult  # noqa: E402
from core.model_exchange.adapters.apex_adapter import ApexAdapter  # noqa: E402
from core.model_exchange.adapters.mock_adapter import MockAdapter  # noqa: E402
from core.model_exchange.adapters.openai_adapter import OpenAIAdapter  # noqa: E402
from core.model_exchange.adapters.claude_adapter import ClaudeAdapter  # noqa: E402
from core.model_exchange.adapters.gguf_adapter import GGUFAdapter  # noqa: E402


def _sample_packet():
    return {
        "request_id": "REQ-ADAPTER-001",
        "topic": "SLA Review",
        "question": "Is the deployment within SLA?",
        "evidence": ["ev-latency", "ev-error-rate"],
        "ttl": 3600,
    }


# -- APEX Adapter --


class TestApexAdapterMock:
    def test_reason_returns_result(self):
        adapter = ApexAdapter()
        result = adapter.reason(_sample_packet())
        assert isinstance(result, ReasoningResult)

    def test_adapter_name(self):
        assert ApexAdapter().adapter_name == "apex"

    def test_mock_claims(self):
        result = ApexAdapter().reason(_sample_packet())
        assert len(result.claims) == 2
        assert all(c.claim_id.startswith("APEX-C-") for c in result.claims)

    def test_mock_reasoning_steps(self):
        result = ApexAdapter().reason(_sample_packet())
        assert len(result.reasoning) == 3

    def test_mock_confidence_bounded(self):
        result = ApexAdapter().reason(_sample_packet())
        assert 0 <= result.confidence <= 1

    def test_mock_model_meta(self):
        result = ApexAdapter().reason(_sample_packet())
        assert result.model_meta.model == "Cognis-APEX-3.2"
        assert result.model_meta.provider == "local"
        assert result.model_meta.runtime == "mock"

    def test_mock_ttl_passthrough(self):
        result = ApexAdapter().reason(_sample_packet())
        assert result.ttl == "3600"

    def test_mock_citations(self):
        result = ApexAdapter().reason(_sample_packet())
        assert len(result.citations) == 2

    def test_health(self):
        health = ApexAdapter().health()
        assert health["ok"] is True
        assert health["mode"] == "mock"

    def test_command_mode_no_cmd_raises(self):
        adapter = ApexAdapter(mode="command", cmd="")
        with pytest.raises(RuntimeError, match="DEEPSIGMA_APEX_CMD"):
            adapter.reason(_sample_packet())

    def test_deterministic_output(self):
        adapter = ApexAdapter()
        r1 = adapter.reason(_sample_packet())
        r2 = adapter.reason(_sample_packet())
        assert r1.claims[0].claim_id == r2.claims[0].claim_id
        assert r1.confidence == r2.confidence


# -- Mock Adapter --


class TestMockAdapter:
    def test_reason_returns_result(self):
        result = MockAdapter().reason(_sample_packet())
        assert isinstance(result, ReasoningResult)

    def test_adapter_name(self):
        assert MockAdapter().adapter_name == "mock"

    def test_two_claims(self):
        result = MockAdapter().reason(_sample_packet())
        assert len(result.claims) == 2

    def test_claim_ids_prefixed(self):
        result = MockAdapter().reason(_sample_packet())
        assert all(c.claim_id.startswith("MOCK-C-") for c in result.claims)

    def test_model_meta(self):
        result = MockAdapter().reason(_sample_packet())
        assert result.model_meta.model == "mock-deterministic-v1"


# -- OpenAI Adapter --


class TestOpenAIAdapterMock:
    def test_reason_mock(self):
        adapter = OpenAIAdapter(mode="mock")
        result = adapter.reason(_sample_packet())
        assert isinstance(result, ReasoningResult)
        assert result.adapter_name == "openai"

    def test_claim_ids_prefixed(self):
        result = OpenAIAdapter(mode="mock").reason(_sample_packet())
        assert all(c.claim_id.startswith("OAI-C-") for c in result.claims)

    def test_health_mock(self):
        health = OpenAIAdapter(mode="mock").health()
        assert health["ok"] is True
        assert health["mode"] == "mock"

    def test_live_no_key_returns_warning(self):
        adapter = OpenAIAdapter(mode="live", api_key="")
        result = adapter.reason(_sample_packet())
        assert len(result.warnings) > 0
        assert result.confidence == 0.0


# -- Claude Adapter --


class TestClaudeAdapterMock:
    def test_reason_mock(self):
        adapter = ClaudeAdapter(mode="mock")
        result = adapter.reason(_sample_packet())
        assert isinstance(result, ReasoningResult)
        assert result.adapter_name == "claude"

    def test_two_claims(self):
        result = ClaudeAdapter(mode="mock").reason(_sample_packet())
        assert len(result.claims) == 2

    def test_claim_ids_prefixed(self):
        result = ClaudeAdapter(mode="mock").reason(_sample_packet())
        assert all(c.claim_id.startswith("CLD-C-") for c in result.claims)

    def test_health_mock(self):
        health = ClaudeAdapter(mode="mock").health()
        assert health["ok"] is True
        assert health["mode"] == "mock"

    def test_risk_claim_present(self):
        result = ClaudeAdapter(mode="mock").reason(_sample_packet())
        risk_claims = result.claims_by_type("risk")
        assert len(risk_claims) >= 1

    def test_live_no_key_returns_warning(self):
        adapter = ClaudeAdapter(mode="live", api_key="")
        result = adapter.reason(_sample_packet())
        assert len(result.warnings) > 0


# -- GGUF Adapter --


class TestGGUFAdapterMock:
    def test_reason_mock(self):
        adapter = GGUFAdapter(mode="mock")
        result = adapter.reason(_sample_packet())
        assert isinstance(result, ReasoningResult)
        assert result.adapter_name == "gguf"

    def test_claim_ids_prefixed(self):
        result = GGUFAdapter(mode="mock").reason(_sample_packet())
        assert all(c.claim_id.startswith("GGUF-C-") for c in result.claims)

    def test_health_mock(self):
        health = GGUFAdapter(mode="mock").health()
        assert health["ok"] is True
        assert health["mode"] == "mock"

    def test_command_mode_no_cmd_raises(self):
        adapter = GGUFAdapter(mode="command", cmd="")
        with pytest.raises(RuntimeError, match="DEEPSIGMA_GGUF_CMD"):
            adapter.reason(_sample_packet())


# -- Cross-adapter --


class TestCrossAdapterConsistency:
    """All adapters in mock mode should produce valid ReasoningResult."""

    @pytest.mark.parametrize("adapter_cls", [
        ApexAdapter, MockAdapter, OpenAIAdapter, ClaudeAdapter, GGUFAdapter,
    ])
    def test_all_adapters_return_valid_result(self, adapter_cls):
        adapter = adapter_cls()
        result = adapter.reason(_sample_packet())
        assert isinstance(result, ReasoningResult)
        assert result.request_id == "REQ-ADAPTER-001"
        assert len(result.claims) >= 1
        assert 0 <= result.confidence <= 1
        assert result.model_meta.provider in ("local", "openai", "anthropic")

    @pytest.mark.parametrize("adapter_cls", [
        ApexAdapter, MockAdapter, OpenAIAdapter, ClaudeAdapter, GGUFAdapter,
    ])
    def test_all_adapters_serializable(self, adapter_cls):
        adapter = adapter_cls()
        result = adapter.reason(_sample_packet())
        d = result.to_dict()
        assert "requestId" in d
        assert "claims" in d
        assert "modelMeta" in d
