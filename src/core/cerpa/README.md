# CERPA — Claim, Event, Review, Patch, Apply

The foundational adaptation loop for DeepSigma.

```
Claim -> Event -> Review -> Patch -> Apply
```

## Modules

| File | Purpose |
|------|---------|
| `types.py` | Enums: CerpaDomain, CerpaStatus, ReviewVerdict, PatchAction |
| `models.py` | Dataclasses: Claim, Event, Review, Patch, ApplyResult, CerpaCycle |
| `engine.py` | Orchestrator: `run_cerpa_cycle()` and step functions |
| `mappers.py` | Bidirectional adapters to AtomicClaim, DriftSignal, DLR, etc. |

## Quick Start

```python
from core.cerpa import Claim, Event, run_cerpa_cycle, cycle_to_dict

claim = Claim(id="c-1", text="Service uptime >= 99.9%", domain="reops",
              source="sla-monitor", timestamp="2026-03-01T10:00:00Z")
event = Event(id="e-1", text="Service uptime dropped to 99.5%", domain="reops",
              source="apm", timestamp="2026-03-02T10:00:00Z",
              observed_state={"status": "failed"}, metadata={})
cycle = run_cerpa_cycle(claim, event)
print(cycle_to_dict(cycle))
```

## Demos

```bash
python -m src.core.examples.cerpa_contract_demo
python -m src.core.examples.cerpa_agent_supervision_demo
```
