# Deep Sigma Zipf Compensator

**Version 1.0.0 · Synthetic pilot · RESONATOR supporting capability**

A working Python engine and JavaScript review console for comparing frequency-sensitive attention with a bounded rarity adjustment. Evidence and authority checks are evaluated separately from the ranking.

The bundle runs offline, contains its own demonstration data, and uses no LLM, API key, external service, CDN, or third-party Python package. It is an executable pilot, not a production authorization system.

## Start the console

1. Extract the ZIP.
2. Open a terminal in the extracted `deep_sigma_zipf_v1_0_0` folder.
3. Run:

```bash
python run.py
```

On systems where Python is named `python3`, use `python3 run.py`. On Windows, `py -3 run.py` works with the Python launcher; `start_windows.bat` is also included. On macOS/Linux, `sh start_unix.sh` starts the same server.

4. Open [http://127.0.0.1:8765](http://127.0.0.1:8765).

The server binds to the local machine only. Use `python run.py --port 8766` if the port is occupied. Stop with Ctrl+C. It does not save uploaded data or contact a remote server.

**Without Python:** open `web/index.html` directly in an evergreen browser. The console uses the JavaScript engine locally and clearly identifies that mode. File mode runs the same simulated checks; it is not a trusted approval boundary.

Python 3.10+ is the intended minimum; Node.js 18+ is optional for cross-language verification. The bundled build was exercised on Python 3.12.14 and Node.js 24.19.0; other versions require local verification. Internet access is unnecessary once the runtime is installed.

## What to inspect

- **Baseline:** a deliberately frequency-sensitive comparator for this experiment.
- **Compensated:** the same evidence with normalized concepts, deduplicated event counts and a bounded rarity bonus.
- **Full control:** the compensated selection plus explicit simulated evidence and authority results. A HOLD preserves the claim as unverified; it does not delete it or hide it from the reviewer.
- **Mandatory alerts:** always shown in a separate lane; they never consume the discretionary review budget.
- **Claim detail:** scoring reasons, original report count, distinct events, support origins, missing evidence types, excluded evidence and gate reasons.

Change the review budget, inspect selected claims, import your own scenario JSON, reset to the demonstration, or export the evaluation. The `as_of` time is an explicit scenario time, not the live clock, so expiry tests are reproducible.

The data includes 33 claims and 1,081 reports: 1,000 routine observations, five uncommon review targets, 50 copies of one allegation, six rare irrelevant distractors, and 20 observations for two mandatory alerts. The cargo allegation is entirely synthetic and is not a reconstruction of the reported Chinese-vessel incident.

## Run the engine without a browser

```bash
python evaluate.py data/demo.json --output result.json
python evaluate.py data/demo.json --budget 3 --as-of 2026-09-20T12:00:00Z
```

Python use:

```python
import json
from deep_sigma_zipf.engine import evaluate

with open('data/demo.json', encoding='utf-8') as stream:
    result = evaluate(json.load(stream))
print(result['modes']['full_control']['review_ids'])
```

JavaScript/Node use:

```javascript
const fs = require('node:fs');
const { evaluate } = require('./web/engine.js');
const scenario = JSON.parse(fs.readFileSync('./data/demo.json', 'utf8'));
console.log(evaluate(scenario).modes.full_control.review_ids);
```

## Verify the package

```bash
python verify.py
```

Verification exercises ranking, duplicate invariance, genuine recurrence, aliases, mandatory retention, source independence, review/authority failure states, evidence gaps and Python/JavaScript parity. Node is optional for Python use; if absent, the verifier reports that parity was skipped. The build's actual results are in [VALIDATION.md](docs/VALIDATION.md).

Run `python generate_demo.py` to regenerate `data/demo.json` and the offline `web/demo.js` wrapper from the readable scenario generator.

## Meaning and limits of the scores

Ratings for relevance, consequence and evidence quality are supplied scenario metadata. The engine does not infer those values from text. Concept aliases are explicit, not AI-generated ontology alignment. Source independence is declared using origin IDs; the program cannot prove that real sources are independent.

The baseline gives a capped popularity bonus to concepts with more distinct observed events. The compensated ranking replaces that bonus with a bounded inverse-frequency adjustment, only for claims that meet relevance and quality thresholds. Both retain all raw report records. Repeating one source/event pair cannot increase frequency weight or corroboration; independent recurring events remain counted.

The formula is an inspectable pilot heuristic informed by Zipf's Law, **not a fit of a Zipf distribution, an established risk estimator, or a proof of truth**. See [CONTRACT.md](docs/CONTRACT.md) for the full formula and data contract.

## What the simulated gate establishes

`ELIGIBLE` means that the supplied scenario metadata meets the configured rules. The UI labels it **Simulated eligible**. It requires assessed, current, version-matched support from enough declared independent origins, coverage of required evidence types, valid review metadata, and current authority metadata for the intended use. A contradiction or failed requirement produces `HOLD` with reasons.

These controls do not authenticate a reviewer, verify the truth of the cargo, validate a cryptographic signature, enforce classification rules, or publish/authorize anything downstream. An imported scenario can assert its own policy, identities and assessments. Both the JavaScript engine and local Python server are **simulation tools**, not trusted production approval services.

Production integration requires a separately trusted, versioned policy store; authenticated and scoped reviewers; validated evidence assessments and provenance; signed claim/evidence/approval bindings; current revocation checks; immutable audit; and enforcement at every release/consumer interface. Changes to evidence must invalidate the bound approval. The pilot binds approvals to claim and policy versions but does not fingerprint the evidence set. Do not promote this simulation to production by merely putting its server on a network.

The tool identifies missing evidence against explicitly required types. It cannot discover facts never collected. Common critical alerts are retained; rarity does not override mandatory rules. The full-control view does not change the ranking and therefore has the same attention-recall result as the compensated view; it adds a separate status decision.

## Evaluation interpretation

The bundled labels are visible and chosen for a synthetic experiment. They do not establish operational performance or demonstrate prevention of any historical incident. Labels never affect engine ranking or gate results. An operational pilot should use separately held evaluator truth, prespecified thresholds and representative data.

Rare-target recall uses labeled rare review targets as the denominator. A false positive is a selected discretionary claim labeled irrelevant to this particular review task. Routine reports labeled irrelevant in this scenario are not being declared intrinsically unimportant. Mandatory retention uses the labeled mandatory set and its own lane. Missing-evidence detection refers only to the seeded gaps.

## Package map

| Path | Purpose |
|---|---|
| `deep_sigma_zipf/engine.py` | Python validation, ranking and simulated gate |
| `web/engine.js` | Matching JavaScript evaluator |
| `web/index.html`, `styles.css`, `app.js` | Responsive offline review console |
| `data/demo.json`, `web/demo.js` | Synthetic scenario and direct-file wrapper |
| `data/minimal.json` | Small editable scenario with one eligible claim |
| `data/demo_result.json` | Reference output for the bundled demonstration |
| `run.py` | Loopback-only local server |
| `evaluate.py` | Command-line JSON evaluation |
| `verify.py`, `tests/` | Reproducible verification and parity checks |
| `generate_demo.py` | Readable synthetic-data generator |
| `docs/CONTRACT.md` | Exact schema semantics and formulas |
| `docs/ARCHITECTURE.md` | Integration boundaries and extension points |
| `data/scenario.schema.json` | JSON Schema for editor assistance |
| `docs/VALIDATION.md` | Results from this packaged build |
| `MANIFEST.sha256` | File integrity hashes for the distribution |

## Technical basis

- [Introduction to Information Retrieval — Zipf's Law](https://nlp.stanford.edu/IR-book/html/htmledition/zipfs-law-modeling-the-distribution-of-terms-1.html)
- [Introduction to Information Retrieval — Inverse document frequency](https://nlp.stanford.edu/IR-book/html/htmledition/inverse-document-frequency-1.html)

This implementation does not claim to implement standard TF-IDF. It uses the bounded, explicitly specified event-frequency adjustment in the contract.
