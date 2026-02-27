"""Tests for the ASGI middleware."""
from __future__ import annotations

import asyncio

import pytest

from deepsigma_middleware.fastapi_mw import DeepSigmaMiddleware
from deepsigma_middleware.decorator import configure, get_session, reset_session


@pytest.fixture(autouse=True)
def clean_session():
    reset_session()
    yield
    reset_session()


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestDeepSigmaMiddleware:

    def test_http_request_logs_decision(self):
        configure(agent_id="asgi-test")
        sent = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200})
            await send({"type": "http.response.body", "body": b"ok"})

        mw = DeepSigmaMiddleware(mock_app)
        scope = {"type": "http", "method": "GET", "path": "/health"}

        async def mock_receive():
            return {"type": "http.request"}

        async def mock_send(msg):
            sent.append(msg)

        _run(mw(scope, mock_receive, mock_send))
        assert len(sent) == 2
        assert sent[0]["status"] == 200

    def test_non_http_passthrough(self):
        called = []

        async def mock_app(scope, receive, send):
            called.append(True)

        mw = DeepSigmaMiddleware(mock_app)

        async def run():
            await mw({"type": "websocket"}, None, None)

        _run(run())
        assert len(called) == 1

    def test_agent_id_override(self):
        sent = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200})
            await send({"type": "http.response.body", "body": b""})

        mw = DeepSigmaMiddleware(mock_app, agent_id="custom-agent")

        async def mock_send(msg):
            sent.append(msg)

        _run(mw(
            {"type": "http", "method": "POST", "path": "/api"},
            None,
            mock_send,
        ))
        assert len(sent) == 2

    def test_captures_status_code(self):
        sent = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 404})
            await send({"type": "http.response.body", "body": b"not found"})

        mw = DeepSigmaMiddleware(mock_app)

        async def mock_send(msg):
            sent.append(msg)

        _run(mw(
            {"type": "http", "method": "GET", "path": "/missing"},
            None,
            mock_send,
        ))
        assert sent[0]["status"] == 404
