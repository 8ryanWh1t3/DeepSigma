# Deep Sigma Contrast v0.1.0 — Build Report

    ## Release gates
    - Unit tests: **PASS** — 15 tests
    - Python syntax compile: **PASS**
    - Import/API smoke test: **PASS**
    - CLI demonstration: **PASS**
    - `pyproject.toml` parse: **PASS**
    - Core third-party runtime dependencies: **0**
    - Autonomous APPLY / authority: **disabled by design**

    ## Test output

    ```text
    Spreadsheet runtime warmup failed during python startup
Traceback (most recent call last):
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/patches/warm_spreadsheet_runtime_on_startup.py", line 26, in warm_spreadsheet_runtime_on_startup
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/spreadsheet_warmup.py", line 785, in warm_spreadsheet_runtime
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/spreadsheet_warmup.py", line 720, in _warm_feature_flows
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/spreadsheet_warmup.py", line 704, in _warm_collaboration_flows
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/generated/interface/models.py", line 32317, in hydrate_crdt_from_proto
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/rpc/remote.py", line 749, in __call__
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/rpc/client.py", line 150, in call
artifact_tool.rpc.client.RemoteError: hydrateCrdtFromProto requires an empty collaborative document.
test_pathfinder_returns_comparable (test_adapters.AdapterTests.test_pathfinder_returns_comparable) ... ok
test_resonator_projects_findings (test_adapters.AdapterTests.test_resonator_projects_findings) ... ok
test_advisory_only (test_contrast.ContrastTests.test_advisory_only) ... ok
test_assumption_confidence_delta_detected (test_contrast.ContrastTests.test_assumption_confidence_delta_detected) ... ok
test_cerpa_never_auto_applies (test_contrast.ContrastTests.test_cerpa_never_auto_applies) ... ok
test_context_delta_detected (test_contrast.ContrastTests.test_context_delta_detected) ... ok
test_discriminating_factors_created (test_contrast.ContrastTests.test_discriminating_factors_created) ... ok
test_dsal_blocks_apply (test_contrast.ContrastTests.test_dsal_blocks_apply) ... ok
test_evidence_delta_detected (test_contrast.ContrastTests.test_evidence_delta_detected) ... ok
test_outcome_delta_detected (test_contrast.ContrastTests.test_outcome_delta_detected) ... ok
test_pair_generation_hard_negative (test_contrast.ContrastTests.test_pair_generation_hard_negative) ... ok
test_similarity_range (test_contrast.ContrastTests.test_similarity_range) ... ok
test_find_comparable (test_memory.MemoryTests.test_find_comparable) ... ok
test_in_memory_store (test_memory.MemoryTests.test_in_memory_store) ... ok
test_jsonl_roundtrip (test_memory.MemoryTests.test_jsonl_roundtrip) ... ok

----------------------------------------------------------------------
Ran 15 tests in 0.004s

OK

    ```

    ## Smoke output

    ```text
    0.1.0
ContrastEngine
to_cerpa_handoff
Spreadsheet runtime warmup failed during python startup
Traceback (most recent call last):
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/patches/warm_spreadsheet_runtime_on_startup.py", line 26, in warm_spreadsheet_runtime_on_startup
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/spreadsheet_warmup.py", line 785, in warm_spreadsheet_runtime
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/spreadsheet_warmup.py", line 720, in _warm_feature_flows
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/spreadsheet_warmup.py", line 704, in _warm_collaboration_flows
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/generated/interface/models.py", line 32317, in hydrate_crdt_from_proto
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/rpc/remote.py", line 749, in __call__
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/rpc/client.py", line 150, in call
artifact_tool.rpc.client.RemoteError: hydrateCrdtFromProto requires an empty collaborative document.

    ```

    ## Release invariant

    The library may identify similarities, material differences, discriminating factors,
    and proposed patch candidates. It may not originate institutional authority or APPLY
    authoritative changes.
