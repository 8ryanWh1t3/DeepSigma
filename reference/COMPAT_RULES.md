# Compatibility Rules

How schema and contract changes map to semver bumps.

See [CONSTITUTION.md](CONSTITUTION.md) for enforcement and [CHANGELOG.md](CHANGELOG.md) for history.

## MAJOR (breaking)

A change is **MAJOR** if any existing consumer that validates against the current
schema would reject a newly-produced artifact, or would silently misinterpret a
field that changed meaning.

- Remove or rename a required field from any schema
- Change a field's type (e.g. `string` to `integer`)
- Add a new value to a closed `enum` that consumers must handle to remain correct
- Remove a schema from the manifest
- Narrow a `pattern` or tighten validation so that previously-valid data is rejected
- Change the canonical hash algorithm (SHA-256 to another)
- Remove or redefine an existing FEEDS topic or recordType

**Required**: Migration notes with consumer action + rollback assessment.

## MINOR (compatible, additive)

A change is **MINOR** if old consumers continue to work without modification, but
new consumers gain access to additional data or capabilities.

- Add a new optional field to a schema
- Add a new schema to the manifest
- Widen an enum (add a value consumers may safely ignore)
- Relax a pattern or loosen validation (accept more input)
- Add a new FEEDS topic or recordType

**Required**: CHANGELOG entry with `ADDITIVE:` or `COMPATIBLE:` annotation.

## PATCH (metadata only)

A change is **PATCH** if it does not alter validation behavior at all.

- Fix a `description` or `title` in a schema (no structural change)
- Update a `$id` URL without changing validation rules
- Update policy baseline prose without changing enforceable rules
- Regenerate manifest after description-only edits

**Required**: CHANGELOG entry with `COMPATIBLE:` annotation.

## Migration Notes Template

Every CHANGELOG entry for MAJOR or MINOR changes must follow this structure:

```markdown
## vX.Y.Z — <title>

`BREAKING:` | `COMPATIBLE:` | `ADDITIVE:` <one-line summary>

### Migration

**Affected schemas**: <list of changed schema files>
**Consumer action**: <what SDK users must do, or "None" for additive>
**Rollback**: <can old consumers read new artifacts? yes/no>
**Fingerprint**: `sha256:<contract fingerprint after change>`
```

## Contract Fingerprint

Every CHANGELOG entry includes the contract fingerprint — a single SHA-256 digest
of the schema manifest. This lets any consumer verify which contract surface
produced an artifact by comparing the fingerprint in the artifact against the
CHANGELOG.

The fingerprint is computed by `constitution_gate.py` and written to
`reference/CONTRACT_FINGERPRINT`.
