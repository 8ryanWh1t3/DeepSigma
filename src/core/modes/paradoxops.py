"""ParadoxOps domain mode -- paradox tension detection and lifecycle.

12 function handlers keyed by PDX-F01 through PDX-F12.

The tension loop: create -> attach dimensions -> shift -> pressure ->
threshold -> promote/seal -> patch -> rebalance/archive.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from .base import DomainMode, FunctionResult


class ParadoxOps(DomainMode):
    """Fifth domain mode: Paradox Tension Set lifecycle management."""

    domain = "paradoxops"

    def _register_handlers(self) -> None:
        self._handlers = {
            "PDX-F01": self._tension_set_create,
            "PDX-F02": self._pole_manage,
            "PDX-F03": self._dimension_attach,
            "PDX-F04": self._dimension_shift,
            "PDX-F05": self._pressure_compute,
            "PDX-F06": self._imbalance_compute,
            "PDX-F07": self._threshold_evaluate,
            "PDX-F08": self._drift_promote,
            "PDX-F09": self._interdimensional_drift_detect,
            "PDX-F10": self._seal_snapshot,
            "PDX-F11": self._patch_issue,
            "PDX-F12": self._lifecycle_transition,
        }

    # ── PDX-F01: Create Tension Set ──────────────────────────────

    def _tension_set_create(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Create a new Paradox Tension Set with poles.

        ── PDX-F01: tension_set_create ──
        """
        from core.paradox_ops import (
            ParadoxTensionSet, TensionPole, TensionLifecycleState,
            validate_tension_set, ParadoxRegistry, TensionLifecycle,
        )

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []
        drift_signals: List[Dict[str, Any]] = []
        mg_updates: List[str] = []

        errors = validate_tension_set(payload)
        if errors:
            return FunctionResult(
                function_id="PDX-F01", success=False,
                error="; ".join(errors),
            )

        tension_id = payload.get("tensionId", f"PTS-{uuid.uuid4().hex[:8]}")
        subtype = payload.get("subtype", "tension_pair")
        now = ctx.get("now", datetime.now(timezone.utc))
        now_iso = now.isoformat() if hasattr(now, "isoformat") else str(now)

        poles = [
            TensionPole(
                pole_id=p.get("poleId", f"POLE-{uuid.uuid4().hex[:6]}"),
                label=p.get("label", ""),
                weight=p.get("weight", 1.0),
                evidence_refs=p.get("evidenceRefs", []),
            )
            for p in payload.get("poles", [])
        ]

        pts = ParadoxTensionSet(
            tension_id=tension_id,
            subtype=subtype,
            poles=poles,
            lifecycle_state=TensionLifecycleState.DETECTED.value,
            created_at=now_iso,
            updated_at=now_iso,
            episode_id=payload.get("episodeId", ""),
        )

        registry: ParadoxRegistry = ctx.get("paradox_registry")  # type: ignore[assignment]
        if registry is not None:
            registry.add(pts)

        lifecycle: TensionLifecycle = ctx.get("tension_lifecycle")  # type: ignore[assignment]
        if lifecycle is not None:
            lifecycle.set_state(tension_id, TensionLifecycleState.DETECTED)

        mg = ctx.get("memory_graph")
        if mg is not None:
            from core.memory_graph import GraphNode, NodeKind
            mg._add_node(GraphNode(
                node_id=tension_id,
                kind=NodeKind.TENSION_SET,
                label=subtype,
                timestamp=now_iso,
                properties={
                    "lifecycle_state": "detected",
                    "pole_count": len(poles),
                    "pressure_score": 0.0,
                },
            ))
            mg_updates.append(tension_id)

        events.append({
            "topic": "drift_signal",
            "subtype": "pts_created",
            "tensionId": tension_id,
            "subtype_value": subtype,
            "poleCount": len(poles),
        })

        return FunctionResult(
            function_id="PDX-F01", success=True,
            events_emitted=events,
            drift_signals=drift_signals,
            mg_updates=mg_updates,
        )

    # ── PDX-F02: Pole Manage ─────────────────────────────────────

    def _pole_manage(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Add, remove, or update poles on a PTS.

        ── PDX-F02: pole_manage ──
        """
        from core.paradox_ops import ParadoxRegistry, TensionPole, TensionSubtype

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []
        mg_updates: List[str] = []

        registry: ParadoxRegistry = ctx.get("paradox_registry")  # type: ignore[assignment]
        tension_id = payload.get("tensionId", "")
        pts = registry.get(tension_id) if registry else None

        if pts is None:
            return FunctionResult(
                function_id="PDX-F02", success=False,
                error=f"PTS not found: {tension_id}",
            )

        operation = payload.get("operation", "add")
        pole_data = payload.get("pole", {})

        if operation == "add":
            pole = TensionPole(
                pole_id=pole_data.get("poleId", f"POLE-{uuid.uuid4().hex[:6]}"),
                label=pole_data.get("label", ""),
                weight=pole_data.get("weight", 1.0),
            )
            pts.poles.append(pole)
        elif operation == "remove":
            pole_id = pole_data.get("poleId", "")
            pts.poles = [p for p in pts.poles if p.pole_id != pole_id]
        elif operation == "update":
            pole_id = pole_data.get("poleId", "")
            for p in pts.poles:
                if p.pole_id == pole_id:
                    if "weight" in pole_data:
                        p.weight = pole_data["weight"]
                    if "label" in pole_data:
                        p.label = pole_data["label"]

        n = len(pts.poles)
        if n == 2:
            pts.subtype = TensionSubtype.TENSION_PAIR.value
        elif n == 3:
            pts.subtype = TensionSubtype.TENSION_TRIPLE.value
        elif n >= 4:
            pts.subtype = TensionSubtype.HIGHER_ORDER.value

        now = ctx.get("now", datetime.now(timezone.utc))
        pts.updated_at = now.isoformat() if hasattr(now, "isoformat") else str(now)
        registry.update(pts)

        events.append({
            "topic": "drift_signal",
            "subtype": "pts_pole_added",
            "tensionId": tension_id,
            "operation": operation,
            "poleCount": len(pts.poles),
        })

        return FunctionResult(
            function_id="PDX-F02", success=True,
            events_emitted=events, mg_updates=mg_updates,
        )

    # ── PDX-F03: Dimension Attach ────────────────────────────────

    def _dimension_attach(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Attach a dimension to a PTS.

        ── PDX-F03: dimension_attach ──
        """
        from core.paradox_ops import ParadoxRegistry, DimensionRegistry

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []

        registry: ParadoxRegistry = ctx.get("paradox_registry")  # type: ignore[assignment]
        tension_id = payload.get("tensionId", "")
        pts = registry.get(tension_id) if registry else None

        if pts is None:
            return FunctionResult(
                function_id="PDX-F03", success=False,
                error=f"PTS not found: {tension_id}",
            )

        dim_name = payload.get("dimensionName", "")
        existing_names = {d.name for d in pts.dimensions}
        if dim_name in existing_names:
            return FunctionResult(
                function_id="PDX-F03", success=False,
                error=f"Dimension already attached: {dim_name}",
            )

        dim_registry: DimensionRegistry = ctx.get("dimension_registry")  # type: ignore[assignment]
        if dim_registry is None:
            dim_registry = DimensionRegistry()

        template = dim_registry.get(dim_name)
        if template is None:
            return FunctionResult(
                function_id="PDX-F03", success=False,
                error=f"Unknown dimension: {dim_name}",
            )

        dim = dim_registry.create_dimension(dim_name)
        if "threshold" in payload:
            dim.threshold = payload["threshold"]

        pts.dimensions.append(dim)
        now = ctx.get("now", datetime.now(timezone.utc))
        pts.updated_at = now.isoformat() if hasattr(now, "isoformat") else str(now)
        registry.update(pts)

        events.append({
            "topic": "drift_signal",
            "subtype": "pts_dimension_attached",
            "tensionId": tension_id,
            "dimensionName": dim_name,
            "kind": dim.kind,
        })

        return FunctionResult(
            function_id="PDX-F03", success=True,
            events_emitted=events,
        )

    # ── PDX-F04: Dimension Shift ─────────────────────────────────

    def _dimension_shift(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Record a dimension value change.

        ── PDX-F04: dimension_shift ──
        """
        from core.paradox_ops import ParadoxRegistry, validate_dimension_shift

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []

        registry: ParadoxRegistry = ctx.get("paradox_registry")  # type: ignore[assignment]
        tension_id = payload.get("tensionId", "")
        pts = registry.get(tension_id) if registry else None

        if pts is None:
            return FunctionResult(
                function_id="PDX-F04", success=False,
                error=f"PTS not found: {tension_id}",
            )

        errors = validate_dimension_shift(payload, pts)
        if errors:
            return FunctionResult(
                function_id="PDX-F04", success=False,
                error="; ".join(errors),
            )

        dim_id = payload.get("dimensionId", payload.get("dimension_id", ""))
        new_value = payload.get("newValue", payload.get("new_value", 0.0))
        now = ctx.get("now", datetime.now(timezone.utc))
        now_iso = now.isoformat() if hasattr(now, "isoformat") else str(now)

        for d in pts.dimensions:
            if d.dimension_id == dim_id:
                d.previous_value = d.current_value
                d.current_value = float(new_value)
                d.shifted_at = now_iso
                break

        pts.updated_at = now_iso
        registry.update(pts)

        events.append({
            "topic": "drift_signal",
            "subtype": "pts_dimension_shifted",
            "tensionId": tension_id,
            "dimensionId": dim_id,
            "newValue": new_value,
        })

        return FunctionResult(
            function_id="PDX-F04", success=True,
            events_emitted=events,
        )

    # ── PDX-F05: Pressure Compute ────────────────────────────────

    def _pressure_compute(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Compute pressure score and elevate if threshold met.

        ── PDX-F05: pressure_compute ──
        """
        from core.paradox_ops import (
            ParadoxRegistry, TensionLifecycle, TensionLifecycleState,
            compute_pressure,
        )

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []
        drift_signals: List[Dict[str, Any]] = []

        registry: ParadoxRegistry = ctx.get("paradox_registry")  # type: ignore[assignment]
        tension_id = payload.get("tensionId", "")
        pts = registry.get(tension_id) if registry else None

        if pts is None:
            return FunctionResult(
                function_id="PDX-F05", success=False,
                error=f"PTS not found: {tension_id}",
            )

        pressure = compute_pressure(pts, ctx)
        pts.pressure_score = pressure
        now = ctx.get("now", datetime.now(timezone.utc))
        pts.updated_at = now.isoformat() if hasattr(now, "isoformat") else str(now)
        registry.update(pts)

        elevated = False
        if pressure >= 0.7 and pts.lifecycle_state == TensionLifecycleState.ACTIVE.value:
            lifecycle: TensionLifecycle = ctx.get("tension_lifecycle")  # type: ignore[assignment]
            if lifecycle is not None:
                elevated = lifecycle.transition(tension_id, TensionLifecycleState.ELEVATED)
                if elevated:
                    pts.lifecycle_state = TensionLifecycleState.ELEVATED.value
                    registry.update(pts)

        events.append({
            "topic": "drift_signal",
            "subtype": "pts_pressure_elevated" if elevated else "pts_pressure_computed",
            "tensionId": tension_id,
            "pressureScore": pressure,
            "elevated": elevated,
        })

        if elevated:
            drift_signals.append({
                "driftType": "tension_pressure",
                "severity": "yellow" if pressure < 0.85 else "red",
                "tensionId": tension_id,
                "pressureScore": pressure,
            })

        return FunctionResult(
            function_id="PDX-F05", success=True,
            events_emitted=events,
            drift_signals=drift_signals,
        )

    # ── PDX-F06: Imbalance Compute ───────────────────────────────

    def _imbalance_compute(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Compute imbalance vector.

        ── PDX-F06: imbalance_compute ──
        """
        from core.paradox_ops import ParadoxRegistry, compute_imbalance

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []

        registry: ParadoxRegistry = ctx.get("paradox_registry")  # type: ignore[assignment]
        tension_id = payload.get("tensionId", "")
        pts = registry.get(tension_id) if registry else None

        if pts is None:
            return FunctionResult(
                function_id="PDX-F06", success=False,
                error=f"PTS not found: {tension_id}",
            )

        imbalance = compute_imbalance(pts)
        pts.imbalance_vector = imbalance
        now = ctx.get("now", datetime.now(timezone.utc))
        pts.updated_at = now.isoformat() if hasattr(now, "isoformat") else str(now)
        registry.update(pts)

        events.append({
            "topic": "drift_signal",
            "subtype": "pts_imbalance_computed",
            "tensionId": tension_id,
            "imbalanceVector": imbalance,
        })

        return FunctionResult(
            function_id="PDX-F06", success=True,
            events_emitted=events,
        )

    # ── PDX-F07: Threshold Evaluate ──────────────────────────────

    def _threshold_evaluate(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Evaluate dimension thresholds.

        ── PDX-F07: threshold_evaluate ──
        """
        from core.paradox_ops import ParadoxRegistry, evaluate_thresholds

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []
        drift_signals: List[Dict[str, Any]] = []

        registry: ParadoxRegistry = ctx.get("paradox_registry")  # type: ignore[assignment]
        tension_id = payload.get("tensionId", "")
        pts = registry.get(tension_id) if registry else None

        if pts is None:
            return FunctionResult(
                function_id="PDX-F07", success=False,
                error=f"PTS not found: {tension_id}",
            )

        breaches = evaluate_thresholds(pts)

        if breaches:
            gov_breach = any(b.get("isGovernanceRelevant") for b in breaches)
            severity = "red" if gov_breach else ("orange" if len(breaches) > 1 else "yellow")
            events.append({
                "topic": "drift_signal",
                "subtype": "pts_threshold_breached",
                "tensionId": tension_id,
                "breachCount": len(breaches),
                "breaches": breaches,
            })
            drift_signals.append({
                "driftType": "tension_threshold_breach",
                "severity": severity,
                "tensionId": tension_id,
                "breachCount": len(breaches),
            })
        else:
            events.append({
                "topic": "drift_signal",
                "subtype": "pts_threshold_evaluated",
                "tensionId": tension_id,
                "breachCount": 0,
            })

        return FunctionResult(
            function_id="PDX-F07", success=True,
            events_emitted=events,
            drift_signals=drift_signals,
        )

    # ── PDX-F08: Drift Promote ───────────────────────────────────

    def _drift_promote(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Promote elevated tension to drift signal.

        ── PDX-F08: drift_promote ──
        """
        from core.paradox_ops import (
            ParadoxRegistry, TensionLifecycle, TensionLifecycleState,
        )
        from core.severity import compute_severity_score

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []
        drift_signals: List[Dict[str, Any]] = []
        mg_updates: List[str] = []

        registry: ParadoxRegistry = ctx.get("paradox_registry")  # type: ignore[assignment]
        tension_id = payload.get("tensionId", "")
        pts = registry.get(tension_id) if registry else None

        if pts is None:
            return FunctionResult(
                function_id="PDX-F08", success=False,
                error=f"PTS not found: {tension_id}",
            )

        if pts.lifecycle_state != TensionLifecycleState.ELEVATED.value:
            return FunctionResult(
                function_id="PDX-F08", success=False,
                error=f"PTS must be in elevated state to promote, current: {pts.lifecycle_state}",
            )

        sev_score = compute_severity_score("tension_pressure", "red")
        severity = "red" if sev_score >= 0.7 else "yellow"
        drift_id = f"DS-pdx-{uuid.uuid4().hex[:8]}"
        now = ctx.get("now", datetime.now(timezone.utc))
        now_iso = now.isoformat() if hasattr(now, "isoformat") else str(now)

        drift_signal = {
            "driftId": drift_id,
            "driftType": "tension_pressure",
            "severity": severity,
            "detectedAt": now_iso,
            "evidenceRefs": [f"tension:{tension_id}"],
            "fingerprint": {"key": f"{tension_id}:promote", "version": "1"},
            "targetType": "tension_set",
            "targetId": tension_id,
            "notes": f"Tension promoted to drift at pressure {pts.pressure_score}",
        }
        drift_signals.append(drift_signal)

        lifecycle: TensionLifecycle = ctx.get("tension_lifecycle")  # type: ignore[assignment]
        if lifecycle is not None:
            lifecycle.transition(tension_id, TensionLifecycleState.PROMOTED_TO_DRIFT)
        pts.lifecycle_state = TensionLifecycleState.PROMOTED_TO_DRIFT.value
        pts.promoted_drift_id = drift_id
        pts.updated_at = now_iso
        registry.update(pts)

        mg = ctx.get("memory_graph")
        if mg is not None:
            from core.memory_graph import GraphNode, NodeKind
            mg._add_node(GraphNode(
                node_id=drift_id,
                kind=NodeKind.DRIFT,
                label="tension_pressure",
                timestamp=now_iso,
                properties={"tension_id": tension_id, "pressure": pts.pressure_score},
            ))
            mg_updates.append(drift_id)

        events.append({
            "topic": "drift_signal",
            "subtype": "pts_promoted_to_drift",
            "tensionId": tension_id,
            "driftId": drift_id,
            "severity": severity,
        })

        return FunctionResult(
            function_id="PDX-F08", success=True,
            events_emitted=events,
            drift_signals=drift_signals,
            mg_updates=mg_updates,
        )

    # ── PDX-F09: Inter-Dimensional Drift Detect ──────────────────

    def _interdimensional_drift_detect(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Detect inter-dimensional drift.

        ── PDX-F09: interdimensional_drift_detect ──
        """
        from core.paradox_ops import ParadoxRegistry, detect_interdimensional_drift

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []
        drift_signals: List[Dict[str, Any]] = []
        mg_updates: List[str] = []

        registry: ParadoxRegistry = ctx.get("paradox_registry")  # type: ignore[assignment]
        tension_id = payload.get("tensionId", "")
        pts = registry.get(tension_id) if registry else None

        if pts is None:
            return FunctionResult(
                function_id="PDX-F09", success=False,
                error=f"PTS not found: {tension_id}",
            )

        drift = detect_interdimensional_drift(pts)

        if drift is not None:
            drift_signals.append(drift)
            events.append({
                "topic": "drift_signal",
                "subtype": "interdimensional_drift_detected",
                "tensionId": tension_id,
                "driftId": drift["driftId"],
                "shiftedDimensions": drift["shiftedDimensions"],
                "staleDimensions": drift["staleDimensions"],
            })

            mg = ctx.get("memory_graph")
            if mg is not None:
                from core.memory_graph import GraphNode, NodeKind
                mg._add_node(GraphNode(
                    node_id=drift["driftId"],
                    kind=NodeKind.DRIFT,
                    label="interdimensional_drift",
                    timestamp=drift["detectedAt"],
                    properties={
                        "tension_id": tension_id,
                        "shifted": drift["shiftedDimensions"],
                        "stale": drift["staleDimensions"],
                    },
                ))
                mg_updates.append(drift["driftId"])
        else:
            events.append({
                "topic": "drift_signal",
                "subtype": "interdimensional_drift_evaluated",
                "tensionId": tension_id,
                "driftDetected": False,
            })

        return FunctionResult(
            function_id="PDX-F09", success=True,
            events_emitted=events,
            drift_signals=drift_signals,
            mg_updates=mg_updates,
        )

    # ── PDX-F10: Seal Snapshot ───────────────────────────────────

    def _seal_snapshot(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Seal current PTS state with hash and version.

        ── PDX-F10: seal_snapshot ──
        """
        from core.paradox_ops import ParadoxRegistry, TensionLifecycle, TensionLifecycleState
        from core.authority.seal_and_hash import seal

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []

        registry: ParadoxRegistry = ctx.get("paradox_registry")  # type: ignore[assignment]
        tension_id = payload.get("tensionId", "")
        pts = registry.get(tension_id) if registry else None

        if pts is None:
            return FunctionResult(
                function_id="PDX-F10", success=False,
                error=f"PTS not found: {tension_id}",
            )

        snapshot = {
            "tensionId": pts.tension_id,
            "subtype": pts.subtype,
            "poleCount": len(pts.poles),
            "dimensionCount": len(pts.dimensions),
            "pressureScore": pts.pressure_score,
            "imbalanceVector": pts.imbalance_vector,
            "lifecycleState": pts.lifecycle_state,
        }
        sealed = seal(snapshot)

        now = ctx.get("now", datetime.now(timezone.utc))
        now_iso = now.isoformat() if hasattr(now, "isoformat") else str(now)

        pts.seal_hash = sealed["hash"]
        pts.sealed_at = sealed.get("sealedAt", now_iso)
        pts.seal_version = pts.seal_version + 1
        pts.updated_at = now_iso

        lifecycle: TensionLifecycle = ctx.get("tension_lifecycle")  # type: ignore[assignment]
        if lifecycle is not None:
            lifecycle.transition(tension_id, TensionLifecycleState.SEALED)
        pts.lifecycle_state = TensionLifecycleState.SEALED.value
        registry.update(pts)

        events.append({
            "topic": "drift_signal",
            "subtype": "pts_sealed",
            "tensionId": tension_id,
            "sealHash": pts.seal_hash,
            "sealVersion": pts.seal_version,
        })

        return FunctionResult(
            function_id="PDX-F10", success=True,
            events_emitted=events,
        )

    # ── PDX-F11: Patch Issue ─────────────────────────────────────

    def _patch_issue(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Issue a tension patch with recommended actions.

        ── PDX-F11: patch_issue ──
        """
        from core.paradox_ops import (
            ParadoxRegistry, TensionLifecycle, TensionLifecycleState,
            TensionPatch, evaluate_thresholds, build_patch_recommendations,
        )

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []
        mg_updates: List[str] = []

        registry: ParadoxRegistry = ctx.get("paradox_registry")  # type: ignore[assignment]
        tension_id = payload.get("tensionId", "")
        pts = registry.get(tension_id) if registry else None

        if pts is None:
            return FunctionResult(
                function_id="PDX-F11", success=False,
                error=f"PTS not found: {tension_id}",
            )

        breaches = evaluate_thresholds(pts)
        actions = build_patch_recommendations(pts, breaches)

        now = ctx.get("now", datetime.now(timezone.utc))
        now_iso = now.isoformat() if hasattr(now, "isoformat") else str(now)
        patch_id = f"TPATCH-{uuid.uuid4().hex[:8]}"

        patch = TensionPatch(
            patch_id=patch_id,
            tension_id=tension_id,
            recommended_actions=actions,
            rationale=f"Auto-generated from {len(breaches)} threshold breaches at pressure {pts.pressure_score}",
            issued_at=now_iso,
        )

        pts.patch_id = patch_id
        pts.updated_at = now_iso
        lifecycle: TensionLifecycle = ctx.get("tension_lifecycle")  # type: ignore[assignment]
        if lifecycle is not None:
            lifecycle.transition(tension_id, TensionLifecycleState.PATCHED)
        pts.lifecycle_state = TensionLifecycleState.PATCHED.value
        registry.update(pts)

        mg = ctx.get("memory_graph")
        if mg is not None:
            from core.memory_graph import GraphNode, NodeKind
            mg._add_node(GraphNode(
                node_id=patch_id,
                kind=NodeKind.PATCH,
                label="tension_patch",
                timestamp=now_iso,
                properties={
                    "tension_id": tension_id,
                    "actions": actions,
                    "breach_count": len(breaches),
                },
            ))
            mg_updates.append(patch_id)

        events.append({
            "topic": "drift_signal",
            "subtype": "pts_patch_issued",
            "tensionId": tension_id,
            "patchId": patch_id,
            "recommendedActions": actions,
        })

        return FunctionResult(
            function_id="PDX-F11", success=True,
            events_emitted=events,
            mg_updates=mg_updates,
        )

    # ── PDX-F12: Lifecycle Transition ────────────────────────────

    def _lifecycle_transition(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Handle explicit lifecycle transitions (rebalance, archive).

        ── PDX-F12: lifecycle_transition ──
        """
        from core.paradox_ops import ParadoxRegistry, TensionLifecycle, TensionLifecycleState

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []

        registry: ParadoxRegistry = ctx.get("paradox_registry")  # type: ignore[assignment]
        tension_id = payload.get("tensionId", "")
        pts = registry.get(tension_id) if registry else None

        if pts is None:
            return FunctionResult(
                function_id="PDX-F12", success=False,
                error=f"PTS not found: {tension_id}",
            )

        target_str = payload.get("targetState", "")
        try:
            target = TensionLifecycleState(target_str)
        except ValueError:
            return FunctionResult(
                function_id="PDX-F12", success=False,
                error=f"Invalid target state: {target_str}",
            )

        lifecycle: TensionLifecycle = ctx.get("tension_lifecycle")  # type: ignore[assignment]
        if lifecycle is None:
            return FunctionResult(
                function_id="PDX-F12", success=False,
                error="No lifecycle tracker in context",
            )

        ok = lifecycle.transition(tension_id, target)
        if not ok:
            return FunctionResult(
                function_id="PDX-F12", success=False,
                error=f"Invalid transition from {pts.lifecycle_state} to {target_str}",
            )

        now = ctx.get("now", datetime.now(timezone.utc))
        pts.lifecycle_state = target.value
        pts.updated_at = now.isoformat() if hasattr(now, "isoformat") else str(now)
        registry.update(pts)

        subtype = "pts_rebalanced" if target == TensionLifecycleState.REBALANCED else "pts_lifecycle_transitioned"
        if target == TensionLifecycleState.ARCHIVED:
            subtype = "pts_archived"

        events.append({
            "topic": "drift_signal",
            "subtype": subtype,
            "tensionId": tension_id,
            "newState": target.value,
        })

        return FunctionResult(
            function_id="PDX-F12", success=True,
            events_emitted=events,
        )
