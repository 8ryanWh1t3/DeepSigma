# OpenClaw Adapter (Scaffold)

Goal: route OpenClaw skill execution through Σ OVERWATCH governance.

## Intended behavior
- skill/tool call → Overwatch tool proxy
- state-changing skill → Safe Action Contract enforcement
- verification required above thresholds
- always seal DecisionEpisode + emit drift on failure

This directory is a scaffold for the adapter implementation.

## Custom Policy Example

A zero-toolchain demo bundle is available at:

- `src/adapters/openclaw/examples/custom-policy/`

It includes:

- sample source (`reject_low_confidence.rs`)
- precompiled modules (`reject_low_confidence.wasm`, `import_demo.wasm`)
- Python helper (`adapters.openclaw.examples.custom_policy`)
- tests (`tests/test_openclaw_custom_policy_example.py`)
