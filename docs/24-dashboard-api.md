# Dashboard API

FastAPI server exposing DeepSigma episode, drift, and coherence data for the React dashboard.

The API server loads real DecisionEpisodes and DriftEvents from the sample corpus, runs the full `coherence_ops` governance pipeline (DLR / RS / DS / MG), and serves the results as JSON. Includes SSE streaming, IRIS query support, and webhook endpoints for SharePoint and Power Automate.

**Source:** `dashboard/api_server.py`

---

## Setup

```bash
pip install fastapi uvicorn
python dashboard/api_server.py
```

The server starts on `http://0.0.0.0:8000` by default. Set `PORT` to override.

---

## REST Endpoints

### `GET /api/health`

Aggregated health endpoint with readiness semantics.

```json
{
  "status": "ok",
  "ready": true,
  "draining": false,
  "persistence_ok": true,
  "persistence_detail": "ok",
  "inflight_requests": 0,
  "uptime_s": 12.1,
  "episode_count": 12,
  "drift_count": 5,
  "repo_root": "/path/to/DeepSigma"
}
```

`status` is `degraded` when persistence is unavailable or the service is draining.

### `GET /api/live`

Liveness probe. Returns `200` whenever the process is alive.

```json
{"status":"live","draining":false,"inflight_requests":0,"uptime_s":12.1}
```

### `GET /api/ready`

Readiness probe. Returns:
- `200` when persistence is available and the server is not draining
- `503` when persistence is unavailable or drain mode is active

Use this endpoint for load balancer readiness checks.

### `GET /api/episodes`

All DecisionEpisodes transformed to dashboard format. Returns an array of objects with fields: `episodeId`, `agentName`, `timestamp`, `deadline`, `actualDuration`, `status`, `freshness`, `dataAge`, `distance`, `variability`, `drag`, `decision`, `verification`, `outcome`, `actionContract`, `al6Score`.

### `GET /api/drifts`

All DriftEvents in dashboard format. Returns an array of objects with fields: `driftId`, `episodeId`, `type`, `severity`, `timestamp`, `patchHint`, `delta`, `threshold`.

### `GET /api/agents`

Per-agent metric aggregates. Returns an array with: `agentName`, `successRate`, `avgLatency`, `p95Latency`, `p99Latency`, `timeoutRate`, `degradedRate`, `averageFreshness`, `episodeCount`, `driftCount`.

### `GET /api/coherence`

Runs the full DLR/RS/DS/MG pipeline through `CoherenceScorer` and returns the scored report.

### `POST /api/iris`

IRIS query endpoint. Body (JSON):

```json
{
    "query_type": "WHY",
    "text": "Why did the agent abstain?",
    "episode_id": "ep-001",
    "decision_type": "classify"
}
```

Supported `query_type` values: `WHY`, `WHAT_CHANGED`, `WHAT_DRIFTED`, `RECALL`, `STATUS`.

### `GET /api/mg`

Memory Graph as JSON (`{nodes, edges}`).

---

## SSE Endpoint

### `GET /api/sse`

Server-Sent Events stream that multiplexes live data. Polls every 2 seconds and pushes when data changes.

| Event name | Payload |
|---|---|
| `episodes` | Array of dashboard episodes |
| `drifts` | Array of dashboard drifts |
| `agents` | Array of agent metrics |
| `mg` | Memory Graph JSON |

Keepalive comments (`: keepalive`) are sent between polls.

```javascript
const es = new EventSource("http://localhost:8000/api/sse");
es.addEventListener("episodes", (e) => setEpisodes(JSON.parse(e.data)));
es.addEventListener("drifts", (e) => setDrifts(JSON.parse(e.data)));
```

---

## Webhook Endpoints

### `POST /api/webhooks/sharepoint`

SharePoint Graph API webhook receiver.

- **Validation handshake:** Echoes `?validationToken` query parameter as `text/plain`.
- **Change notification:** Accepts Graph API change payloads. Logs notification count.
- **HMAC:** When `SP_WEBHOOK_SECRET` is set, verifies `X-SP-Signature` header.

### `POST /api/webhooks/powerautomate`

Power Automate webhook receiver.

- **Canonical records:** If payload contains `record_id` and `record_type`, passes through directly.
- **Raw Dataverse:** Otherwise, auto-transforms via `DataverseConnector._to_canonical()`.
- **HMAC:** When `PA_WEBHOOK_SECRET` is set, verifies `X-PowerAutomate-Signature` header.

---

## CORS Configuration

Default allowed origins:

```
http://localhost:3000
http://localhost:5173
http://127.0.0.1:3000
http://127.0.0.1:5173
```

Override with comma-separated list:

```bash
export CORS_ORIGINS="https://dashboard.example.com,http://localhost:3000"
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8000` | Server listen port |
| `CORS_ORIGINS` | localhost:3000,5173 | Comma-separated allowed origins |
| `SP_WEBHOOK_SECRET` | *(unset)* | HMAC secret for SharePoint webhook |
| `PA_WEBHOOK_SECRET` | *(unset)* | HMAC secret for Power Automate webhook |
| `DEEPSIGMA_DRAIN_TIMEOUT_S` | `5.0` | Max seconds to wait for in-flight requests during shutdown |
| `DEEPSIGMA_DRAIN_POLL_S` | `0.05` | Poll interval for in-flight drain loop |

---

## Files

| File | Path |
|---|---|
| Source | `dashboard/api_server.py` |
| Episode data | `examples/episodes/` |
| Drift data | `coherence_ops/examples/sample_drift.json` |
| This doc | `docs/24-dashboard-api.md` |
