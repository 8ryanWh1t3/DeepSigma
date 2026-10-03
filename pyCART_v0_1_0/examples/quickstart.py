"""Run after installing the wheel: python examples/quickstart.py"""
from deepsigma_cartography import Atlas, Edge, Evidence, Node, assess, impact, trace

atlas = Atlas(
    id="atlas:example",
    title="Synthetic decision dependencies",
    evidence=(Evidence("ev:source", "synthetic://example", "Illustrative source record"),),
    nodes=(
        Node("decision:1", "Publish a review packet", "decision", evidence_ids=("ev:source",)),
        Node("claim:1", "The packet is ready for review", "claim", evidence_ids=("ev:source",)),
        Node("authority:1", "Review role", "authority"),
    ),
    edges=(
        Edge("edge:1", "decision:1", "depends_on", "claim:1", evidence_ids=("ev:source",)),
        Edge("edge:2", "decision:1", "authorized_by", "authority:1", evidence_ids=("ev:source",)),
    ),
)
view = atlas.view(as_of="2026-10-03T12:00:00Z")
print(trace(view, "decision:1", "claim:1").to_dict())
print(impact(view, "claim:1").node_ids)
print(assess(view).to_dict())
# The authority edge is a recorded reference, not a verified permission grant.
