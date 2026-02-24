# Indexing Strategy

Three retrieval patterns work together: **vector search**, **keyword search**, and **graph traversal**.  This document defines what gets indexed, how, and why.

## Vector index

Semantic similarity search over record content and provenance.

| Index name | Fields indexed | Embedding model | Dimension | Refresh |
|---|---|---|---|---|
| `content_vector` | `content` (serialized to text) | text-embedding-3-small (or equivalent) | 1536 | On ingest + on patch |
| `provenance_vector` | `confidence.explanation` + `provenance.chain[*].statement` | Same | 1536 | On ingest |

**Chunking**: Records are embedded whole (not chunked) because each canonical record is a self-contained unit.  If `content` exceeds 8192 tokens, split into overlapping chunks of 4096 tokens with 512-token overlap, linking chunks back to the parent record_id.

**Metadata attached to vectors**: `record_id`, `record_type`, `labels.domain`, `confidence.score`, `observed_at`, `ttl`.  This enables metadata filtering during vector search.

## Keyword index

Exact-match and full-text search over structured fields.

| Index name | Fields | Type | Use case |
|---|---|---|---|
| `record_type_idx` | `record_type` | Exact match | Filter by type |
| `domain_idx` | `labels.domain` | Exact match | Filter by business domain |
| `sensitivity_idx` | `labels.sensitivity` | Exact match | Access control filtering |
| `tags_idx` | `labels.tags[]` | Multi-value exact | Tag-based filtering |
| `source_system_idx` | `source.system` | Exact match | Trace by source |
| `actor_idx` | `source.actor.id` | Exact match | Trace by actor |
| `content_fts` | `content` (flattened text) | Full-text search | Keyword search within payloads |
| `created_at_idx` | `created_at` | Range | Time-range queries |
| `observed_at_idx` | `observed_at` | Range | Freshness queries |

## Graph index

The knowledge graph is formed by `links[]` edges.  Index for efficient traversal.

| Index name | Fields | Type | Use case |
|---|---|---|---|
| `outbound_edges` | `record_id` → `links[].target` | Adjacency list | Forward traversal |
| `inbound_edges` | `links[].target` → `record_id` | Reverse adjacency | Backward traversal (who links to me?) |
| `edge_type_idx` | `links[].rel` | Exact match | Filter edges by type |

## Hybrid query execution

Most queries combine all three patterns:

1. **Vector search** produces a candidate set ranked by semantic similarity.
2. **Keyword filters** narrow the candidate set by type, domain, tags, time range.
3. **Freshness gate** excludes records where `observed_at + ttl < now()`.
4. **Graph expansion** follows edges from the candidate set to discover related records.
5. **Re-rank** using a weighted score: `0.4 * vector_score + 0.3 * keyword_score + 0.2 * graph_proximity + 0.1 * confidence.score`.

## Index maintenance

- **On ingest**: record is indexed in all three systems atomically (or with eventual consistency < 5s).
- **On patch**: vector embedding is recomputed; keyword index is updated; graph edges are updated.
- **TTL sweep**: a background job runs every 15 minutes, marking expired records as `stale` in all indexes.  Stale records are excluded from default queries but remain queryable with `include_stale=true`.
- **Compaction**: records that have been stale for > 30 days are archived to cold storage and removed from hot indexes.
