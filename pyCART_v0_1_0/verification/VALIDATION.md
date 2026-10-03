# CARTOGRAPHY 0.1.0 — executed validation

**Disposition: tested development release. Not a production authorization certification.**

## Results

| Check | Executed result |
|---|---|
| Pytest suite | **127 passed, 0 failed, 0 errors, 0 skipped** |
| Interpreter | Python **3.13.5**; other declared 3.10+ interpreters were not exercised |
| Clean wheel | Installed offline into isolated venv; only pip and deepsigma-cartography installed |
| Clean demo | Ran through installed wheel using isolated `python -I` |
| Source / wheel identity | Every package source file byte-compared to installed wheel payload |
| Native adapter | Actual supplied DeepSigma 2.1.2 MemoryGraph export consumed |
| Native CERPA contracts | Actual Review/Patch constructors accepted generated draft dictionaries |
| RDF interoperability | JSON-LD and N-Triples independently parsed to the same RDF graph |
| Schema | Published JSON Schema validated; unsupported authoritative flag rejected |
| Archive | Positive and negative tests include separate-process restart, stale writers, corruption, failed writes, and pinned-head rollback detection |
| Optional Excel | artifact_tool build, key-range inspection, formula scan, dashboard rendering, date-format check, XLSX export; **11 sheets** |

The workbook check was executed separately and is **not included in the 127 pytest count**.
The coverage report likewise does not include the separately exercised workbook or isolated CLI subprocesses.
One non-fatal warning came from RDFLib's JSON-LD parser using its deprecated ConjunctiveGraph class.
Exact test cases and timings are in `junit.xml`; console output is in `pytest.txt`.

## Synthetic acceptance thread

The sample is explicitly synthetic: 10 nodes, 8 relationships, 6 baseline review findings.
The mission-to-evidence route has 3 hops. The proposed candidate resolves 3 findings while
leaving the unknown claim, missing evidence, and isolated node visible. Two map editions are
retained. Neither the candidate nor an archived edition grants authority or executes APPLY.

## Reproduction

From the source-package root, install development test dependencies and run:

```bash
python -m pip install ".[dev]" rdflib jsonschema
python -m pytest -q
```

The two native integration tests require the supplied DeepSigma snapshot's `src/` on PYTHONPATH.
Without it those tests skip. RDFLib and jsonschema tests skip when those optional test dependencies
are absent. These test libraries are not core runtime requirements. The native snapshot is not
redistributed in this package; its file hashes are in `baseline.json`.

Recorded full-run command in this build environment:

```bash
PYTHONPATH=$PWD/src:/mnt/data/_cartography_baseline/src \
  python -m coverage run --branch --source=deepsigma_cartography \
  -m pytest -q --tb=short --junitxml=verification/junit.xml
```

Clean install and execution:

```bash
python -m venv .venv
.venv/bin/python -m pip install --no-index --no-deps dist/deepsigma_cartography-0.1.0-py3-none-any.whl
.venv/bin/python -I -m deepsigma_cartography demo --out fresh-demo
```

On Windows use `.venv\Scripts\python.exe` instead of `.venv/bin/python`.
Choose a new demo output directory; existing directories are intentionally rejected.

## Boundaries not verified or not implemented

No live branch, native VINCULUM UI/runtime hook, MERIDIAN import, Lattice vendor connection,
end-to-end COMPOSER commit path, security accreditation, production scalability, or human
identity/authorization service is claimed. The VINCULUM envelope is a proposed interchange.
SHA-256 detects content changes, not identity or truth. Whole-file archive rollback requires
an independently retained trusted head; restoring both database and checkpoint is outside
this model. Analytical scope/layer filters do not sanitize or declassify information.
