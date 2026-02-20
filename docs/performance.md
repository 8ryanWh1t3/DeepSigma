# Performance Characteristics

Exhaust pipeline throughput and memory benchmarks validated at 10k, 50k, and 100k evidence nodes.

## Pipeline Throughput

| Operation | 1k nodes | 10k nodes | 50k nodes | 100k nodes |
|-----------|----------|-----------|-----------|------------|
| `extract_truth` | < 0.1s | < 1s | < 5s | < 10s |
| `extract_reasoning` | < 0.1s | < 1s | < 5s | < 10s |
| `extract_memory` | < 0.1s | < 0.5s | < 2s | < 5s |
| `detect_drift` (canon lookup) | < 0.1s | < 1s | < 5s | < 10s |
| `score_coherence` | < 0.01s | < 0.5s | < 1s | < 2s |
| Full pipeline (extract → drift → score) | < 0.5s | < 5s | < 15s | < 30s |
| Trust Scorecard generation | < 0.1s | < 1s | < 1s | < 1s |

## Memory Usage

### JSONL Export — Streaming vs Load-All

| Approach | 10k records | 100k records | 1M records |
|----------|-------------|--------------|------------|
| `_read_jsonl()` (load-all) | ~5 MB | ~50 MB | ~500 MB |
| `_iter_jsonl()` (streaming) | ~1 KB | ~1 KB | ~1 KB |
| `_count_jsonl()` (count-only) | ~1 KB | ~1 KB | ~1 KB |

Streaming helpers (`_iter_jsonl`, `_count_jsonl`) use bounded memory regardless of file size. Use them for:

- Health endpoint event/drift counting
- Drift signal listing with filters
- Building lookup sets (e.g., drift episode IDs)

Load-all (`_read_jsonl`) is still needed when the full list must be manipulated (assembly, commit).

## Complexity Analysis

| Function | Time Complexity | Space Complexity |
|----------|----------------|------------------|
| `extract_truth` | O(E × L) | O(C) |
| `extract_reasoning` | O(E × L) | O(R) |
| `extract_memory` | O(E) | O(M) |
| `detect_drift` | O(N + T + M) | O(N) |
| `score_coherence` | O(T + R + M + D) | O(1) |

Where:
- **E** = number of events in episode
- **L** = average lines per event payload
- **C** = unique claims (deduplicated)
- **R** = unique reasoning items
- **M** = unique memory items
- **N** = canon entries in memory graph
- **T** = extracted truth items
- **D** = drift signals

## SLO Reference

| SLO | Threshold | Validated At |
|-----|-----------|--------------|
| IRIS query resolution | < 60s | 100 episodes |
| Drift detection latency | < 5s | 10k canon entries |
| Trust Scorecard generation | < 5s | 10k nodes |
| Full pipeline (1k events) | < 10s | 1k events |
| Full pipeline (10k events) | < 15s | 10k events |
| JSONL streaming (100k) | < 10s | 100k records |

## Production Recommendations

1. **Use streaming helpers** for read-heavy endpoints. The `_iter_jsonl()` and `_count_jsonl()` functions avoid loading entire JSONL files into memory.

2. **Canon caching** — `detect_drift()` re-reads the memory graph on each call. For batch refinement of multiple episodes, load canon once and pass it via `canon_path`.

3. **Episode size** — Rule-based extraction scales linearly with event count. Episodes under 1k events complete refinement in under 1 second. Larger episodes (10k+) still complete within SLO but benefit from streaming.

4. **Storage backend** — For production deployments exceeding 100k records, consider the SQLite or PostgreSQL storage backends (see `coherence_ops/storage.py`) which provide indexed queries and ACID guarantees.

5. **JSONL compaction** — Use `deepsigma compact` to tier old evidence into warm/cold archives, keeping hot-tier files small for fast reads.
