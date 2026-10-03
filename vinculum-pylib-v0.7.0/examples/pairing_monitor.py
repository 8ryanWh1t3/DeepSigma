"""Pair formation is separate from comparison. No automatic action or authority."""
from vinculum import PairGraph, PairingMonitor
from vinculum.demos import bakers_dozen
fixture = bakers_dozen()
monitor = PairingMonitor()
proposals = []
for node in fixture.graph.nodes.values():
    proposals.extend(monitor.ingest(node))
reviewed = PairGraph('MONITOR-SELECTED')
for proposal in proposals:
    print(proposal)
    # Selection is an explicit application decision, not a confidence threshold trick.
    monitor.select(reviewed, proposal, rationale='demonstration: caller selected this exact transaction pair')
print(reviewed.evaluate().summary)
