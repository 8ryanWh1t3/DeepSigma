# Build notes

This release was assembled from the actual provided 0.5.2 source ZIP, not inferred from screenshots or prior completion messages. The source ZIP digest matched the earlier published digest and the baseline suite was rerun before modifications.

The extension adds a new explicit API and CLI rather than silently changing the historical scoring engine. The functional source hashes and new files are recorded in SEMANTIC_DELTA.json. Current specs are at the package root; historical specs are archived under docs/legacy_v0_5_2.

Synthetic examples are explicitly invoked through `vinculum.demos`; none are automatically loaded into user analyses. The report viewer has no LLM dependency, external fonts, trackers or JavaScript.

Source/wheel/delivery tests, dependency versions, measured example outcomes and manifest verification are recorded in VALIDATION.md and validation JSON files. Test results apply to the tested environment and fixtures, not universal operational safety.

`MANIFEST.sha256` covers delivered regular files except itself. The ZIP digest lives in its separate sidecar to avoid recursive self-hashing. Rebuilding a wheel/ZIP may change packaging timestamps; canonical evaluation fingerprints are the replay mechanism, not byte-identical packaging claims.
