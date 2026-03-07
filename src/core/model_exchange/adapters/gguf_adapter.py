"""Generic GGUF adapter — run any GGUF model via a local runtime.

Configuration via environment variables:
  DEEPSIGMA_GGUF_MODE        mock | command (default: mock)
  DEEPSIGMA_GGUF_CMD         command to execute (e.g. "llama-cli")
  DEEPSIGMA_GGUF_MODEL_PATH  path to .gguf model file
  DEEPSIGMA_GGUF_CTX_SIZE    context window size (default: 4096)

In mock mode, returns deterministic output without any network calls or
local runtime.  In command mode, shells out to the configured command
using the same safety constraints as the APEX adapter.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from typing import Any, Dict, Optional

from ..base_adapter import BaseModelAdapter
from ..models import (
    CandidateClaim,
    ModelMeta,
    ReasoningResult,
    ReasoningStep,
)
from ..ttl import compute_claim_ttl_seconds, ttl_from_packet

_DEFAULT_TIMEOUT_SECONDS = 120


class GGUFAdapter(BaseModelAdapter):
    """Generic adapter for any GGUF-format model."""

    adapter_name = "gguf"

    def __init__(
        self,
        *,
        mode: Optional[str] = None,
        cmd: Optional[str] = None,
        model_path: Optional[str] = None,
        model_name: Optional[str] = None,
        ctx_size: Optional[int] = None,
        timeout: int = _DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._mode = mode or os.environ.get("DEEPSIGMA_GGUF_MODE", "mock")
        self._cmd = cmd or os.environ.get("DEEPSIGMA_GGUF_CMD", "")
        self._model_path = model_path or os.environ.get(
            "DEEPSIGMA_GGUF_MODEL_PATH", ""
        )
        self._model_name = model_name or "generic-gguf"
        self._ctx_size = ctx_size or int(
            os.environ.get("DEEPSIGMA_GGUF_CTX_SIZE", "4096")
        )
        self._timeout = timeout

    def reason(self, packet: Dict[str, Any]) -> ReasoningResult:
        if self._mode == "command":
            return self._reason_command(packet)
        return self._reason_mock(packet)

    def health(self) -> Dict[str, Any]:
        base = super().health()
        base["mode"] = self._mode
        base["model_name"] = self._model_name
        if self._mode == "command":
            base["cmd_configured"] = bool(self._cmd)
            base["model_path_configured"] = bool(self._model_path)
        return base

    # -- mock mode --

    def _reason_mock(self, packet: Dict[str, Any]) -> ReasoningResult:
        request_id = packet.get("request_id", "gguf-req-001")
        question = packet.get("question", "No question provided")
        evidence = packet.get("evidence", [])
        topic = packet.get("topic", "general")
        ttl_str = ttl_from_packet(packet)
        ttl_sec = compute_claim_ttl_seconds(packet)

        h = hashlib.sha256(question.encode()).hexdigest()[:8]

        claims = [
            CandidateClaim(
                claim_id=f"GGUF-C-{h}-1",
                text=f"GGUF model analysis of '{question[:50]}': consistent with evidence",
                claim_type="inference",
                confidence=0.78,
                citations=[str(e) for e in evidence[:2]] if evidence else [],
                ttl_seconds=ttl_sec,
            ),
        ]

        reasoning = [
            ReasoningStep(
                step_id=f"GGUF-S-{h}-1",
                kind="observation",
                text=f"Processing evidence for '{topic}'",
                evidence_refs=[str(e) for e in evidence[:2]] if evidence else [],
            ),
            ReasoningStep(
                step_id=f"GGUF-S-{h}-2",
                kind="inference",
                text=f"Local model inference for: {question[:80]}",
            ),
        ]

        return ReasoningResult(
            request_id=request_id,
            adapter_name=self.adapter_name,
            claims=claims,
            reasoning=reasoning,
            confidence=0.78,
            citations=[str(e) for e in evidence] if evidence else [],
            contradictions=[],
            model_meta=self._meta(),
            ttl=ttl_str,
        )

    # -- command mode --

    def _reason_command(self, packet: Dict[str, Any]) -> ReasoningResult:
        if not self._cmd:
            raise RuntimeError(
                "GGUF command mode requires DEEPSIGMA_GGUF_CMD to be set"
            )
        request_id = packet.get("request_id", "gguf-cmd-001")

        question = packet.get("question", "")
        evidence = packet.get("evidence", [])
        prompt = (
            f"Analyze the following and provide structured JSON output.\n"
            f"Question: {question}\nEvidence: {json.dumps(evidence)}\n"
            f"Return JSON with: claims (array of {{text, claimType, confidence}}), "
            f"confidence (float)."
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as tmp:
            tmp.write(prompt)
            tmp_path = tmp.name

        try:
            cmd_parts = self._cmd.split()
            if self._model_path:
                cmd_parts.extend(["-m", self._model_path])
            cmd_parts.extend([
                "-c", str(self._ctx_size),
                "-f", tmp_path,
            ])

            proc = subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            stdout = proc.stdout.strip()
        except subprocess.TimeoutExpired:
            return self._error_result(request_id, "GGUF command timed out")
        except FileNotFoundError:
            return self._error_result(
                request_id,
                f"GGUF command not found: {self._cmd.split()[0]}",
            )
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        return self._parse_output(request_id, stdout)

    def _parse_output(self, request_id: str, stdout: str) -> ReasoningResult:
        try:
            data = json.loads(stdout)
            claims = [
                CandidateClaim(
                    claim_id=f"GGUF-CMD-{i}",
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
            return ReasoningResult(
                request_id=request_id,
                adapter_name=self.adapter_name,
                claims=[
                    CandidateClaim(
                        claim_id=f"GGUF-RAW-{request_id}",
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
                warnings=["Could not parse structured output from GGUF command"],
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
            model=self._model_name,
            adapter_name=self.adapter_name,
            version=None,
            runtime="gguf-cli" if self._mode == "command" else "mock",
        )
