# Build validation

Build: 1.0.0, 20 September 2026. Runtime exercised: Python 3.12.14 and Node.js 24.19.0 on Linux.

## Completed checks

- 27 Python behavior and loopback-server tests passed.
- Python and JavaScript outputs matched across 159 scenarios: 43 valid scenarios and 116 rejected malformed scenarios.
- Both JavaScript source files passed Node syntax checks; Python modules compiled.
- The CLI evaluated the bundled demonstration and the minimal one-claim example.
- The server tests exercised evaluation, health, assets, invalid JSON/schema, duplicate JSON keys, nonfinite values, origin/host restrictions, content type and file-path restrictions.

Reproduce the behavioral and parity checks from the extracted package:

```bash
python verify.py --require-node
```

Without Node, `python verify.py` runs Python tests and explicitly reports the parity skip. The package has no dependency on Node for normal Python or browser use.

## Bundled synthetic comparison

Inputs: 33 claims, 1,081 raw reports, 1,031 distinct report events, 50 duplicate copies, five discretionary review slots, and two mandatory alerts.

| Measure | Baseline | Compensated | Full control |
|---|---:|---:|---:|
| Labeled rare review targets selected | 1 / 5 | 5 / 5 | 5 / 5 |
| Claims labeled irrelevant selected | 4 / 26 | 0 / 26 | 0 / 26 |
| Mandatory alerts retained | 2 / 2 | 2 / 2 | 2 / 2 |
| Simulated release gate applied to view | No | No | Yes |

In Full control, four of the seven selected claims receive HOLD and three are simulated eligible. The cargo allegation receives HOLD because its supporting evidence has not been assessed; repeating it 50 times does not supply corroboration. The expired approval, contradiction, and missing required evidence each retain their distinct reasons.

The denominator 26 is the set labeled irrelevant to the discretionary review task. These counts are fixture outcomes, not estimates of Army operational performance. The full-control view has the same attention selection as Compensated; its additional result is the simulated gate status.

## Browser limitation

Browser visual and interaction testing was not completed in the build environment. Chromium was unavailable and its download failed with network errors/timeouts. JavaScript syntax and engine parity were checked, but those checks do not establish browser layout or end-to-end interaction quality.

Before relying on the console locally, check:

1. `python run.py` serves the page and the runtime badge reads Python localhost simulation.
2. All three tabs work; changing the budget preserves both mandatory alerts.
3. The cargo-allegation detail shows HOLD and unassessed-support reasons.
4. Exported JSON can be reimported; invalid JSON preserves the last result with an error.
5. `web/index.html` opens directly and identifies JavaScript offline simulation.
6. At a narrow window width, controls remain usable and tables can be scrolled.

This pilot has no production identity authentication or real release enforcement. Passing these checks does not validate source truth or real-world prevention.
