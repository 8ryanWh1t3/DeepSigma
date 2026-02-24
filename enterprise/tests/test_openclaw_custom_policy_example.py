"""Tests for the OpenClaw custom policy example bundle."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.openclaw.examples.custom_policy import (  # noqa: E402
    evaluate_claim_policy,
    load_import_demo_wasm,
    load_policy_wasm,
)
from adapters.openclaw.runtime import SandboxConfig, WASMRuntime  # noqa: E402


def test_example_wasm_files_validate() -> None:
    runtime = WASMRuntime()
    assert runtime.validate_module(load_policy_wasm()) == []
    assert runtime.validate_module(load_import_demo_wasm()) == []


def test_import_whitelist_blocks_host_functions_when_removed() -> None:
    runtime = WASMRuntime(
        config=SandboxConfig(import_whitelist={"env.log_info"}),
    )
    errors = runtime.validate_module(load_import_demo_wasm())
    assert any("env.get_claim" in err for err in errors)
    assert any("env.emit_signal" in err for err in errors)


def test_policy_evaluation_returns_structured_decision() -> None:
    decision = evaluate_claim_policy(0.4)
    assert isinstance(decision, dict)
    assert {"action", "reason", "runtime_success", "confidence"}.issubset(decision.keys())

    if decision["runtime_success"]:
        assert decision["action"] in {"allow", "reject"}
    else:
        assert isinstance(decision["runtime_error"], str)
        assert "wasmtime" in decision["runtime_error"].lower()
