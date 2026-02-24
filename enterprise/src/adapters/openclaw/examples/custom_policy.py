"""OpenClaw custom policy demo helpers."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from adapters.openclaw.runtime import ExecutionResult, WASMRuntime

EXAMPLE_DIR = Path(__file__).resolve().parent / "custom-policy"
POLICY_WASM_PATH = EXAMPLE_DIR / "reject_low_confidence.wasm"
IMPORT_DEMO_WASM_PATH = EXAMPLE_DIR / "import_demo.wasm"


@dataclass
class PolicyDecision:
    action: str
    reason: str
    threshold: float
    confidence: float
    runtime_success: bool
    runtime_error: str | None = None


def load_policy_wasm() -> bytes:
    return POLICY_WASM_PATH.read_bytes()


def load_import_demo_wasm() -> bytes:
    return IMPORT_DEMO_WASM_PATH.read_bytes()


def evaluate_claim_policy(
    confidence: float,
    threshold: float = 0.5,
    runtime: WASMRuntime | None = None,
) -> dict[str, Any]:
    """Evaluate a confidence gate policy with WASMRuntime.

    The WASM module returns an integer verdict code:
    - `1`: allow
    - `0`: reject
    """
    rt = runtime or WASMRuntime()
    result = rt.execute(
        load_policy_wasm(),
        "evaluate",
        {"claim_confidence": confidence, "threshold": threshold},
    )
    return asdict(_result_to_decision(result, confidence, threshold))


def _result_to_decision(
    result: ExecutionResult,
    confidence: float,
    threshold: float,
) -> PolicyDecision:
    if not result.success:
        return PolicyDecision(
            action="error",
            reason="runtime execution failed",
            threshold=threshold,
            confidence=confidence,
            runtime_success=False,
            runtime_error=result.error,
        )

    verdict_code = int(result.output)
    if verdict_code == 1:
        return PolicyDecision(
            action="allow",
            reason="claim confidence meets threshold",
            threshold=threshold,
            confidence=confidence,
            runtime_success=True,
        )
    return PolicyDecision(
        action="reject",
        reason="claim confidence below threshold",
        threshold=threshold,
        confidence=confidence,
        runtime_success=True,
    )
