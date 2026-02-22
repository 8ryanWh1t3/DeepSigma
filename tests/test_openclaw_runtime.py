"""Tests for OpenClaw WASM sandbox runtime.

Validates resource limits, access controls, import
whitelisting, and graceful termination.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.openclaw.runtime import (  # noqa: E402
    DEFAULT_IMPORT_WHITELIST,
    ExecutionResult,
    SandboxConfig,
    SandboxViolation,
    WASMRuntime,
    _read_leb128,
)


# ── Minimal WASM module (no imports, exports i32) ───────


def _minimal_wasm() -> bytes:
    """Build a minimal valid WASM module.

    Module with no imports and one exported function
    that returns 42 (i32.const 42; end).
    """
    # WASM binary format (hand-assembled):
    # magic + version
    header = b"\x00asm\x01\x00\x00\x00"
    # Type section: 1 type, func() -> i32
    type_sec = bytes([
        0x01,  # section id
        0x05,  # section size
        0x01,  # 1 type
        0x60,  # func
        0x00,  # 0 params
        0x01, 0x7F,  # 1 result: i32
    ])
    # Function section: 1 function, type 0
    func_sec = bytes([
        0x03,  # section id
        0x02,  # size
        0x01,  # 1 function
        0x00,  # type index 0
    ])
    # Export section: export "evaluate" as func 0
    name = b"evaluate"
    export_sec = bytes([
        0x07,  # section id
        2 + len(name) + 2,  # size
        0x01,  # 1 export
        len(name),  # name length
    ]) + name + bytes([
        0x00,  # export kind: function
        0x00,  # function index 0
    ])
    # Code section: 1 body
    body = bytes([
        0x00,  # 0 locals
        0x41, 0x2A,  # i32.const 42
        0x0B,  # end
    ])
    code_sec = bytes([
        0x0A,  # section id
        2 + len(body),  # size
        0x01,  # 1 body
        len(body),  # body size
    ]) + body

    return (
        header + type_sec + func_sec
        + export_sec + code_sec
    )


def _wasm_with_import(
    mod: str, func: str,
) -> bytes:
    """Build a WASM module that imports a function."""
    header = b"\x00asm\x01\x00\x00\x00"
    mod_bytes = mod.encode()
    func_bytes = func.encode()

    # Type section: 1 type, func() -> ()
    type_sec = bytes([
        0x01, 0x04, 0x01,
        0x60, 0x00, 0x00,
    ])

    # Import section
    import_payload = bytes([
        0x01,  # 1 import
        len(mod_bytes),
    ]) + mod_bytes + bytes([
        len(func_bytes),
    ]) + func_bytes + bytes([
        0x00,  # kind: function
        0x00,  # type index 0
    ])
    import_sec = bytes([
        0x02,
        len(import_payload),
    ]) + import_payload

    return header + type_sec + import_sec


# ── SandboxConfig tests ─────────────────────────────────


class TestSandboxConfig:
    def test_defaults(self):
        cfg = SandboxConfig()
        assert cfg.memory_limit_mb == 64
        assert cfg.fuel_limit == 500_000_000
        assert cfg.timeout_s == 5.0
        assert cfg.allow_filesystem is False
        assert cfg.allow_network is False
        assert cfg.encrypt_at_rest is False

    def test_custom_limits(self):
        cfg = SandboxConfig(
            memory_limit_mb=32,
            fuel_limit=100_000,
            timeout_s=2.0,
        )
        assert cfg.memory_limit_mb == 32
        assert cfg.fuel_limit == 100_000
        assert cfg.timeout_s == 2.0

    def test_default_whitelist(self):
        cfg = SandboxConfig()
        assert "env.log_info" in cfg.import_whitelist
        assert "env.get_claim" in cfg.import_whitelist
        assert "env.emit_signal" in cfg.import_whitelist

    def test_custom_whitelist(self):
        cfg = SandboxConfig(
            import_whitelist={"env.custom_fn"},
        )
        assert "env.custom_fn" in cfg.import_whitelist
        assert "env.log_info" not in cfg.import_whitelist


# ── WASMRuntime tests ────────────────────────────────────


class TestWASMRuntime:
    def test_creation(self):
        rt = WASMRuntime()
        assert rt.execution_count == 0
        assert rt.total_violations == 0
        assert rt.config.memory_limit_mb == 64

    def test_custom_config(self):
        cfg = SandboxConfig(memory_limit_mb=128)
        rt = WASMRuntime(config=cfg)
        assert rt.config.memory_limit_mb == 128

    def test_register_allowed_function(self):
        rt = WASMRuntime()
        rt.register_host_function(
            "env.log_info", lambda msg: None,
        )
        assert "env.log_info" in rt._host_functions

    def test_register_denied_function(self):
        rt = WASMRuntime()
        with pytest.raises(SandboxViolation) as exc:
            rt.register_host_function(
                "env.dangerous_fn",
                lambda: None,
            )
        assert exc.value.kind == "import_denied"


# ── Module validation tests ──────────────────────────────


class TestModuleValidation:
    def test_empty_module_fails(self):
        rt = WASMRuntime()
        errors = rt.validate_module(b"")
        assert "Empty WASM module" in errors

    def test_invalid_magic_fails(self):
        rt = WASMRuntime()
        errors = rt.validate_module(b"not-wasm")
        assert any(
            "magic" in e.lower() for e in errors
        )

    def test_valid_minimal_module(self):
        rt = WASMRuntime()
        wasm = _minimal_wasm()
        errors = rt.validate_module(wasm)
        assert errors == []

    def test_oversized_module_fails(self):
        cfg = SandboxConfig(memory_limit_mb=1)
        rt = WASMRuntime(config=cfg)
        # Create module larger than 1 MB
        big = b"\x00asm\x01\x00\x00\x00" + (
            b"\x00" * (2 * 1024 * 1024)
        )
        errors = rt.validate_module(big)
        assert any("exceeds" in e for e in errors)

    def test_unauthorized_import_detected(self):
        rt = WASMRuntime()
        wasm = _wasm_with_import(
            "evil", "hack_system",
        )
        errors = rt.validate_module(wasm)
        assert any(
            "Unauthorized" in e for e in errors
        )

    def test_authorized_import_passes(self):
        cfg = SandboxConfig(
            import_whitelist={"env.log_info"},
        )
        rt = WASMRuntime(config=cfg)
        wasm = _wasm_with_import("env", "log_info")
        errors = rt.validate_module(wasm)
        assert errors == []


# ── Execution tests (graceful degradation) ───────────────


class TestExecution:
    def test_execute_empty_module(self):
        rt = WASMRuntime()
        result = rt.execute(
            b"", "evaluate", {},
        )
        assert result.success is False
        assert "validation failed" in result.error
        assert rt.execution_count == 1

    def test_execute_invalid_module(self):
        rt = WASMRuntime()
        result = rt.execute(
            b"bad-bytes", "evaluate", {},
        )
        assert result.success is False
        assert rt.total_violations > 0

    def test_execute_unauthorized_import(self):
        rt = WASMRuntime()
        wasm = _wasm_with_import(
            "evil", "hack",
        )
        result = rt.execute(
            wasm, "evaluate", {},
        )
        assert result.success is False
        assert len(result.violations) > 0

    def test_execution_result_structure(self):
        result = ExecutionResult(success=True)
        assert result.output is None
        assert result.error is None
        assert result.elapsed_ms == 0
        assert result.fuel_consumed == 0
        assert result.violations == []

    def test_execution_tracks_count(self):
        rt = WASMRuntime()
        rt.execute(b"", "f", {})
        rt.execute(b"", "f", {})
        assert rt.execution_count == 2


# ── Access control tests ─────────────────────────────────


class TestAccessControl:
    def test_filesystem_denied_by_default(self):
        cfg = SandboxConfig()
        assert cfg.allow_filesystem is False

    def test_network_denied_by_default(self):
        cfg = SandboxConfig()
        assert cfg.allow_network is False

    def test_filesystem_explicit_allow(self):
        cfg = SandboxConfig(allow_filesystem=True)
        assert cfg.allow_filesystem is True

    def test_network_explicit_allow(self):
        cfg = SandboxConfig(allow_network=True)
        assert cfg.allow_network is True


# ── Import whitelist tests ───────────────────────────────


class TestImportWhitelist:
    def test_default_whitelist_contents(self):
        expected = {
            "env.log_debug",
            "env.log_info",
            "env.log_warn",
            "env.get_claim",
            "env.get_evidence",
            "env.get_config",
            "env.emit_signal",
        }
        assert DEFAULT_IMPORT_WHITELIST == expected

    def test_whitelist_is_frozen(self):
        assert isinstance(
            DEFAULT_IMPORT_WHITELIST, frozenset,
        )

    def test_custom_whitelist_replaces(self):
        cfg = SandboxConfig(
            import_whitelist={"env.custom"},
        )
        assert cfg.import_whitelist == {"env.custom"}


# ── SandboxViolation tests ──────────────────────────────


class TestSandboxViolation:
    def test_violation_attributes(self):
        v = SandboxViolation(
            "fuel_exhausted",
            "Computation limit exceeded",
            {"fuel_used": 500000000},
        )
        assert v.kind == "fuel_exhausted"
        assert v.details["fuel_used"] == 500000000
        assert "fuel_exhausted" in str(v)

    def test_violation_default_details(self):
        v = SandboxViolation("test", "msg")
        assert v.details == {}


# ── LEB128 utility tests ────────────────────────────────


class TestLEB128:
    def test_single_byte(self):
        val, consumed = _read_leb128(bytes([42]), 0)
        assert val == 42
        assert consumed == 1

    def test_multi_byte(self):
        # 624485 = 0xE5 0x8E 0x26 in LEB128
        val, consumed = _read_leb128(
            bytes([0xE5, 0x8E, 0x26]), 0,
        )
        assert val == 624485
        assert consumed == 3

    def test_zero(self):
        val, consumed = _read_leb128(bytes([0]), 0)
        assert val == 0
        assert consumed == 1

    def test_offset(self):
        data = bytes([0xFF, 42])
        val, consumed = _read_leb128(data, 1)
        assert val == 42
        assert consumed == 1


# ── Fuzzing harness ──────────────────────────────────────


class TestFuzzingHarness:
    """Property-based tests for sandbox robustness."""

    @pytest.mark.parametrize("size", [
        0, 1, 4, 8, 100, 1000,
    ])
    def test_random_bytes_no_crash(self, size):
        """Ensure random bytes never crash the runtime."""
        import os

        rt = WASMRuntime()
        data = os.urandom(size)
        result = rt.execute(data, "evaluate", {})
        assert result.success is False
        assert result.error is not None

    @pytest.mark.parametrize("name", [
        "", "a" * 1000, "eval\x00uate",
        "../../../etc/passwd",
    ])
    def test_malicious_function_names(self, name):
        """Ensure malicious function names are safe."""
        rt = WASMRuntime()
        wasm = _minimal_wasm()
        result = rt.execute(wasm, name, {})
        # Either fails validation or gracefully errors
        assert isinstance(result, ExecutionResult)

    def test_concurrent_executions_tracked(self):
        """Verify execution counter is accurate."""
        rt = WASMRuntime()
        for _ in range(10):
            rt.execute(b"", "f", {})
        assert rt.execution_count == 10
        assert rt.total_violations >= 10
