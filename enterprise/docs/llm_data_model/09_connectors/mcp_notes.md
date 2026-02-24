# MCP Notes

How the LLM Data Model integrates with the Model Context Protocol (MCP) transport layer.

## Overview

MCP provides the communication channel between agents and the canonical store.  The LLM Data Model defines *what* flows through that channel; MCP defines *how*.

See `/adapters/mcp/` for the MCP JSON-RPC stdio server scaffold.

## MCP tools for data model operations

| MCP tool | Method | Description |
|---|---|---|
| `record_ingest` | `POST /records` | Submit a canonical record to the store |
| `record_get` | `GET /records/{record_id}` | Retrieve a single record by ID |
| `record_query` | `POST /records/query` | Hybrid search (vector + keyword + graph) |
| `record_patch` | `PATCH /records/{record_id}` | Append to patch_log |
| `graph_traverse` | `POST /graph/traverse` | Walk edges from a starting record |
| `graph_neighbors` | `GET /graph/{record_id}/neighbors` | Get immediate neighbors |
| `freshness_check` | `POST /records/freshness` | Batch TTL validation |
| `seal_verify` | `POST /records/verify` | Batch seal hash verification |

## MCP resource types

MCP resources expose read-only views of data model content:

| Resource URI | Description |
|---|---|
| `record://{record_id}` | A single canonical record |
| `schema://canonical_record` | The canonical record JSON Schema |
| `ontology://node_types` | Node type definitions |
| `ontology://edge_types` | Edge type definitions |
| `query://patterns/{id}` | Pre-defined query patterns (see `07_retrieval/query_patterns.md`) |

## MCP prompts

Pre-built prompts that agents can use to interact with the data model:

| Prompt | Input | Output |
|---|---|---|
| `assemble_context` | `decision_type`, `domain` | Set of fresh, high-confidence records for context assembly |
| `trace_decision` | `episode_record_id` | Full evidence tree via graph traversal |
| `check_contradictions` | `claim_record_id` | List of contradicting records |
| `freshness_report` | `domain` | Summary of expired vs. fresh records |

## Transport considerations

- MCP uses JSON-RPC over stdio for local tool execution.
- For remote canonical stores, the MCP server proxies requests to the ingest API.
- Responses include `record_id` references that can be used in subsequent MCP tool calls.
- Large result sets are paginated with `cursor` tokens.

## Alignment with existing MCP scaffold

The existing `/adapters/mcp/overwatch_mcp_server.py` exposes RAL primitives (DTE lookup, episode sealing, drift detection).  The data model MCP tools extend this with persistence and retrieval operations.  Both tool sets share the same MCP server instance.
