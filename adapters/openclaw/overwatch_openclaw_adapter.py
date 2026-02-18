"""
Σ OVERWATCH × OpenClaw adapter

Connects an OpenClaw skill runner to the Overwatch dashboard API.
All calls go to the dashboard FastAPI server (default: http://localhost:8000).

Configuration via environment variables:
    OVERWATCH_BASE_URL   Base URL of the dashboard API (default: http://localhost:8000)
    OVERWATCH_TIMEOUT    Request timeout in seconds (default: 30)

Usage:
    from adapters.openclaw.overwatch_openclaw_adapter import OverwatchClient, SkillRun, run_skill_with_overwatch

    client = OverwatchClient()  # reads OVERWATCH_BASE_URL from env
    result = run_skill_with_overwatch(
        SkillRun(skill_name="AccountQuarantine", payload={...}, actor_id="agent-1"),
        client,
    )
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:8000"
_DEFAULT_TIMEOUT = 30


def _api(base_url: str, path: str, body: Dict[str, Any] | None = None, timeout: int = _DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """Make a JSON API call (GET if body is None, POST otherwise)."""
    url = base_url.rstrip("/") + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST" if data is not None else "GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode(errors="replace")
        raise RuntimeError(f"Overwatch API {exc.code} at {url}: {body_text}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Overwatch API unreachable at {url}: {exc.reason}") from exc


@dataclass
class SkillRun:
    skill_name: str
    payload: Dict[str, Any]
    actor_id: str


class OverwatchClient:
    """HTTP client for the Σ OVERWATCH dashboard API.

    All methods map directly to dashboard API endpoints.
    Uses stdlib urllib only — no external dependencies required.
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: int | None = None,
    ):
        self.base_url = (base_url or os.environ.get("OVERWATCH_BASE_URL", _DEFAULT_BASE_URL)).rstrip("/")
        self.timeout = timeout or int(os.environ.get("OVERWATCH_TIMEOUT", str(_DEFAULT_TIMEOUT)))

    def _call(self, path: str, body: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return _api(self.base_url, path, body, self.timeout)

    # ── Episode lifecycle ────────────────────────────────────────

    def submit_task(self, decision_type: str, payload: Dict[str, Any], actor_id: str) -> str:
        """Create a new episode and return its session/episode ID.

        Maps to: POST /api/episodes
        """
        resp = self._call("/api/episodes", {
            "decisionType": decision_type,
            "payload": payload,
            "actorId": actor_id,
        })
        episode_id: str = resp.get("episodeId") or resp.get("id") or resp["session_id"]
        logger.debug("submit_task → episodeId=%s", episode_id)
        return episode_id

    def execute_tool(self, session_id: str, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call within an episode.

        Maps to: POST /api/episodes/{session_id}/tool_calls
        """
        resp = self._call(f"/api/episodes/{session_id}/tool_calls", {
            "toolName": tool_name,
            "toolInput": tool_input,
        })
        logger.debug("execute_tool session=%s tool=%s → %s", session_id, tool_name, resp.get("status"))
        return resp

    def dispatch_action(self, session_id: str, action_contract: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch an action through the safe action contract enforcement layer.

        Maps to: POST /api/episodes/{session_id}/actions
        """
        resp = self._call(f"/api/episodes/{session_id}/actions", action_contract)
        logger.debug("dispatch_action session=%s → %s", session_id, resp.get("status"))
        return resp

    def verify(self, session_id: str, method: str, details: Dict[str, Any]) -> Dict[str, Any]:
        """Run a postcondition verifier on the episode.

        Maps to: POST /api/episodes/{session_id}/verify
        """
        resp = self._call(f"/api/episodes/{session_id}/verify", {
            "method": method,
            "details": details,
        })
        logger.debug("verify session=%s method=%s → %s", session_id, method, resp.get("outcome"))
        return resp

    def seal(self, session_id: str, episode: Dict[str, Any]) -> Dict[str, Any]:
        """Seal and commit the episode to immutable storage.

        Maps to: POST /api/episodes/{session_id}/seal
        """
        resp = self._call(f"/api/episodes/{session_id}/seal", episode)
        logger.debug("seal session=%s → %s", session_id, resp.get("status"))
        return resp

    def health(self) -> Dict[str, Any]:
        """Check dashboard API health.

        Maps to: GET /api/health
        """
        return self._call("/api/health")


def map_skill_to_decision_type(skill_name: str) -> str:
    """Default skill → decisionType mapping; override per project."""
    return f"OpenClaw::{skill_name}"


def run_skill_with_overwatch(skill: SkillRun, ow: OverwatchClient) -> Dict[str, Any]:
    """Run a full skill lifecycle through the Overwatch governance pipeline.

    Steps: submit → (tool execution) → (action dispatch) → verify → seal
    """
    decision_type = map_skill_to_decision_type(skill.skill_name)
    session_id = ow.submit_task(
        decision_type=decision_type,
        payload=skill.payload,
        actor_id=skill.actor_id,
    )

    # Callers can add tool execution and action dispatch here:
    # ow.execute_tool(session_id, "my_tool", {...})
    # ow.dispatch_action(session_id, action_contract)

    verification = ow.verify(session_id, "read_after_write", {})
    seal_result = ow.seal(session_id, {"verificationResult": verification})

    return {
        "session_id": session_id,
        "verification": verification,
        "seal": seal_result,
        "status": seal_result.get("status", "sealed"),
    }
