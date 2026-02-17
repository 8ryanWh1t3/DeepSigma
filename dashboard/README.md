# Σ OVERWATCH Dashboard

Real-time monitoring dashboard for the **Σ OVERWATCH** agentic AI control plane.

## 🚀 Zero-Install Demo

Open the all-in-one demo directly in your browser — no build step, no dependencies:

➡ [`dashboard/demo.html`](dashboard/demo.html)

## Features

### Overview (Tab 1)
- **KPI Cards** — Success rate, average latency, drift events, active agents, system health
- **Deadline vs Actual Duration** — Area chart with gradient fills
- **Decision Status Distribution** — Interactive donut chart
- **Agent Comparison Radar** — Multi-axis radar for cross-agent metrics
- **Agent Performance** — Grouped bar chart (success rate + latency)
- **Drift Events by Type** — Horizontal bar chart breakdown

### Episodes (Tab 2)
- Searchable, filterable, sortable table with **pagination** (10/20/50/100 per page)
- Visual freshness progress bars with color-coded thresholds
- Status badges (success, timeout, degraded, failed)
- **Click any row** to open a detail modal showing all episode fields (AL6 score, action contract, data age, distance, variability, drag, etc.)
- Real-time result count with page navigation

### Drift Monitoring (Tab 3)
- Severity summary cards (high / medium / low counts)
- Filterable drift event feed with severity dropdown
- Timestamps and patch hints on each event
- **Toast notifications** for high-severity drifts (auto-dismiss after 6s)

### IRIS Query Panel (Tab 4)
- Natural-language query interface for the IRIS engine
- Query types: Why, What Changed, What Drifted, Recall, Status
- Structured response with provenance chain and decision lineage

### CoherenceOps Pipeline (Tab 5)
- DLR / RS / DS / MG pillar status cards with live indicators
- Knowledge Graph summary: node and edge counts by kind

### Memory Graph Visualization (Tab 6)
- **Force-directed SVG graph** of the Memory Graph (MG)
- Node types: episodes, actions, drifts, patches, evidence (color-coded)
- Edge types: produced, triggered, resolved_by, evidence_of, recurrence
- **Interactive**: drag nodes, pan canvas, zoom with scroll wheel
- Click a node to see its edge count and metadata

### Export (Tab 7)
- One-click JSON or CSV download
- Data summary with episode, drift, agent, and data point counts

### Global Features

| Feature | Description |
|---------|-------------|
| 🎨 Dark/Light Theme | Toggle with the theme button or press `T` |
| 🔍 Search & Filter | Search episodes by agent/ID, filter by status or severity |
| 📊 Sortable Tables | Click any column header to sort ascending/descending |
| 📈 System Health Gauge | SVG ring gauge showing overall system health |
| 🔔 Toast Notifications | Auto-popup alerts for high-severity drift events |
| ⌨️ Keyboard Shortcuts | `1-7` switch views, `R` refresh, `T` toggle theme |
| 📤 JSON & CSV Export | Download all data in either format |
| ♻️ Auto-Refresh | 5-second polling with toggle control |
| 📋 Pagination | Configurable page size for episodes table |
| 🔎 Episode Detail Modal | Click any episode row for full field breakdown |

## Tech Stack (Build Version)

| Tool | Purpose |
|------|---------|
| React 18 | UI framework |
| TypeScript | Type safety |
| Recharts | Charts (Area, Bar, Line, Pie, Radar) |
| Tailwind CSS | Styling (with class-based dark mode) |
| Vite | Dev server + build |
| Zustand | State management (planned) |
| Lucide React | Icons |

## Quickstart

```sh
cd dashboard
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Build

```sh
npm run build
```

Output in `dist/` — deploy to any static host.

## Data

Mock data generators produce realistic:

- **DecisionEpisodes** — 100 episodes with deadline/duration/status/freshness/AL6 scores/action contracts
- **DriftEvents** — ~15 events per refresh with type, severity, patch hints, delta, threshold
- **AgentMetrics** — 4 agents with success rate, latency percentiles, freshness, episode/drift counts

To connect real data, replace the generators in `src/mockData.ts` with API calls to your OVERWATCH backend.

## Project Structure

```
dashboard/
├── demo.html            # Zero-dependency all-in-one demo
├── index.html           # Vite entry point
├── package.json         # Dependencies
├── vite.config.ts       # Vite configuration
├── tsconfig.json        # TypeScript config
├── tailwind.config.js   # Tailwind config (dark mode: class)
├── postcss.config.js    # PostCSS config
├── coherence_mock_data.json
├── README.md            # This file
├── server/
│   └── api.py           # REST API endpoints
└── src/
    ├── App.tsx          # Main dashboard with all 7 views
    ├── CoherencePanel.tsx  # CoherenceOps pipeline panel
    ├── IrisPanel.tsx    # IRIS query panel
    ├── main.tsx         # React entry point
    ├── mockData.ts      # Data generators + TypeScript interfaces
    └── index.css        # Tailwind directives + dark/light theme
```
