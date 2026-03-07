"""Primitive MG — maps primitive envelopes to Memory Graph nodes and edges.

Bridges the PrimitiveEnvelope layer with the existing MemoryGraph,
creating typed nodes for each envelope and provenance edges for
supersede chains and coherence loop step sequences.
"""

from __future__ import annotations

from typing import Any, Dict

from .memory_graph import EdgeKind, GraphEdge, GraphNode, MemoryGraph, NodeKind
from .primitive_envelope import PrimitiveEnvelope
from .primitives import PrimitiveType


# ── Mapping ────────────────────────────────────────────────────


PRIMITIVE_TO_NODE_KIND: Dict[PrimitiveType, NodeKind] = {
    PrimitiveType.CLAIM: NodeKind.CLAIM,
    PrimitiveType.EVENT: NodeKind.EPISODE,
    PrimitiveType.REVIEW: NodeKind.REVIEW,
    PrimitiveType.PATCH: NodeKind.PATCH,
    PrimitiveType.APPLY: NodeKind.APPLY,
}


# ── Ingest helpers ─────────────────────────────────────────────


def ingest_envelope(mg: MemoryGraph, envelope: PrimitiveEnvelope) -> str:
    """Add a PrimitiveEnvelope as a node in the Memory Graph.

    If the envelope has a parent (supersede chain), a DERIVED_FROM
    edge is created from the parent to the new node.

    Returns the node_id.
    """
    node_kind = PRIMITIVE_TO_NODE_KIND[envelope.primitive_type]
    node = GraphNode(
        node_id=envelope.envelope_id,
        kind=node_kind,
        label=f"{envelope.primitive_type.value}:v{envelope.version}",
        timestamp=envelope.created_at,
        properties={
            "primitive_type": envelope.primitive_type.value,
            "version": envelope.version,
            "source": envelope.source,
            "sealed": envelope.sealed,
        },
    )
    mg._add_node(node)

    if envelope.parent_envelope_id is not None:
        mg._add_edge(GraphEdge(
            source_id=envelope.parent_envelope_id,
            target_id=envelope.envelope_id,
            kind=EdgeKind.DERIVED_FROM,
        ))

    return envelope.envelope_id


def ingest_loop_result(mg: MemoryGraph, loop_result: Any) -> None:
    """Ingest all step envelopes from a CoherenceLoopResult.

    Creates nodes for each step envelope and PRECEDED_BY edges
    linking consecutive steps in order.
    """
    prev_id = None
    for record in loop_result.steps:
        node_id = ingest_envelope(mg, record.envelope)
        if prev_id is not None:
            mg._add_edge(GraphEdge(
                source_id=prev_id,
                target_id=node_id,
                kind=EdgeKind.PRECEDED_BY,
            ))
        prev_id = node_id
