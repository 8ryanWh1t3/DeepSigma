"""CascadeEngine — cross-domain event propagation.

Subscribes to all domain event streams, matches cascade rules, and
invokes target handlers in the appropriate domain mode.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import DomainMode, FunctionResult
from .cascade_rules import CascadeRule, get_rules_for_event


class CascadeResult:
    """Result of a cascade propagation."""

    def __init__(self) -> None:
        self.triggered_rules: List[str] = []
        self.results: List[FunctionResult] = []
        self.errors: List[str] = []

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    @property
    def total_triggered(self) -> int:
        return len(self.triggered_rules)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "triggeredRules": self.triggered_rules,
            "totalTriggered": self.total_triggered,
            "success": self.success,
            "errors": self.errors,
        }


class CascadeEngine:
    """Orchestrates cross-domain event cascades.

    Register domain modes, then call ``propagate()`` with events.
    The engine matches rules and invokes target handlers.
    """

    def __init__(self) -> None:
        self._domains: Dict[str, DomainMode] = {}

    def register_domain(self, mode: DomainMode) -> None:
        """Register a domain mode for cascade routing."""
        self._domains[mode.domain] = mode

    @property
    def domain_count(self) -> int:
        return len(self._domains)

    def propagate(
        self,
        source_domain: str,
        event: Dict[str, Any],
        context: Dict[str, Any],
        max_depth: int = 3,
    ) -> CascadeResult:
        """Propagate an event through cascade rules.

        Args:
            source_domain: The domain that emitted the event.
            event: The event dict (must have 'subtype').
            context: Shared execution context.
            max_depth: Maximum cascade depth to prevent infinite loops.

        Returns:
            CascadeResult with triggered rules and handler results.
        """
        result = CascadeResult()

        if max_depth <= 0:
            return result

        subtype = event.get("subtype", "")
        severity = event.get("severity", "")

        rules = get_rules_for_event(source_domain, subtype, severity)

        for rule in rules:
            target_mode = self._domains.get(rule.target_domain)
            if target_mode is None:
                result.errors.append(
                    f"Target domain '{rule.target_domain}' not registered for rule {rule.rule_id}"
                )
                continue

            # Build cascade event
            cascade_event = {
                "payload": event.get("payload", event),
                "cascadeRuleId": rule.rule_id,
                "sourceEvent": event,
            }

            handler_result = target_mode.handle(
                rule.target_function_id, cascade_event, context
            )

            result.triggered_rules.append(rule.rule_id)
            result.results.append(handler_result)

            if not handler_result.success:
                result.errors.append(
                    f"Rule {rule.rule_id} handler {rule.target_function_id} failed: "
                    f"{handler_result.error}"
                )

            # Recursive cascade: propagate handler output events
            for emitted in handler_result.events_emitted:
                sub_result = self.propagate(
                    source_domain=rule.target_domain,
                    event=emitted,
                    context=context,
                    max_depth=max_depth - 1,
                )
                result.triggered_rules.extend(sub_result.triggered_rules)
                result.results.extend(sub_result.results)
                result.errors.extend(sub_result.errors)

        return result
