"""OpenClaw adapter with contract verification. Closes #7, closes #8.

Provides an OpenClawSupervisor class that wraps decision episodes
with pre/post contract checks for action safety verification.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class ContractViolation:
    """Records a single contract violation."""
    contract_id: str
    condition_type: str  # "precondition" or "postcondition"
    field: str
    expected: Any
    actual: Any
    message: str = ""


@dataclass
class ContractResult:
    """Result of checking pre or post conditions."""
    passed: bool
    violations: List[ContractViolation] = field(default_factory=list)


class OpenClawSupervisor:
    """Supervisor that enforces OpenClaw action contracts.

    Wraps the decision episode lifecycle with pre-condition and
    post-condition checks defined in the policy pack.
    """

    def __init__(self, policy_pack: Dict[str, Any]):
        self.policy_pack = policy_pack
        self._contracts = policy_pack.get("contracts", {})
        self._violations_log: List[ContractViolation] = []

    def get_contract(self, decision_type: str) -> Dict[str, Any]:
        """Retrieve the contract for a given decision type."""
        return self._contracts.get(decision_type, {})

    def check_preconditions(
        self, decision_type: str, context: Dict[str, Any]
    ) -> ContractResult:
        """Check action preconditions before execution.

        Args:
            decision_type: The type of decision being made.
            context: The current context/state dict.

        Returns:
            ContractResult indicating pass/fail and any violations.
        """
        contract = self.get_contract(decision_type)
        preconditions = contract.get("preconditions", [])
        if not preconditions:
            return ContractResult(passed=True)

        violations = []
        for cond in preconditions:
            field_name = cond.get("field")
            expected = cond.get("equals")
            actual = context.get(field_name)
            if actual != expected:
                v = ContractViolation(
                    contract_id=contract.get("contractId", "unknown"),
                    condition_type="precondition",
                    field=field_name,
                    expected=expected,
                    actual=actual,
                    message=cond.get("message", f"{field_name}: expected {expected}, got {actual}"),
                )
                violations.append(v)
                self._violations_log.append(v)

        return ContractResult(passed=len(violations) == 0, violations=violations)

    def check_postconditions(
        self, decision_type: str, context: Dict[str, Any], result: Dict[str, Any]
    ) -> ContractResult:
        """Check action postconditions after execution.

        Args:
            decision_type: The type of decision that was made.
            context: The context at time of decision.
            result: The result/output of the action.

        Returns:
            ContractResult indicating pass/fail and any violations.
        """
        contract = self.get_contract(decision_type)
        postconditions = contract.get("postconditions", [])
        if not postconditions:
            return ContractResult(passed=True)

        violations = []
        for cond in postconditions:
            field_name = cond.get("field")
            expected = cond.get("equals")
            actual = result.get(field_name)
            if actual != expected:
                v = ContractViolation(
                    contract_id=contract.get("contractId", "unknown"),
                    condition_type="postcondition",
                    field=field_name,
                    expected=expected,
                    actual=actual,
                    message=cond.get("message", f"{field_name}: expected {expected}, got {actual}"),
                )
                violations.append(v)
                self._violations_log.append(v)

        return ContractResult(passed=len(violations) == 0, violations=violations)

    def supervise(
        self,
        decision_type: str,
        context: Dict[str, Any],
        action_fn,
    ) -> Dict[str, Any]:
        """Run a supervised action with pre/post contract checks.

        Args:
            decision_type: Type of decision.
            context: Current context dict.
            action_fn: Callable that takes context and returns result dict.

        Returns:
            Dict with outcome, contract results, and timing.
        """
        start = time.monotonic()

        # Pre-condition check
        pre_result = self.check_preconditions(decision_type, context)
        if not pre_result.passed:
            logger.warning(
                "Precondition check failed for %s: %d violations",
                decision_type,
                len(pre_result.violations),
            )
            return {
                "outcome": "blocked",
                "reason": "precondition_failed",
                "violations": [v.__dict__ for v in pre_result.violations],
                "elapsed_ms": int((time.monotonic() - start) * 1000),
            }

        # Execute action
        try:
            result = action_fn(context)
        except Exception as exc:
            logger.error("Action %s raised: %s", decision_type, exc)
            return {
                "outcome": "error",
                "reason": str(exc),
                "elapsed_ms": int((time.monotonic() - start) * 1000),
            }

        # Post-condition check
        post_result = self.check_postconditions(decision_type, context, result)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        if not post_result.passed:
            logger.warning(
                "Postcondition check failed for %s: %d violations",
                decision_type,
                len(post_result.violations),
            )
            return {
                "outcome": "postcondition_failed",
                "result": result,
                "violations": [v.__dict__ for v in post_result.violations],
                "elapsed_ms": elapsed_ms,
            }

        return {
            "outcome": "success",
            "result": result,
            "elapsed_ms": elapsed_ms,
        }

    @property
    def violations(self) -> List[ContractViolation]:
        """Return all recorded violations."""
        return list(self._violations_log)
