"""APEX adapter — Cognis-APEX-3.2 local model integration.

Supports two modes:
  1. **mock** (default) — deterministic output for tests and demos.
  2. **command** — shell out to a local runtime (e.g. llama.cpp).

Configuration via environment variables:
  DEEPSIGMA_APEX_MODE       mock | command  (default: mock)
  DEEPSIGMA_APEX_CMD        command to execute (required in command mode)
  DEEPSIGMA_APEX_MODEL_PATH path to the model weights file

Safety:
  - No ``shell=True``
  - Timeout enforced (default 60 s)
  - Graceful error handling
  - No writes outside temp files
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

from ..base_adapter import BaseModelAdapter
from ..models import (
    CandidateClaim,
    ContradictionRecord,
    ModelMeta,
    ReasoningResult,
    ReasoningStep,
)
from ..ttl import compute_claim_ttl_seconds, ttl_from_packet

_DEFAULT_TIMEOUT_SECONDS = 60


class ApexAdapter(BaseModelAdapter):
    """Adapter for the Cognis-APEX-3.2 local model.

    In mock mode the adapter returns deterministic structured output.
    In command mode it shells out to a configured local runtime.
    """

    adapter_name = "apex"

    def __init__(
        self,
        *,
        mode: Optional[str] = None,
        cmd: Optional[str] = None,
        model_path: Optional[str] = None,
        timeout: int = _DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._mode = mode or os.environ.get("DEEPSIGMA_APEX_MODE", "mock")
        self._cmd = cmd or os.environ.get("DEEPSIGMA_APEX_CMD", "")
        self._model_path = model_path or os.environ.get(
            "DEEPSIGMA_APEX_MODEL_PATH", ""
        )
        self._timeout = timeout

    # -- public API --

    def reason(self, packet: Dict[str, Any]) -> ReasoningResult:
        if self._mode == "command":
            return self._reason_command(packet)
        return self._reason_mock(packet)

    def health(self) -> Dict[str, Any]:
        base = super().health()
        base["mode"] = self._mode
        if self._mode == "command":
            base["cmd_configured"] = bool(self._cmd)
            base["model_path_configured"] = bool(self._model_path)
        return base

    # -- mock mode --

    def _reason_mock(self, packet: Dict[str, Any]) -> ReasoningResult:
        request_id = packet.get("request_id", "apex-req-001")
        question = packet.get("question", "No question provided")
        evidence = packet.get("evidence", [])
        topic = packet.get("topic", "general")
        ttl_str = ttl_from_packet(packet)
        ttl_sec = compute_claim_ttl_seconds(packet)

        h = hashlib.sha256(question.encode()).hexdigest()[:8]

        claims = [
            CandidateClaim(
                claim_id=f"APEX-C-{h}-1",
                text=f"APEX analysis: '{question[:50]}' — supported by evidence",
                claim_type="inference",
                confidence=0.88,
                citations=[str(e) for e in evidence[:2]] if evidence else [],
                ttl_seconds=ttl_sec,
            ),
            CandidateClaim(
                claim_id=f"APEX-C-{h}-2",
                text=f"Operational context for '{topic}' is nominal",
                claim_type="fact",
                confidence=0.93,
                citations=[str(e) for e in evidence[:1]] if evidence else [],
                ttl_seconds=ttl_sec,
            ),
        ]

        reasoning = [
            ReasoningStep(
                step_id=f"APEX-S-{h}-1",
                kind="observation",
                text=f"Ingesting evidence set ({len(evidence)} items) for topic '{topic}'",
                evidence_refs=[str(e) for e in evidence[:3]] if evidence else [],
            ),
            ReasoningStep(
                step_id=f"APEX-S-{h}-2",
                kind="comparison",
                text="Cross-referencing claims against baseline operational parameters",
            ),
            ReasoningStep(
                step_id=f"APEX-S-{h}-3",
                kind="inference",
                text=f"Concluding on question: {question[:80]}",
            ),
        ]

        return ReasoningResult(
            request_id=request_id,
            adapter_name=self.adapter_name,
            claims=claims,
            reasoning=reasoning,
            confidence=0.90,
            citations=[str(e) for e in evidence] if evidence else [],
            contradictions=[],
            model_meta=self._meta(),
            ttl=ttl_str,
        )

    # -- command mode --

    def _reason_command(self, packet: Dict[str, Any]) -> ReasoningResult:
        if not self._cmd:
            raise RuntimeError(
                "APEX command mode requires DEEPSIGMA_APEX_CMD to be set"
            )
        request_id = packet.get("request_id", "apex-cmd-001")

        # Write packet to a temp file and pass its path to the command
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            json.dump(packet, tmp)
            tmp_path = tmp.name

        try:
            cmd_parts = self._cmd.split()
            if self._model_path:
                cmd_parts.extend(["--model", self._model_path])
            cmd_parts.extend(["--input", tmp_path])

            proc = subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            stdout = proc.stdout.strip()
        except subprocess.TimeoutExpired:
            return self._error_result(
                request_id, "APEX command timed out"
            )
        except FileNotFoundError:
            return self._error_result(
                request_id,
                f"APEX command not found: {self._cmd.split()[0]}",
            )
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        return self._parse_command_output(request_id, stdout, packet)

    def _parse_command_output(
        self,
        request_id: str,
        stdout: str,
        packet: Dict[str, Any],
    ) -> ReasoningResult:
        """Attempt to parse structured JSON from command stdout."""
        try:
            data = json.loads(stdout)
            claims = [
                CandidateClaim(
                    claim_id=c.get("claimId", f"APEX-CMD-{i}"),
                    text=c.get("text", ""),
                    claim_type=c.get("claimType", "inference"),
                    confidence=float(c.get("confidence", 0.5)),
                    citations=c.get("citations", []),
                )
                for i, c in enumerate(data.get("claims", []))
            ]
            return ReasoningResult(
                request_id=request_id,
                adapter_name=self.adapter_name,
                claims=claims,
                reasoning=[],
                confidence=float(data.get("confidence", 0.5)),
                citations=data.get("citations", []),
                contradictions=[],
                model_meta=self._meta(),
                raw_json=data,
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            # Wrap raw text as a minimal structured result
            return ReasoningResult(
                request_id=request_id,
                adapter_name=self.adapter_name,
                claims=[
                    CandidateClaim(
                        claim_id=f"APEX-RAW-{request_id}",
                        text=stdout[:500] if stdout else "(empty output)",
                        claim_type="inference",
                        confidence=0.3,
                    )
                ],
                reasoning=[],
                confidence=0.3,
                citations=[],
                contradictions=[],
                model_meta=self._meta(),
                raw_text=stdout,
                warnings=["Could not parse structured output from APEX command"],
            )

    def _error_result(self, request_id: str, message: str) -> ReasoningResult:
        return ReasoningResult(
            request_id=request_id,
            adapter_name=self.adapter_name,
            claims=[],
            reasoning=[],
            confidence=0.0,
            citations=[],
            contradictions=[],
            model_meta=self._meta(),
            warnings=[message],
        )

    def _meta(self) -> ModelMeta:
        return ModelMeta(
            provider="local",
            model="Cognis-APEX-3.2",
            adapter_name=self.adapter_name,
            version="3.2",
            runtime="llama.cpp" if self._mode == "command" else "mock",
        )
