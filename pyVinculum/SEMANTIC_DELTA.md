# VINCULUM v0.4 — Semantic Delta Declaration

## Release intent

v0.4 changes the **authoritative ingress/egress path**, not the core bounded-coherence semantics.

The existing P + D + G evaluation behavior remains the v0.3 baseline.

## Byte-identical semantic modules from v0.3

The following source modules are SHA-256 identical between v0.3.0 and v0.4.0:

```text
authority.py
constraints.py
evidence.py
exceptions.py
metrics.py
models.py
protocols.py
provenance.py
receipts.py
trust.py
cli.py
```

## Byte-identical core engine functions

The following v0.3/v0.4 function bodies are SHA-256 identical:

```text
VinculumEngine.bind
  c7da1eb25a562741fae32faf285cd9ed43cfbbdc31dc1a9f054f9699ce7e54c9

VinculumEngine.bind_trusted
  e0cd5dfb3e407a3b5e399d055cdafdd489fe027eedb0bdc906c1833ef9d80edc

VinculumEngine._bind_one
  8b4a2e6dbca30f7b93e493d02f21d5d442a3b6f68c5a49f264698a3a0c9220ff
```

## Byte-identical pre-v0.4 governance policy methods

```text
GovernancePolicy.compatibility
  f6077e9644d15a28a6c8698f571c71a6c61398e3a36a410d5108bc9beb8e2774

GovernancePolicy.strict
  fade53fef3444949d3f4f766fc472a3791bca1f17e8e9f0da28f1e3c66df5ab9

GovernancePolicy.trusted
  683f4f44f0eacc5d80e4eb1380d9dd33d8a196c8ac419d420dae0b351a03873b

GovernancePolicy.to_dict
  c298a9bf8607adf829c673069c66eea5250cb59b2fde30f6b681b14699877948
```

## New v0.4 surfaces

```text
authoritative.py
  ComposerChange
  CommitIntent
  FileAuthoritativeStateStore
  AuthoritativeBootstrapService
  AuthoritativeCommitService
  AuthoritativeGovernanceRuntime
  AuthoritativeCommitReceipt
  AuthoritativeSnapshot

integration.py
  AuthoritativeBinding
  CerpaHandoff
  CerpaBridge

engine.py
  VinculumEngine.bind_authoritative   # new method only

governance.py
  GovernancePolicy.authoritative      # new label; same gates as trusted v0.3
```

## Declared semantic effect

v0.4 does **not** change how a hypothesis is accepted/rejected/unresolved once a `GovernanceContext` is chosen.

It changes the higher-order rule for authoritative operation:

```text
v0.3 trusted path:
root-valid + monotonic signed context

v0.4 authoritative path:
root-valid + monotonic + COMPOSER committed current context
```

That is a provenance/authority-state delta, not a P/D scoring or constraint-evaluation delta.
