# Reports, formats and replay

## Default portable bundle

`result.export(directory)` writes:

- `JOB.json`: complete declarative recipe, including verified input source hashes.
- `pipeline.json`: pipeline result, stage trace, extraction/normalization, evidence, pairing and diagnostics.
- `report.json`: core pair/group/matrix evaluation.
- `report.html`: offline, escaped, no-JavaScript matrix and details report. No external resources.
- `REPORT.md`: human-readable summary and review queue.
- `scenario.ttl`: typed native scenario graph/policy roundtrip.
- `findings.ttl`: RDF result projection with pair IDs, statuses and scores.
- Eight CSV tables: five core tables plus sources, extraction and findings.
- `OUTPUT_MANIFEST.json`: hashes of files written by that export call.

A previous file remaining in the directory is not automatically covered by the new call's manifest; export into an empty destination for a clean per-run bundle. The release demonstration's final manifest explicitly covers its XLSX/PDF artifacts too.

## Optional PDF

ReportLab creates a programmatic executive summary and review queue. It is not a reproduction of source-page layout. Delta text identifies the left unit when scalar; set/range cases are not mislabeled as scalar zero.

## Optional XLSX

The host `artifact_tool` runtime creates 11 sheets. Derived count/score cells are formulas over preserved results; missing support remains blank. User-provided formula-like text is escaped. The spreadsheet is a review/export surface, not an authorization engine or a full CERPA workflow implementation.

## Input adapters and coverage

| Format | Supported scope |
|---|---|
| TXT / MD | Nonblank text segments, not unrestricted parsing of meaning |
| JSON / JSONL | Object rows with explicit field mapping; duplicate keys and nonfinite values rejected |
| CSV | Unique text headers, strict row width |
| YAML | Optional safe loader; no aliases, duplicate keys or unsafe tags |
| PDF | Optional text layer only; bounded pages/streams; no OCR; reading order and images may be missing |
| DOCX | Body paragraphs/tables in document order; no images, footnotes/comments or tracked-change interpretation |
| XLSX | Optional artifact_tool; selected/first sheet, row1 headers, columns A:AZ, configured first N data rows only; formulas withheld as unverified numeric observations |
| Parquet | Optional pyarrow row iterator with explicit field mapping; real decoder untested in this release environment |
| Turtle | Local explicit triple mapping, or native scenario restoration; no arbitrary semantic entailment or remote imports |

Declared defaults: 25 MB input, 10,000 rows, 1,000,000 extracted text characters, 200 PDF pages, 50 MB expanded archive/content budget. Third-party parsers still require isolated process and operating-system limits for hostile inputs; post-decompression limits are not a complete memory sandbox.

## Replay boundaries

JOB.json preserves inline sources and pins input content identities. It does not copy file-backed inputs. For a file-backed replay, put the job at its original authorized root or call `run(job, base_dir=original_root, allow_files=True)` with the original files.

The native Turtle graph and core report are useful interchange formats; they do not include the pipeline's evidence registry plugin or every source extraction configuration. They cannot replace JOB.json for full-fidelity pipeline replay.

Machine-readable data can feed downstream systems. No live downstream connector or platform-specific certification is implied.
