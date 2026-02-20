# Cookbook: OpenClaw — Supervised Run

**Adapter:** `adapters/openclaw/adapter.py`
**Status:** Alpha — contract checking is functional; adapter API may evolve.

This recipe shows how to use `OpenClawSupervisor` to:
1. Load a policy pack with pre/post action contracts
2. Run a supervised decision and observe pass/fail outcomes
3. Verify which artifacts are produced

---

## Prerequisites

- Python 3.10+
- DeepSigma installed: `pip install -e .` (from repo root)
- PyYAML (included in `requirements.txt`)

```bash
pip install -r requirements.txt && pip install -e .
```

---

## Steps

### Step 1 — Review the minimal policy pack

`policy_pack_min.yaml` in this directory defines one contract for `LoanApproval`:

```yaml
contracts:
  LoanApproval:
    contractId: "contract-loan-min"
    preconditions:
      - field: "applicant_verified"
        equals: true
        message: "Applicant must be verified before loan approval"
    postconditions:
      - field: "decision"
        equals: "approved"
```

**Precondition:** `context["applicant_verified"]` must be `true` — otherwise the action is blocked.
**Postcondition:** `result["decision"]` must be `"approved"` — otherwise a contract violation is logged.

### Step 2 — Run the supervised demo

```bash
bash cookbook/openclaw/supervised_run/run.sh
```

Or directly with Python:

```bash
python - <<'EOF'
import sys, yaml
sys.path.insert(0, ".")
from pathlib import Path
from adapters.openclaw.adapter import OpenClawSupervisor

policy = yaml.safe_load(
    Path("cookbook/openclaw/supervised_run/policy_pack_min.yaml").read_text()
)
supervisor = OpenClawSupervisor(policy_pack=policy)

# --- Scenario 1: PASS (precondition met, action returns approved) ---
context_ok = {"applicant_verified": True, "amount_requested": 50000}
result = supervisor.supervise(
    decision_type="LoanApproval",
    context=context_ok,
    action_fn=lambda ctx: {"decision": "approved", "amount": ctx["amount_requested"]},
)
print("Scenario 1 (PASS):", result)

# --- Scenario 2: BLOCKED (precondition fails) ---
context_fail = {"applicant_verified": False, "amount_requested": 50000}
result = supervisor.supervise(
    decision_type="LoanApproval",
    context=context_fail,
    action_fn=lambda ctx: {"decision": "approved"},
)
print("Scenario 2 (BLOCKED):", result)
EOF
```

---

## Expected Output

```
Scenario 1 (PASS): {
  'outcome': 'success',
  'result': {'decision': 'approved', 'amount': 50000},
  'elapsed_ms': 0
}

Scenario 2 (BLOCKED): {
  'outcome': 'blocked',
  'reason': 'precondition_failed',
  'violations': [{
    'contract_id': 'contract-loan-min',
    'condition_type': 'precondition',
    'field': 'applicant_verified',
    'expected': True,
    'actual': False,
    'message': 'Applicant must be verified before loan approval'
  }],
  'elapsed_ms': 0
}
```

---

## Artifacts Produced

The `supervise()` method returns a dict — not a sealed DeepSigma episode by itself. To create a full governance record, wrap the supervised call in a `DecisionEpisode`:

```python
import json
from datetime import datetime, timezone

episode = {
    "episodeId": "ep-openclaw-001",
    "decisionType": "LoanApproval",
    "actor": {"id": "openclaw-supervisor"},
    "startedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "outcome": {
        "code": "success" if result["outcome"] == "success" else "fail",
        "reason": result.get("reason", ""),
    },
    "context": context_ok,
    "actions": [{"actionType": "LoanApproval", "result": result.get("result", {})}],
    "seal": {"sealedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "sealHash": "openclaw"},
}
print(json.dumps(episode, indent=2))
```

**To validate the episode against the schema:**
```bash
python tools/validate_examples.py  # validates files in examples/
# or manually:
python -c "
import json, jsonschema
from pathlib import Path
schema = json.loads(Path('specs/episode.schema.json').read_text())
jsonschema.validate(YOUR_EPISODE_DICT, schema)
print('Valid')
"
```

---

## Verification

After running:

1. `outcome == "success"` → preconditions passed, action ran, postconditions passed
2. `outcome == "blocked"` → a precondition was `False`; check `violations` for which field
3. `outcome == "postcondition_failed"` → action ran but its output didn't meet postconditions
4. `outcome == "error"` → the `action_fn` raised an exception; check `reason`

No files are written — all state is in-memory. Violations are also accessible via `supervisor.violations`.

---

## Failure Modes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `outcome: blocked` unexpectedly | `context` dict key doesn't match `field` in policy | Check policy YAML field names exactly match context keys |
| `yaml.parser.ParserError` | Indentation or syntax error in YAML | Use spaces (not tabs); validate with `python -c "import yaml; yaml.safe_load(open('policy_pack_min.yaml'))"` |
| `ModuleNotFoundError: adapters.openclaw` | Wrong working directory | Run from repo root |
| `outcome: postcondition_failed` | Action returned wrong value | Check `result` dict key matches postcondition `field` |
