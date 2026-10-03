# Security and limits

This is a bounded reference analysis extension, not a hardened multi-tenant
service or an operational authorization implementation.

## Enforced locally

Strict episode schemas reject unknown fields, duplicate JSON keys and duplicate
identities. They reject dangling local evidence/node references, unsupported
states, naive timestamps, reversed ranges and nonfinite values. Numeric aspects
use bounded integer or numeric-string values, including exact rational forms;
floating values are not silently promoted into precise measurements. Host raw
reports may retain their finite floating descriptors without using them as
measurement authority.

Snapshots are immutable at the public model interface. Returned dictionaries are
copies. The adapter copies all host data and preserves original selected pairs.
JIT has no composite score. Navigation only follows a recorded adjacent link in
the pinned world; unloaded external targets stay visible and cannot be traversed.

JSON input and individual snapshots are capped at 8 MB, strings at 100,000
characters, nesting at 60 levels, nodes at 10,000 and local folds at 20,000.
Neighborhood depth is at most 100 and returned nodes at most 10,000. These are
input guardrails, not a proof of worst-case time/memory safety. Host quotas and
process isolation remain necessary for hostile workloads.

## Persistence boundary

Journal creation is explicit and fails when the path already exists. Opening a
journal uses SQLite `mode=ro` or `mode=rw`, never an implicit create mode. Writes
use a transaction, validate revision/predecessor identity and read back the row
before commit. Missing/corrupt history is not treated as a new genesis.

The journal is not independently trusted. An attacker with write access to the
entire database can alter every hash. Internal consistency alone cannot detect a
whole-history rollback. `verify(expected_tip=...)` compares against a separately
retained expected tip; that reference must itself be protected by the host.
Ordinary restart behavior is tested. Power-loss guarantees, hostile filesystem
replacement, platform-specific durability and full adversarial concurrency are
not certified. The library does not authenticate a caller-provided host result.

## Export boundary

Exports reserve a new directory and never overwrite an existing output. Failure
can leave an incomplete new directory; verification then fails. This is not an
all-or-nothing cross-filesystem transaction. Manifest verification rejects file
inventory changes and symbolic-link inputs, checks hashes and regenerates the
read-only projections. It is unsigned. Fully replacing both episode and manifest
is not detectable without a separately pinned episode digest.

## Access, scope and effects

The caller must supply only material the viewer is authorized to inspect. The
package does not redact classified material, infer safe disclosure, perform
source network retrieval, execute code from JSON, grant access, issue operational
commands, write COMPOSER authority or run CERPA APPLY. CERPA and DLR/RS/DS/MG
locators are references only. JIT's Awareness values describe an attributed
interpretation of an artifact, not a personality profile or a person score.
