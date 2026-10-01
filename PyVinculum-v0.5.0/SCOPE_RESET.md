# Scope Reset — Why v0.5 Exists

VINCULUM began as a P↔D measurement idea:

- **Language:** push probabilistic meaning toward deterministic form (`P→D`).
- **Mathematics:** defend deterministic form from probabilistic contamination (`D←P`).
- **Third state:** preserve both forces and quantify their relationship as a continuous, inspectable tension model.

During v0.3/v0.4 the implementation expanded into trust roots, governance, authoritative publication, and CERPA integration. Those are legitimate downstream integrations, but they are not the purpose of the core pyLib.

v0.5 therefore establishes a hard scope boundary:

```text
VINCULUM CORE
  ingest
  decompose
  score P
  score D
  derive V / τ
  aggregate
  explain drivers

NOT VINCULUM CORE
  authorization
  policy approval
  signatures
  root of trust
  publication commit
  CERPA APPLY
  legal/compliance verdicts
```

Future integrations may consume VINCULUM results, but they must not redefine the measurement kernel.
