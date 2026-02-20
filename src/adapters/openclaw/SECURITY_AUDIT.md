---
title: "OpenClaw WASM Runtime Security Audit"
version: "1.0"
date: "2026-02-20"
---

# OpenClaw WASM Runtime Security Audit

## Scope

This document covers the security posture of the OpenClaw WASM
sandbox runtime (`adapters/openclaw/runtime.py`) for executing
untrusted third-party policy modules.

## Threat Model

| Threat | Mitigation | Status |
|--------|-----------|--------|
| Memory exhaustion | Configurable memory limit (default 64 MB) via wasmtime store limits | Implemented |
| CPU exhaustion | Fuel metering (default 500M units ~5s) + wall-clock timeout | Implemented |
| Filesystem access | WASI config with no preopened directories | Implemented |
| Network access | No network capabilities in WASI config | Implemented |
| Unauthorized imports | Import whitelist validation before instantiation | Implemented |
| Module injection | WASM magic number and size validation | Implemented |
| Host function abuse | Only 7 approved host functions, all read-only except emit_signal | Implemented |
| Process crash on limit | Graceful termination returning ExecutionResult with error | Implemented |

## Resource Limits

| Resource | Default | Configurable | Enforcement |
|----------|---------|-------------|-------------|
| Memory per module | 64 MB | `SandboxConfig.memory_limit_mb` | wasmtime Store.set_limits |
| CPU time | 500M fuel units (~5s) | `SandboxConfig.fuel_limit` | wasmtime fuel metering |
| Wall-clock timeout | 5 seconds | `SandboxConfig.timeout_s` | Python time.monotonic check |
| Module binary size | memory_limit_mb | Derived from memory limit | Pre-execution validation |

## Import Whitelist

Only the following host functions are permitted:

| Import | Purpose | Side Effects |
|--------|---------|-------------|
| `env.log_debug` | Debug logging | Append to log (non-destructive) |
| `env.log_info` | Info logging | Append to log |
| `env.log_warn` | Warning logging | Append to log |
| `env.get_claim` | Read a claim from the lattice | Read-only |
| `env.get_evidence` | Read evidence from the lattice | Read-only |
| `env.get_config` | Read policy configuration | Read-only |
| `env.emit_signal` | Emit a drift/governance signal | Write (controlled) |

Any import not in this list is rejected at validation time with
a `SandboxViolation(kind="import_denied")`.

## Access Controls

| Capability | Default | Override |
|-----------|---------|---------|
| Filesystem read | Denied | `SandboxConfig.allow_filesystem` |
| Filesystem write | Denied | `SandboxConfig.allow_filesystem` |
| Network inbound | Denied | `SandboxConfig.allow_network` |
| Network outbound | Denied | `SandboxConfig.allow_network` |
| Environment variables | Denied | Not configurable |
| System clock | Allowed | Via host functions only |

## Fuzzing Coverage

The test suite includes a fuzzing harness that validates:

- Random byte inputs (0-1000 bytes) never crash the runtime
- Malicious function names (empty, oversized, null bytes, path traversal) are handled safely
- Concurrent execution tracking is accurate
- All failure modes return structured `ExecutionResult` objects

## Recommendations

1. **Production deployment:** Set `fuel_limit` based on measured policy complexity
2. **Custom policies:** Require code review before adding to whitelist
3. **Monitoring:** Track `total_violations` and alert on spikes
4. **Updates:** Pin wasmtime version and audit changelogs for CVEs
5. **Periodic review:** Re-audit whitelist quarterly

## Test Coverage

| Test Class | Tests | Coverage |
|-----------|-------|---------|
| TestSandboxConfig | 4 | Configuration defaults and customization |
| TestWASMRuntime | 4 | Creation, config, host function registration |
| TestModuleValidation | 6 | Empty, invalid, oversized, imports |
| TestExecution | 5 | Graceful failures, result structure, counting |
| TestAccessControl | 4 | Filesystem/network deny/allow |
| TestImportWhitelist | 3 | Default contents, frozen set, custom |
| TestSandboxViolation | 2 | Exception attributes |
| TestLEB128 | 4 | Binary parsing utility |
| TestFuzzingHarness | 3+6 | Random inputs, malicious names, concurrency |
