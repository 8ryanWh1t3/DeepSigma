# VINCULUM pyLib v0.6.0
## Cross-Order Hinge & Codec Evaluation

**When words and numbers collide.**

Each language or mathematical representation can carry probabilistic and deterministic elements at any examination order. A hinge belongs to a selected pair; it is never a third independent source of truth. VINCULUM compares representations, not reality itself.

This release implements the two approved architecture graphics as a typed, testable library. Their “2.0” captions were concept labels. The package release continues from the verified v0.5.2 baseline as **0.6.0**.

## What is new

- Order-aware `Representation` objects on either L or M, with independent P/D descriptors, numeric bounds, scope, support factors and dependence links.
- Explicit `PairGraph` selection across orders: L1 may pair with M4. Five-by-five is the default view, not a requirement that all 25 positions be compared. Higher orders extend the view.
- Pair-local `HingeOrderState` objects: the hinge itself can have P/D descriptors and support at order k, attached only to that pair.
- Required identity, concept, unit, population, denominator, granularity and time checks. Missing information is unresolved; established incompatibility is not a numeric conflict.
- Exact numeric points, bounded intervals, open/closed inequalities and registered unit conversion. Uncertainty does not rewrite observed values.
- Five distinct outcomes: ALIGNED, PARTIAL, CONFLICT, UNRESOLVED, NOT_COMPARABLE. UNPAIRED is a matrix position, not an evaluated outcome.
- Raw collision, support, coverage and support-weighted indication remain separate. P/D balance is not used as a contradiction detector.
- A bounded, in-memory pairing monitor proposes candidate pairs; explicit application selection precedes evaluation. No operational sensor connector is implied.
- Codec-preservation checks for declared material source/target representations: changed values, scope changes, narrowed uncertainty, omitted material and unsupported additions.
- JSON scenarios, native Turtle round-tripping, explicitly mapped generic RDF, Excel-ready CSV tables, optional XLSX export and accessible offline HTML reports.
- Non-scored origin/retreat narrative context. No numeric scores for God, nature, presence or spiritual retreat.
- The original v0.5.2 API and its tests remain available unchanged in the legacy modules. New work should use `CrossOrderEngine` / `PairGraph`.

## Install

```bash
python -m pip install dist/vinculum_pylib-0.6.0-py3-none-any.whl
```

Python >=3.10 is declared; this build was executed on the Python version recorded in VALIDATION.md, not a full multi-version matrix. Runtime dependency: RDFLib >=7.0. No LLM, cryptographic root or authority service is required. New scalar comparison modules use the standard library. RDFLib is retained for old and new Turtle paths.

## Small, explicit example

```python
from vinculum import (
    PairGraph, Scope, SemanticRegistry, measurement,
)

scope = Scope(
    scope_id="order-1", population="cookies",
    denominator="one order", granularity="receipt line",
    timeless=True,  # explicitly a static transaction comparison, not a live feed
)
words = SemanticRegistry.default().representation(
    "baker's dozen", id="L1", entity="order-1", scope=scope,
)
record = measurement(
    id="M1", entity="order-1", concept="item_count",
    value=12, unit="count", scope=scope,
    defense=0.99, defense_basis="illustrative coefficient, not measured calibration",
)

graph = PairGraph("BAKERY")
graph.add_node(words).add_node(record)
graph.add_pair(
    "L1", "M1", rationale="same order and same receipt line",
    alignment_support=1.0, alignment_basis="explicit demonstration identity contract",
)
report = graph.evaluate()
pair = report.pairs[0]
print(pair.status.value)                       # CONFLICT
print(pair.discrepancy["signed_delta"])        # -1
print(pair.raw_collision_score)                # 100
print(pair.supported_collision_score)          # 99 (default bottleneck model)
```

The observed quantity stays **12**. Lowering defense to .42 changes the support-weighted indication to 42 but leaves CONFLICT, the raw score 100 and delta -1 unchanged. Missing defense produces a missing supported score, not zero risk or full confidence.

## Run the full cross-order demonstration

```bash
vinculum-lattice evaluate examples/cross_order_scenario.json --out-dir my_report --summary
python examples/cross_order_demo.py
python examples/pairing_monitor.py
```

The synthetic codec fixture evaluates all five language orders and all five mathematical orders using nine deliberately selected pairs. It preserves zero detections, catches a 100%-versus-60% coverage mismatch, separates detection from actual presence, and tests confidence, interval uncertainty, age and source dependence.

Open `demo_output/report.html` for the delivered result. It contains a clickable order matrix, pair checks, support drivers, coverage, the codec audit and optional non-scored context. It has no external resources or executable JavaScript.

## CLI

```bash
vinculum-lattice --version
vinculum-lattice evaluate scenario.json --summary
vinculum-lattice evaluate scenario.ttl --out-dir output
vinculum-lattice evaluate scenario.json --strict-exit
vinculum-lattice convert scenario.json scenario.ttl
vinculum-lattice convert scenario.ttl scenario.json
vinculum-lattice monitor events.jsonl
```

Default evaluation returns exit 0 when the run completes, even when it finds conflicts. `--strict-exit` returns 2 unless the result is aligned and gap-free; input errors return 1. The monitor emits proposals only and does not turn a match score into a probability.

## Excel

Portable, dependency-light export: `vinculum.report.write_csv(report, directory)` writes five Excel-ready tables. A six-sheet example XLSX is also supplied in `demo_output/`.

`vinculum.excel.export_xlsx` is an optional adapter for environments that provide `artifact_tool`. That spreadsheet runtime is **not** installed by pip as a package dependency. Ordinary installations can always use CSV, JSON and HTML.

## Compatibility

```python
# Kept for legacy callers and historical score reproduction:
from vinculum import VinculumEngine, ingest_text
old_style_result = VinculumEngine().score(ingest_text("This may be true."))

# Canonical cross-order path for new work:
from vinculum import CrossOrderEngine
new_report = CrossOrderEngine().evaluate(graph)
```

The old API still has its historical heuristic baselines and terminology. Do not interpret its `tension_balance` as the new pairwise collision metric. See MIGRATION_V0_5_2_TO_V0_6_0.md.

## Boundaries

This is a tested reference library, not a certified safety system. It does not understand arbitrary prose automatically, prove physical truth, identify hostile objects, command actions or establish authority. A “clear airspace” rule is domain-dependent and is deliberately **not** in the default new lexicon. An application must define the measurand, time, population, coverage and appropriate source support.

See ARCHITECTURE.md, SCORING_MODEL.md, HINGE_CONTRACT.md, CODEC.md, MONITOR.md, GRAPHIC_TRACEABILITY.md, SECURITY.md and VALIDATION.md.
