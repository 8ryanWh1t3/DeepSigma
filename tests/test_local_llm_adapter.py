"""Tests for the local LLM adapter (connector, exhaust, extractor dispatch).

Run from repo root:
    pytest tests/test_local_llm_adapter.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import httpx  # noqa: F401
    _has_httpx = True
except ImportError:
    _has_httpx = False

from dashboard.server.models_exhaust import (
    DecisionEpisode,
    EpisodeEvent,
    Source,
)


# ── Helpers ──────────────────────────────────────────────────────

def _make_episode() -> DecisionEpisode:
    events = [
        EpisodeEvent(
            event_id="ev-local-01",
            episode_id="ep-local-test",
            event_type="metric",
            timestamp="2026-01-01T00:00:00Z",
            source="manual",
            payload={"name": "latency_ms", "value": 42},
        ),
    ]
    return DecisionEpisode(
        episode_id="ep-local-test",
        events=events,
        source=Source.manual,
        project="test-project",
    )


def _openai_chat_response(text: str = "Hello from local") -> dict:
    """Mock OpenAI-compatible /v1/chat/completions response."""
    return {
        "id": "chatcmpl-mock",
        "object": "chat.completion",
        "model": "llama-3-8b",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


def _openai_completion_response(text: str = "Generated text") -> dict:
    """Mock OpenAI-compatible /v1/completions response."""
    return {
        "id": "cmpl-mock",
        "object": "text_completion",
        "model": "llama-3-8b",
        "choices": [{"index": 0, "text": text}],
        "usage": {"prompt_tokens": 8, "completion_tokens": 4, "total_tokens": 12},
    }


def _openai_models_response() -> dict:
    """Mock OpenAI-compatible /v1/models response."""
    return {
        "object": "list",
        "data": [
            {"id": "llama-3-8b", "object": "model", "owned_by": "local"},
            {"id": "mistral-7b", "object": "model", "owned_by": "local"},
        ],
    }


# ── TestLlamaCppConnector ────────────────────────────────────────

@pytest.mark.skipif(not _has_httpx, reason="httpx not installed")
class TestLlamaCppConnector:
    """Tests for the LlamaCppConnector (mocked httpx)."""

    def test_chat_happy_path(self):
        from adapters.local_llm.connector import LlamaCppConnector

        mock_resp = MagicMock()
        mock_resp.json.return_value = _openai_chat_response("test output")
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp

        with patch("httpx.Client", return_value=mock_client):
            connector = LlamaCppConnector(base_url="http://test:8080")
            result = connector.chat([{"role": "user", "content": "Hello"}])

        assert result["text"] == "test output"
        assert result["backend"] == "llama.cpp"
        assert result["model"] == "llama-3-8b"
        assert "latency_ms" in result["timing"]
        assert result["usage"]["total_tokens"] == 15

    def test_chat_passes_model_and_params(self):
        from adapters.local_llm.connector import LlamaCppConnector

        mock_resp = MagicMock()
        mock_resp.json.return_value = _openai_chat_response()
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp

        with patch("httpx.Client", return_value=mock_client):
            connector = LlamaCppConnector(
                base_url="http://test:8080", model="my-model"
            )
            connector.chat(
                [{"role": "user", "content": "Hi"}],
                max_tokens=512,
                temperature=0.7,
            )

        call_kwargs = mock_client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["model"] == "my-model"
        assert payload["max_tokens"] == 512
        assert payload["temperature"] == 0.7

    def test_generate_completion(self):
        from adapters.local_llm.connector import LlamaCppConnector

        mock_resp = MagicMock()
        mock_resp.json.return_value = _openai_completion_response("gen output")
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp

        with patch("httpx.Client", return_value=mock_client):
            connector = LlamaCppConnector(base_url="http://test:8080")
            result = connector.generate("Complete this:", max_tokens=256)

        assert result["text"] == "gen output"
        assert result["backend"] == "llama.cpp"

    def test_health_ok(self):
        from adapters.local_llm.connector import LlamaCppConnector

        mock_resp = MagicMock()
        mock_resp.json.return_value = _openai_models_response()
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("httpx.Client", return_value=mock_client):
            connector = LlamaCppConnector(base_url="http://test:8080")
            health = connector.health()

        assert health["ok"] is True
        assert "llama-3-8b" in health["models"]
        assert "mistral-7b" in health["models"]

    def test_health_failure(self):
        from adapters.local_llm.connector import LlamaCppConnector

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = ConnectionError("refused")

        with patch("httpx.Client", return_value=mock_client):
            connector = LlamaCppConnector(base_url="http://test:8080")
            health = connector.health()

        assert health["ok"] is False
        assert "refused" in health.get("error", "")

    def test_env_var_config(self, monkeypatch):
        from adapters.local_llm.connector import LlamaCppConnector

        monkeypatch.setenv("DEEPSIGMA_LOCAL_BASE_URL", "http://gpu-box:9090")
        monkeypatch.setenv("DEEPSIGMA_LOCAL_API_KEY", "sk-local-test")
        monkeypatch.setenv("DEEPSIGMA_LOCAL_MODEL", "phi-3-mini")
        monkeypatch.setenv("DEEPSIGMA_LOCAL_TIMEOUT", "30")

        connector = LlamaCppConnector()
        assert connector.base_url == "http://gpu-box:9090"
        assert connector.api_key == "sk-local-test"
        assert connector.model == "phi-3-mini"
        assert connector.timeout == 30

    def test_auth_header_included(self):
        from adapters.local_llm.connector import LlamaCppConnector

        connector = LlamaCppConnector(
            base_url="http://test:8080", api_key="my-token"
        )
        headers = connector._headers()
        assert headers["Authorization"] == "Bearer my-token"

    def test_no_auth_header_when_empty(self):
        from adapters.local_llm.connector import LlamaCppConnector

        connector = LlamaCppConnector(base_url="http://test:8080", api_key="")
        headers = connector._headers()
        assert "Authorization" not in headers


# ── TestLocalLLMExhaustAdapter ───────────────────────────────────

class TestLocalLLMExhaustAdapter:
    """Tests for the exhaust wrapper — verify event emission."""

    def test_chat_with_exhaust_emits_events(self):
        from adapters.local_llm.exhaust import LocalLLMExhaustAdapter

        mock_connector = MagicMock()
        mock_connector.chat.return_value = {
            "text": "response text",
            "model": "test-model",
            "backend": "llama.cpp",
            "usage": {"total_tokens": 20},
            "timing": {"latency_ms": 50},
        }

        adapter = LocalLLMExhaustAdapter(mock_connector, project="test-proj")

        with patch.object(adapter, "_flush") as mock_flush:
            result = adapter.chat_with_exhaust(
                [{"role": "user", "content": "Hello"}], max_tokens=256
            )

        assert result["text"] == "response text"
        mock_connector.chat.assert_called_once()

        # Verify 3 events flushed: prompt, response, metric
        mock_flush.assert_called_once()
        events = mock_flush.call_args[0][0]
        assert len(events) == 3
        types = [e["event_type"] for e in events]
        assert types == ["prompt", "response", "metric"]

        # Verify source is "local"
        for ev in events:
            assert ev["source"] == "local"

    def test_chat_with_exhaust_passes_params(self):
        from adapters.local_llm.exhaust import LocalLLMExhaustAdapter

        mock_connector = MagicMock()
        mock_connector.chat.return_value = {
            "text": "ok", "model": "", "backend": "llama.cpp",
            "usage": {}, "timing": {"latency_ms": 10},
        }

        adapter = LocalLLMExhaustAdapter(mock_connector)

        with patch.object(adapter, "_flush"):
            adapter.chat_with_exhaust(
                [{"role": "user", "content": "Hi"}],
                max_tokens=1024,
                temperature=0.5,
            )

        mock_connector.chat.assert_called_once_with(
            [{"role": "user", "content": "Hi"}],
            max_tokens=1024,
            temperature=0.5,
        )


# ── TestLLMExtractorLocalBackend ─────────────────────────────────

class TestLLMExtractorLocalBackend:
    """Integration: verify extractor dispatches to local when configured."""

    def test_call_api_dispatches_to_local(self, monkeypatch):
        monkeypatch.setenv("DEEPSIGMA_LLM_BACKEND", "local")

        from engine.exhaust_llm_extractor import LLMExtractor

        mock_result = {
            "text": json.dumps({
                "truth": [{"claim": "local claim", "confidence": 0.8, "evidence": "test"}],
                "reasoning": [],
                "memory": [],
            }),
            "model": "llama-3-8b",
            "backend": "llama.cpp",
            "usage": {},
            "timing": {"latency_ms": 100},
        }

        with patch(
            "adapters.local_llm.connector.LlamaCppConnector.chat",
            return_value=mock_result,
        ):
            extractor = LLMExtractor()
            buckets = extractor.extract(_make_episode())

        assert len(buckets["truth"]) == 1
        assert buckets["truth"][0].claim == "local claim"

    def test_call_api_defaults_to_anthropic(self, monkeypatch):
        """Without DEEPSIGMA_LLM_BACKEND, defaults to anthropic path."""
        monkeypatch.delenv("DEEPSIGMA_LLM_BACKEND", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")

        from engine.exhaust_llm_extractor import LLMExtractor

        with patch(
            "engine.exhaust_llm_extractor.LLMExtractor._call_anthropic",
            return_value=json.dumps({"truth": [], "reasoning": [], "memory": []}),
        ) as mock_anthropic:
            extractor = LLMExtractor()
            extractor.extract(_make_episode())

        mock_anthropic.assert_called_once()

    def test_local_backend_no_anthropic_key_needed(self, monkeypatch):
        """Local backend works without ANTHROPIC_API_KEY."""
        monkeypatch.setenv("DEEPSIGMA_LLM_BACKEND", "local")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        from engine.exhaust_llm_extractor import LLMExtractor

        mock_result = {
            "text": json.dumps({"truth": [], "reasoning": [], "memory": []}),
            "model": "test",
            "backend": "llama.cpp",
            "usage": {},
            "timing": {"latency_ms": 10},
        }

        with patch(
            "adapters.local_llm.connector.LlamaCppConnector.chat",
            return_value=mock_result,
        ):
            extractor = LLMExtractor()
            buckets = extractor.extract(_make_episode())

        assert buckets == {"truth": [], "reasoning": [], "memory": []}


# ── TestSourceEnum ───────────────────────────────────────────────

def test_source_enum_has_local():
    """Verify 'local' was added to Source enum."""
    assert Source.local.value == "local"
