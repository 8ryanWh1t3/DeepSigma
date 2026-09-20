# DEEP SIGMA Liddell Lens

Version 1.0.0 · A decision loss meter for the indirect approach

**Does changing the conditions before acting improve the outcome enough to justify the effort?**

Liddell Lens compares paired baseline and CERPA observations. It includes preparation and review costs, reports negative savings, and keeps unfinished decisions visible. It runs entirely on your machine, with matching JavaScript and Python calculation engines and an offline dashboard. It contains no AI service, telemetry, external packages, or network requests.

## Why Liddell Lens

The name draws on B. H. Liddell Hart's indirect approach: changing an opponent's physical and psychological balance before decisive engagement. He also discussed its wider application to human affairs. See [The Strategy of Indirect Approach, preface and chapter XI](https://archive.org/stream/strategyofindire035126mbp/strategyofindire035126mbp_djvu.txt).

Deep Sigma's adaptation asks which organizational conditions should change before more effort is committed. Shared definitions, evidence, authority, and correction are candidates to test. The code measures recorded workflow differences; it does not infer strategic success, optimize military operations, or certify evidence. **Liddell Lens is an original Deep Sigma name and implementation.**

The cycloid and electrical grid discussions are explanatory analogies. They supply no efficiency coefficients to this tool. All numbers come from imported observations or explicitly fictional examples.

## Run the dashboard

1. Extract the whole ZIP into a folder.
2. Open `index.html` in a modern browser. No server or installation is needed.
3. Choose an example, or import your own JSON matching `CONTRACT.md`.
4. Export the result as JSON or the per-case comparisons as CSV for Excel.

The three included examples show preparation paying off, overhead exceeding benefit, and incomplete decisions. **Every bundled dataset is illustrative, not measured Deep Sigma performance.** Imported data stays in browser memory until the page closes or you select another dataset. Download an input copy before making changes to preserve your data.

## Run Python

Python 3.9 or later; standard library only. Run these commands from the extracted folder:

```bash
python3 python/liddell_lens.py examples/benefit.json
python3 python/liddell_lens.py examples/benefit.json --output result.json --csv case_results.csv
```

On Windows, use `py -3` or `python` in place of `python3` if appropriate for your installation. Output directories must already exist. Invalid input returns exit code 2 with a field error. The CLI refuses to overwrite the input or send both outputs to the same file.

## Run JavaScript

The browser engine uses ordinary local scripts. The CLI uses Node.js built-ins only:

```bash
node js/cli.js examples/benefit.json
node js/cli.js examples/benefit.json --output result.json --csv case_results.csv
```

Embedding the calculation engine in another Node project:

```javascript
const { analyze } = require('./js/engine.js');
const input = require('./examples/benefit.json');
const report = analyze(input);
console.log(report.comparison.total_effort_minutes);
```

In a browser, use `LiddellLens.analyze(input)` after loading `js/engine.js`. Python users can place the `python` directory on their import path and call `from liddell_lens import analyze`.

## Collect observations consistently

Copy an example JSON, replace every illustrative record, set `data_kind` to `observed`, and use a descriptive title. Pair cases of comparable scope and complexity. A case ID identifies a matched comparison, not two independent tasks whose differences are assumed away. Consider counterbalanced replay or matched cohorts to limit learning and ordering effects. Record the measurement protocol before reviewing results.

For each run record:

| Field | Meaning |
|---|---|
| `elapsed_minutes` | Wall-clock time from intake to closure; for an open case, time to a common observation cutoff |
| `effort_minutes.preparation` | Person-minutes defining the task, meaning, and prerequisites |
| `effort_minutes.execution` | Person-minutes doing the work |
| `effort_minutes.review` | Person-minutes evaluating evidence, authorization, and corrections |
| `effort_minutes.clarification` | Person-minutes resolving questions and misunderstandings |
| `effort_minutes.rework` | Person-minutes repeating or correcting prior work |
| `clarification_cycles` | Number of recorded clarification exchanges under a consistent counting rule |
| `unresolved_contradictions` | Contradictions still unresolved at closure or cutoff |
| `closed`, `supported`, `authorized` | Explicit human assessments; each must be `true` or `false` |

Effort categories must not overlap. Sum time across people; two people working for 30 minutes consume 60 person-minutes. Wall-clock time and staff effort are separate measures. Allocate setup, training, evaluation, and collection costs consistently to the appropriate preparation/review category; disclose the allocation method outside the dataset. Retain the evidence behind the human assessments in your existing records.

## Read results correctly

Savings = baseline minus CERPA. Positive means less recorded consumption; negative means more. Percent saved divides that difference by the baseline; a zero baseline is **N/A**, not 0%. Total effort includes every category and every case. Preparation and review are costs, but are not automatically waste.

Elapsed time is compared only when **both runs** are closed, supported, and authorized. Excluded IDs and completion counts remain visible. A faster subset does not establish a better overall process when completion or support deteriorates. Contradictions remain a separate metric; a completed decision can still acknowledge unresolved issues.

There is no fabricated overall coherence score or automatic winner. Observed differences do not establish causation. Define acceptance criteria in advance, examine tradeoffs, and include the overhead of measurement itself.

## Verify the engines

```bash
python3 -m unittest discover -s tests -v
```

The suite checks known totals, overhead exceeding benefit, unfinished cases, zero baselines, invalid input, CSV text handling, CLI overwrite protection, and Python/JavaScript parity on examples and seeded varied records. Node.js must be available for the parity checks; set `NODE` to its executable path if needed. Without Node those checks are explicitly skipped.

## Files

`index.html`, `css/style.css`, `js/app.js`: offline dashboard. `js/engine.js` and `python/liddell_lens.py`: calculation engines. `js/cli.js`: Node CLI. `examples`: input datasets. `tests`: automated checks. `CONTRACT.md`: complete input and result contract.

CERPA means Claim → Event → Review → Patch → Apply. This first version measures a CERPA-informed workflow; it does not implement a claim ledger or enforce that lifecycle. Exported CSVs neutralize formula-like case IDs for spreadsheet viewing; result JSON retains original identifiers.
