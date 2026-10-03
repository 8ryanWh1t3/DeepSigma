# Σ VINCULUM — Navigable Fold Add-on v0.1.0

**Time orders. Words express. Numbers measure. Folding connects. Unfolding explains.**

An additive Python package for the VINCULUM pyLib workflow. It turns the conceptual
Navigable Fold into versioned, inspectable episode data with the four Journey into
Truth (JIT) lenses, evidence links, replayable navigation and an explicit local
snapshot journal.

**Distribution:** `vinculum-folding`  
**Import:** `vinculum_folding`  
**Host target:** source-inspected VINCULUM pyLib **0.7.0**, at the exact serialization
contract recorded in `docs/BASELINE.json`.  
**Core change:** none. This package neither installs into the `vinculum` namespace
nor changes the original comparison/scoring code.  
**Runtime dependencies:** Python standard library only. Python >=3.10 is the
syntax target; the recorded execution environment is Python 3.13.5.

## Install and run

From the extracted release folder:

```bash
python -m pip install --no-deps dist/vinculum_folding-0.1.0-py3-none-any.whl
vinculum-fold demo --out fold_demo
vinculum-fold inspect fold_demo/episode.json
vinculum-fold unfold fold_demo/episode.json summary-derivation
vinculum-fold verify fold_demo
```

Use a new output directory on each export. Existing output is not overwritten.

The synthetic inspection demo produces `SCOPE_EXPANSION_REVIEW` for the declared
transition from **“the inspection recorded three defects”** to **“only three
defects existed.”** The rule compares explicit `RECORDED` and `EXHAUSTIVE` scope
annotations on a `DERIVED_FROM` relationship. It does **not** infer scope from
arbitrary prose or establish whether either claim is factually true.

## What is implemented

| Capability | Implemented behavior |
|---|---|
| Three aspects | Typed TIME, WORDS and NUMBERS values within one episode identity |
| Origami folds | Explicit directed links, rationale, evidence and counterfold relations |
| JIT 4D | Exactly Legacy of Precision, Density of Exposure, Matrix of Awareness, Ontological Grade on each fold |
| Awareness | Attributed Evaluation, Potency, Activity and viewpoint; no scoring of people |
| Ontological Grade | User-defined Grade-1 Vector / Grade-2 Bivector categories, or UNSPECIFIED; not geometric calculations or truth rankings |
| Precision | Original wording, exact numeric strings/fractions, units and explicit timezone offsets survive serialization |
| Evidence | Source IDs, original locators when supplied, optional SHA-256 and declared root groups |
| Inspector data | Read-only `view.json` for a host canvas, plus `unfold()` evidence recovery |
| Navigation | Adjacent-link traversal, return path, exact-world replay, bounded neighborhoods |
| Cross-episode links | Explicit episode + revision + node targets; missing targets remain unresolved |
| Revision memory | Immutable snapshots, predecessor content hash and revision diffs |
| Local persistence | Explicit SQLite creation; read-only default; append transactions and consistency checks |
| CERPA | CLAIM/EVENT/REVIEW/PATCH/APPLY references and a **non-executing REVIEW handoff** |
| Institutional artifacts | DLR / RS / DS / MG references without inventing their contents |
| Host adapter | Copies full serialized scenario + pipeline result and preserves every original selected-pair result |

The five host pair outcomes stay separate: **ALIGNED, PARTIAL, CONFLICT,
UNRESOLVED, NOT_COMPARABLE**. Unpaired host nodes remain without a selected-pair
result. Time is a sidecar aspect; it does not create a third side in the existing
L/M comparison matrix. Host P/D, order, hinge data and fingerprints remain intact.

## Add to the existing pipeline

The host package must already be installed. The adapter performs no installation,
network calls, evaluation or operational action.

```python
from datetime import datetime, timezone
from pathlib import Path

from vinculum import VinculumPipeline
from vinculum_folding import from_pipeline, export_bundle

# Run the ordinary host job exactly as before.
run = VinculumPipeline().run_file(Path("your_existing_job.json"))

# Add a separate, inspectable episode without changing the host result.
episode = from_pipeline(
    run,
    episode_id="EP-001",
    mission_id="MISSION-001",
    title="Mission assessment and its evidence",
    recorded_at=datetime.now(timezone.utc).isoformat(),
)
export_bundle(episode, "fold_output")
```

The inspected source exposes `run.to_dict()` and `run.scenario.to_dict()`. The
adapter verifies the returned **schema and version**, checks representation/pair
identity consistency and retains both serialized objects in `host_capture`.
Time nodes are projected only from explicit host `scope.window` fields. Missing
source metadata stays missing, missing numeric meaning stays `null`, and all new
JIT lenses initially remain `UNASSESSED`. Grade and exhaustive coverage are never
inferred from a host side or a number.

**Integration status:** the source contract and synthetic adapter cases were
checked here. The full host distribution could not be mounted, so the real-host
smoke test is included but **not claimed as passed**. The base library's original
regression suite was **not rerun**. Run `tests/test_host_integration.py` in the
actual host environment before release integration. See `docs/COMPATIBILITY.md`.

## Navigate, return, replay

```python
from vinculum_folding import FoldWorld, NodeRef
from vinculum_folding.demo import inspection_demo

snapshot = inspection_demo()
world = FoldWorld([snapshot])
origin = world.start(NodeRef(snapshot.episode_id, snapshot.revision, "summary"))
step = world.links(origin.current)[0]
focused = world.follow(origin, step)
assert focused.current.node_id == "observation"
assert world.back(focused) == origin
assert world.replay(focused.to_dict()) == focused
```

Traversal follows recorded links only. Changing the world invalidates the old
world-bound trail. Cross-episode links never silently choose a latest revision.
A neighborhood is recorded relationship reach, not complete causal impact.

## Prepare and preserve a revision

```python
from vinculum_folding import EpisodeJournal
from vinculum_folding.demo import inspection_demo

original = inspection_demo()
revised = original.revise(
    recorded_at="2026-10-03T11:00:00-04:00",
    title="Review captured; outcome still unverified",
)

# Only explicit creation/writer access can append snapshots.
with EpisodeJournal.create("episodes.sqlite") as journal:
    journal.append(original)
    journal.append(revised)
    journal.verify(original.episode_id, expected_tip=revised.digest)

# Opening a journal defaults to a read-only SQLite connection.
with EpisodeJournal.open("episodes.sqlite") as inspector:
    replayed = inspector.get(original.episode_id, revision=1)
    assert replayed == original
```

This is a **local content journal**, not the trusted COMPOSER repository, a CERPA
state machine or a root-of-trust service. A person able to rewrite all database
bytes can recompute all hashes. Rollback detection against external history needs
an independently protected expected tip. The tests demonstrate this limitation
rather than treating a hash as authority.

## Export contract

Each fresh bundle contains:

- `episode.json`: complete snapshot, including any exact serialized host capture.
- `view.json`, `audit.json`, `review_input.json`: reproducible read-only projections.
- `READ_ME.md`, `manifest.json`: boundaries and unsigned content checksums.

`verify_bundle()` checks byte hashes, episode identity and regenerated projections.
It does not authenticate a source, validate physical observations, rerun the host
pipeline or authorize a decision. Full host re-execution still requires the
original job, source files and runtime. No spreadsheet, PDF or UI dependency is
introduced by this add-on.

## Validation

```bash
python -m pytest -q
# In an environment containing the actual supported host package:
python -m pytest -q tests/test_host_integration.py
```

Recorded results, test names, interpreter details, installed-wheel checks and
limitations are in `validation/`. A skipped host test is not a passed integration
test. Windows, macOS and other Python interpreters were not executed here.

## Deliberate boundaries

This release is **backend/data-contract code**, not a newly rendered radial
VINCULUM UI. It has no live connection to VINCULUM World/Studio, enterprise
PATHFINDER/RESONATOR/COMPOSER binaries, Lattice, Foundry, Vantage or an operational
CERPA service. Those hosts can consume the view and review contracts after their
own access-control and integration work.

No general-language semantic parser, automatic proof of truth, composite JIT
score, people score, actuation, authorization, classification downgrade, source
signature verification, physical time reversal or mathematically demonstrated
Folding Maximum is provided. JSON is data; the library does not evaluate code,
load user-named plugins or follow source URLs.

**Origami connects. JIT examines. VINCULUM reveals. CERPA preserves.**
