# Σ OVERWATCH Dashboard

Real-time monitoring dashboard for the Σ OVERWATCH agentic AI control plane.

## Zero-Install Demo

**No build step required.** Open [`demo.html`](demo.html) in any browser for the full dashboard experience:

```bash
# Clone and open — that's it
open dashboard/demo.html
```

Or download just the single file from GitHub and double-click it. The demo loads React + Recharts from CDN and runs entirely client-side with generated mock data. All 4 views (Overview, Episodes, Drift, Export) work out of the box with auto-refreshing data.

## Features

- **Overview** — KPI cards (success rate, avg latency, drift events, active agents), deadline vs duration trend chart, decision status pie chart, agent performance bar chart, drift distribution
- - **Episodes** — Tabular view of recent DecisionEpisodes with status, deadline, duration, freshness, and outcome
  - - **Drift** — Live drift event feed with severity coloring, patch hints, and episode correlation
    - - **Export** — One-click JSON export of all episodes, drifts, and agent metrics
     
      - ## Tech Stack
     
      - - React 18 + TypeScript
        - - Vite (dev server + build)
          - - Tailwind CSS (dark theme)
            - - Recharts (charts/graphs)
              - - Lucide React (icons)
                - - Zustand (state management, ready for extension)
                 
                  - ## Quick Start
                 
                  - ```bash
                    cd dashboard
                    npm install
                    npm run dev
                    ```

                    Opens at `http://localhost:3000`.

                    ## Build

                    ```bash
                    npm run build
                    ```

                    Output in `dist/`.

                    ## Data

                    Currently uses generated mock data (`src/mockData.ts`) that simulates:
                    - 100 DecisionEpisodes with realistic timing, freshness, and status distributions
                    - - Drift events (~15% of episodes) with severity levels and patch hints
                      - - Per-agent metrics (success rate, latency percentiles, freshness)
                       
                        - Auto-refreshes every 5 seconds (toggleable).
                       
                        - ## Connecting to Real Data
                       
                        - Replace the mock data generators in `App.tsx` with API calls to your Overwatch backend:
                       
                        - ```typescript
                          // Replace generateMockEpisodes() with:
                          const response = await fetch('/api/episodes');
                          const episodes = await response.json();
                          ```

                          ## Project Structure

                          ```
                            demo.html             # Zero-install single-file demo (just open in browser)
                          dashboard/
                            index.html            # Entry HTML
                            package.json          # Dependencies
                            vite.config.ts        # Vite configuration
                            tsconfig.json         # TypeScript config
                            tailwind.config.js    # Tailwind CSS config
                            postcss.config.js     # PostCSS config
                            src/
                              main.tsx            # React entry point
                              App.tsx             # Main dashboard component
                              mockData.ts         # Demo data generator
                              index.css           # Tailwind + global styles
                          ```
