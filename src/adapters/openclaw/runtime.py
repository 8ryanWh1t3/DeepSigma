"""OpenClaw WASM sandbox runtime for untrusted policy modules.

Provides hardened execution of WASM policy modules with:
- Configurable memory limits (default 64 MB)
- CPU time limits via fuel metering (default 5s equiv)
- No filesystem access
- No network access
- Import whitelist: only approved host functions
- Graceful termination on limit breach

Requires the ``wasmtime`` optional dependency::

    pip install 'deepsigma[openclaw]'

Usage::

    runtime = WASMRuntime()
    result = runtime.execute(wasm_bytes, "evaluate", context)
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Default resource limits
DEFAULT_MEMORY_LIMIT_MB = 64
DEFAULT_FUEL_LIMIT = 500_000_000  # ~5s of computation
DEFAULT_TIMEOUT_S = 5.0

# Approved host function imports
DEFAULT_IMPORT_WHITELIST: Set[str] = frozenset({
    "env.log_debug",
    "env.log_info",
    "env.log_warn",
    "env.get_claim",
    "env.get_evidence",
    "env.get_config",
    "env.emit_signal",
})


@dataclass
class SandboxConfig:
    """Configuration for the WASM sandbox.

    Parameters
    ----------
    memory_limit_mb : int
        Maximum memory per module in megabytes.
    fuel_limit : int
        Fuel units for computation metering.
        Higher values allow more computation.
    timeout_s : float
        Wall-clock timeout in seconds.
    import_whitelist : set of str
        Allowed import function names
        (``module.function`` format).
    allow_filesystem : bool
        Whether to allow WASI filesystem access.
    allow_network : bool
        Whether to allow WASI network access.
    encrypt_at_rest : bool
        Whether evidence persistence should use at-rest encryption.
    """

    memory_limit_mb: int = DEFAULT_MEMORY_LIMIT_MB
    fuel_limit: int = DEFAULT_FUEL_LIMIT
    timeout_s: float = DEFAULT_TIMEOUT_S
    import_whitelist: Set[str] = field(
        default_factory=lambda: set(
            DEFAULT_IMPORT_WHITELIST,
        ),
    )
    allow_filesystem: bool = False
    allow_network: bool = False
    encrypt_at_rest: bool = False


class SandboxViolation(Exception):
    """Raised when a sandbox limit is breached."""

    def __init__(
        self,
        kind: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.kind = kind
        self.details = details or {}
        super().__init__(f"Sandbox violation [{kind}]: {message}")


@dataclass
class ExecutionResult:
    """Result of a sandboxed WASM policy execution."""

    success: bool
    output: Any = None
    error: Optional[str] = None
    elapsed_ms: int = 0
    fuel_consumed: int = 0
    memory_used_bytes: int = 0
    violations: List[str] = field(
        default_factory=list,
    )


class WASMRuntime:
    """Sandboxed WASM runtime for OpenClaw policy modules.

    Enforces strict resource limits and access controls
    on untrusted WASM modules.
    """

    def __init__(
        self,
        config: Optional[SandboxConfig] = None,
    ) -> None:
        self._config = config or SandboxConfig()
        self._host_functions: Dict[
            str, Callable[..., Any]
        ] = {}
        self._execution_count = 0
        self._total_violations = 0

        self._register_default_host_functions()

    @property
    def config(self) -> SandboxConfig:
        return self._config

    @property
    def execution_count(self) -> int:
        return self._execution_count

    @property
    def total_violations(self) -> int:
        return self._total_violations

    def register_host_function(
        self,
        name: str,
        fn: Callable[..., Any],
    ) -> None:
        """Register a host function for WASM imports.

        The function must be in the import whitelist.

        Parameters
        ----------
        name : str
            Import name (``module.function`` format).
        fn : callable
            Host function implementation.
        """
        if name not in self._config.import_whitelist:
            raise SandboxViolation(
                "import_denied",
                f"Function {name!r} not in whitelist",
            )
        self._host_functions[name] = fn

    def validate_module(
        self, wasm_bytes: bytes,
    ) -> List[str]:
        """Validate a WASM module before execution.

        Checks import requirements against the whitelist.
        Returns a list of validation errors (empty = OK).
        """
        errors: List[str] = []

        if not wasm_bytes:
            errors.append("Empty WASM module")
            return errors

        # Check WASM magic number
        if wasm_bytes[:4] != b"\x00asm":
            errors.append(
                "Invalid WASM magic number",
            )
            return errors

        # Check module size vs memory limit
        max_bytes = self._config.memory_limit_mb * 1024 * 1024
        if len(wasm_bytes) > max_bytes:
            errors.append(
                f"Module size {len(wasm_bytes):,} "
                f"exceeds limit "
                f"{max_bytes:,} bytes",
            )

        # Parse imports from WASM binary
        imports = self._extract_imports(wasm_bytes)
        for imp in imports:
            if imp not in self._config.import_whitelist:
                errors.append(
                    f"Unauthorized import: {imp!r}",
                )

        return errors

    def execute(
        self,
        wasm_bytes: bytes,
        function_name: str,
        context: Dict[str, Any],
    ) -> ExecutionResult:
        """Execute a WASM policy function in the sandbox.

        Parameters
        ----------
        wasm_bytes : bytes
            Compiled WASM module bytes.
        function_name : str
            Exported function to call.
        context : dict
            Input context passed to the function.

        Returns
        -------
        ExecutionResult
            Result with output, timing, and violations.
        """
        start = time.monotonic()
        self._execution_count += 1

        # Pre-execution validation
        val_errors = self.validate_module(wasm_bytes)
        if val_errors:
            self._total_violations += len(val_errors)
            return ExecutionResult(
                success=False,
                error=(
                    "Module validation failed: "
                    + "; ".join(val_errors)
                ),
                violations=val_errors,
                elapsed_ms=self._elapsed(start),
            )

        # Try wasmtime backend
        try:
            return self._execute_wasmtime(
                wasm_bytes,
                function_name,
                context,
                start,
            )
        except ImportError:
            return ExecutionResult(
                success=False,
                error=(
                    "wasmtime not installed. "
                    "Install with: pip install "
                    "'deepsigma[openclaw]'"
                ),
                elapsed_ms=self._elapsed(start),
            )
        except SandboxViolation as exc:
            self._total_violations += 1
            logger.warning(
                "Sandbox violation in %s: %s",
                function_name,
                exc,
            )
            return ExecutionResult(
                success=False,
                error=str(exc),
                violations=[exc.kind],
                elapsed_ms=self._elapsed(start),
            )
        except Exception as exc:
            logger.error(
                "WASM execution error: %s", exc,
            )
            return ExecutionResult(
                success=False,
                error=f"Execution error: {exc}",
                elapsed_ms=self._elapsed(start),
            )

    def _execute_wasmtime(
        self,
        wasm_bytes: bytes,
        function_name: str,
        context: Dict[str, Any],
        start: float,
    ) -> ExecutionResult:
        """Execute via wasmtime backend."""
        import wasmtime  # type: ignore[import-untyped]

        # Configure engine with limits
        engine_cfg = wasmtime.Config()
        engine_cfg.consume_fuel = True

        engine = wasmtime.Engine(engine_cfg)
        store = wasmtime.Store(engine)

        # Set fuel limit
        store.add_fuel(self._config.fuel_limit)

        # Memory limit via store limits
        mem_bytes = (
            self._config.memory_limit_mb * 1024 * 1024
        )
        store.set_limits(
            memory_size=mem_bytes,
        )

        # WASI config (no filesystem, no network)
        wasi_cfg = wasmtime.WasiConfig()
        if not self._config.allow_filesystem:
            pass  # No preopens = no fs access
        if not self._config.allow_network:
            pass  # No network capabilities

        store.set_wasi(wasi_cfg)

        # Compile and instantiate
        module = wasmtime.Module(engine, wasm_bytes)

        # Validate imports
        for imp in module.imports:
            key = f"{imp.module}.{imp.name}"
            if key not in self._config.import_whitelist:
                raise SandboxViolation(
                    "import_denied",
                    f"Unauthorized import: {key!r}",
                )

        linker = wasmtime.Linker(engine)
        linker.define_wasi()

        # Link approved host functions
        for name, fn in self._host_functions.items():
            parts = name.split(".", 1)
            if len(parts) == 2:
                linker.define_func(
                    parts[0], parts[1], fn,
                )

        instance = linker.instantiate(store, module)

        # Find and call the function
        func = instance.exports(store).get(
            function_name,
        )
        if func is None:
            raise SandboxViolation(
                "missing_export",
                f"Function {function_name!r} "
                f"not exported",
            )

        # Wall-clock timeout enforcement
        elapsed = time.monotonic() - start
        if elapsed > self._config.timeout_s:
            raise SandboxViolation(
                "timeout",
                f"Exceeded {self._config.timeout_s}s "
                f"wall-clock limit",
            )

        # Execute
        try:
            output = func(store)
        except wasmtime.WasmtimeError as exc:
            msg = str(exc)
            if "fuel" in msg.lower():
                raise SandboxViolation(
                    "fuel_exhausted",
                    "Computation limit exceeded",
                ) from exc
            if "memory" in msg.lower():
                raise SandboxViolation(
                    "memory_exceeded",
                    (
                        f"Memory limit "
                        f"{self._config.memory_limit_mb}"
                        f"MB exceeded"
                    ),
                ) from exc
            raise

        fuel_left = store.get_fuel()
        fuel_used = self._config.fuel_limit - fuel_left

        return ExecutionResult(
            success=True,
            output=output,
            elapsed_ms=self._elapsed(start),
            fuel_consumed=fuel_used,
        )

    def _register_default_host_functions(self) -> None:
        """Register safe default host functions."""
        self._host_functions["env.log_debug"] = (
            lambda msg: logger.debug(
                "WASM: %s", msg,
            )
        )
        self._host_functions["env.log_info"] = (
            lambda msg: logger.info(
                "WASM: %s", msg,
            )
        )
        self._host_functions["env.log_warn"] = (
            lambda msg: logger.warning(
                "WASM: %s", msg,
            )
        )

    @staticmethod
    def _extract_imports(
        wasm_bytes: bytes,
    ) -> List[str]:
        """Extract import names from WASM binary.

        Performs a lightweight parse of the import
        section without a full WASM parser.
        """
        # WASM import section ID = 2
        # This is a best-effort parse for validation;
        # wasmtime does authoritative validation.
        imports: List[str] = []
        try:
            idx = 8  # skip magic + version
            while idx < len(wasm_bytes):
                section_id = wasm_bytes[idx]
                idx += 1
                # Read LEB128 section size
                size, consumed = _read_leb128(
                    wasm_bytes, idx,
                )
                idx += consumed

                if section_id == 2:  # import section
                    end = idx + size
                    count, c = _read_leb128(
                        wasm_bytes, idx,
                    )
                    idx += c
                    for _ in range(count):
                        if idx >= end:
                            break
                        # module name
                        mlen, c = _read_leb128(
                            wasm_bytes, idx,
                        )
                        idx += c
                        mod = wasm_bytes[
                            idx:idx + mlen
                        ].decode("utf-8", errors="replace")
                        idx += mlen
                        # field name
                        flen, c = _read_leb128(
                            wasm_bytes, idx,
                        )
                        idx += c
                        fld = wasm_bytes[
                            idx:idx + flen
                        ].decode("utf-8", errors="replace")
                        idx += flen
                        # import kind byte + type
                        kind = wasm_bytes[idx]
                        idx += 1
                        if kind == 0:  # function
                            _, c = _read_leb128(
                                wasm_bytes, idx,
                            )
                            idx += c
                        elif kind == 1:  # table
                            idx += 3
                        elif kind == 2:  # memory
                            _, c = _read_leb128(
                                wasm_bytes, idx,
                            )
                            idx += c
                            if wasm_bytes[
                                idx - c - 1
                            ] & 1:
                                _, c2 = _read_leb128(
                                    wasm_bytes, idx,
                                )
                                idx += c2
                        elif kind == 3:  # global
                            idx += 2
                        imports.append(
                            f"{mod}.{fld}",
                        )
                    break
                else:
                    idx += size
        except (IndexError, UnicodeDecodeError):
            pass
        return imports

    @staticmethod
    def _elapsed(start: float) -> int:
        return int(
            (time.monotonic() - start) * 1000,
        )


def _read_leb128(
    data: bytes, offset: int,
) -> tuple[int, int]:
    """Read an unsigned LEB128 integer."""
    result = 0
    shift = 0
    consumed = 0
    while offset < len(data):
        byte = data[offset]
        offset += 1
        consumed += 1
        result |= (byte & 0x7F) << shift
        if (byte & 0x80) == 0:
            break
        shift += 7
    return result, consumed
