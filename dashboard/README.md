# Σ OVERWATCH Dashboard

Real-time monitoring dashboard for the **Σ OVERWATCH** agentic AI control plane.

## 🚀 Zero-Install Demo

Open the all-in-one demo directly in your browser — no build step, no dependencies:

➡ [`dashboard/demo.html`](./demo.html)

### Demo Features

| Feature | Description |
|---------|-------------|
| 🎨 Dark/Light Theme | Toggle with the theme button or press `T` |
| 🔍 Search & Filter | Search episodes by agent/ID, filter by status or severity |
| 📊 Sortable Tables | Click any column header to sort ascending/descending |
| 📈 System Health Gauge | SVG ring gauge showing overall system health |
| 🕸️ Radar Chart | Agent comparison radar for success rate & freshness |
| 📉 Area Charts | Gradient-filled area charts for deadline vs duration |
| 🍩 Donut Chart | Decision status distribution with inner ring |
| 🔔 Toast Notifications | Auto-popup alerts for high-severity drift events |
| ⌨️ Keyboard Shortcuts | `1-4` switch views, `R` refresh, `T` toggle theme |
| 📤 JSON & CSV Export | Download all data in either format |
| ♻️ Auto-Refresh | 5-second polling with toggle control |

## Features

### Overview
- **KPI Cards** — Success rate, average latency, drift events, active agents, system health
- **Deadline vs Actual Duration** — Area chart with gradient fills
- **Decision Status Distribution** — Interactive donut chart
- **Agent Comparison Radar** — Multi-axis radar for cross-agent metrics
- **Agent Performance** — Grouped bar chart (success rate + latency)
- **Drift Events by Type** — Horizontal bar chart breakdown

### Episodes
- Searchable, filterable, sortable table of the last 50 decision episodes
- Visual freshness progress bars with color-coded thresholds
- Status badges (success, timeout, degraded, failed)
- Real-time result count

### Drift Monitoring
- Severity summary cards (high / medium / low counts)
- Filterable drift event feed with severity dropdown
- Timestamps and patch hints on each event
- Toast notifications for high-severity drifts

### Export
- One-click JSON or CSV download
- Data summary with episode, drift, agent, and data point counts

## Tech Stack (Build Version)

| Tool | Purpose |
|------|---------|
| React 18 | UI framework |
| TypeScript | Type safety |
| Recharts | Charts (Area, Bar, Line, Pie, Radar) |
| Tailwind CSS | Styling |
| Vite | Dev server + build |
| Zustand | State management (planned) |
| Lucide React | Icons |

## Quickstart

```bash
cd dashboard
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Build

```bash
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
├── demo.html          # Zero-dependency all-in-one demo
├── index.html         # Vite entry point
├── package.json       # Dependencies
├── vite.config.ts     # Vite configuration
├── tsconfig.json      # TypeScript config
├── tailwind.config.js # Tailwind config
├── postcss.config.js  # PostCSS config
├── README.md          # This file
└── src/
    ├── App.tsx        # Main dashboard with all views
    ├── main.tsx       # React entry point
    ├── mockData.ts    # Data generators + TypeScript interfaces
    └── index.css      # Tailwind directives + dark theme
```
