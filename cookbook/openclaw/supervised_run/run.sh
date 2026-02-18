#!/usr/bin/env bash
# OpenClaw Supervised Run — cookbook example
#
# Prerequisites:
#   pip install -r requirements.txt && pip install -e .
#
# Usage (from repo root):
#   bash cookbook/openclaw/supervised_run/run.sh

set -e
cd "$(dirname "$0")/../../.."   # ensure we're at repo root

echo "=== OpenClaw Supervised Run ==="
echo ""

python - <<'PYEOF'
import sys
import yaml
sys.path.insert(0, ".")
from pathlib import Path
from adapters.openclaw.adapter import OpenClawSupervisor

policy = yaml.safe_load(
    Path("cookbook/openclaw/supervised_run/policy_pack_min.yaml").read_text()
)
supervisor = OpenClawSupervisor(policy_pack=policy)

# ── Scenario 1: PASS ──────────────────────────────────────────────────────────
print("Scenario 1: Verified applicant → PASS")
context_ok = {"applicant_verified": True, "amount_requested": 50000}
result = supervisor.supervise(
    decision_type="LoanApproval",
    context=context_ok,
    action_fn=lambda ctx: {"decision": "approved", "amount": ctx["amount_requested"]},
)
assert result["outcome"] == "success", f"Expected success, got: {result['outcome']}"
print(f"  outcome  : {result['outcome']}")
print(f"  result   : {result['result']}")
print(f"  elapsed  : {result['elapsed_ms']}ms")
print()

# ── Scenario 2: BLOCKED ───────────────────────────────────────────────────────
print("Scenario 2: Unverified applicant → BLOCKED")
context_fail = {"applicant_verified": False, "amount_requested": 50000}
result = supervisor.supervise(
    decision_type="LoanApproval",
    context=context_fail,
    action_fn=lambda ctx: {"decision": "approved"},
)
assert result["outcome"] == "blocked", f"Expected blocked, got: {result['outcome']}"
print(f"  outcome  : {result['outcome']}")
print(f"  reason   : {result['reason']}")
violation = result["violations"][0]
print(f"  violation: field={violation['field']!r}, expected={violation['expected']!r}, actual={violation['actual']!r}")
print()

# ── Scenario 3: POSTCONDITION FAILED ─────────────────────────────────────────
print("Scenario 3: Verified applicant, action returns wrong value → POSTCONDITION FAILED")
result = supervisor.supervise(
    decision_type="LoanApproval",
    context=context_ok,
    action_fn=lambda ctx: {"decision": "pending"},   # wrong value
)
assert result["outcome"] == "postcondition_failed", f"Expected postcondition_failed, got: {result['outcome']}"
print(f"  outcome  : {result['outcome']}")
violation = result["violations"][0]
print(f"  violation: field={violation['field']!r}, expected={violation['expected']!r}, actual={violation['actual']!r}")
print()

print("=== PASS: All three scenarios behaved as expected ===")
PYEOF
