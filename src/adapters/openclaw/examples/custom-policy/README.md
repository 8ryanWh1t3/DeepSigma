# OpenClaw Custom Policy Example

This example demonstrates a custom WASM policy module and how to run it
through `WASMRuntime`.

## Policy

Rule: reject claims with confidence below `0.5`.

- `reject_low_confidence.rs` contains a sample Rust source implementation.
- `reject_low_confidence.wasm` is a precompiled demo binary checked in so the
  example works without installing a Rust toolchain.
- `import_demo.wasm` demonstrates host import usage for:
  - `env.get_claim`
  - `env.emit_signal`

## Run

```python
from adapters.openclaw.examples.custom_policy import evaluate_claim_policy

print(evaluate_claim_policy(0.9))  # allow
print(evaluate_claim_policy(0.2))  # reject
```

If `wasmtime` is not installed, the returned decision includes
`runtime_success=false` with the runtime error message.

## Import Whitelist Controls

`import_demo.wasm` intentionally imports `env.get_claim` and `env.emit_signal`.
`WASMRuntime.validate_module()` will reject this module if these imports are
removed from `SandboxConfig.import_whitelist`.
