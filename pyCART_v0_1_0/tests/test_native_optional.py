"""Executed against the provided 2.1.2 repository snapshot; skipped without core."""
import pytest
from deepsigma_cartography import assess, cerpa_review, from_memory_graph, patch_proposals


def test_native_memory_graph_export_contract():
    native=pytest.importorskip('core.memory_graph')
    graph=native.MemoryGraph()
    graph.add_episode({'episode_id':'ep:synthetic','decision_type':'review','actions':[],
                       'context':{'evidence_refs':['synthetic-source']}})
    atlas=from_memory_graph(graph,atlas_id='a',title='Native adapter fixture')
    assert len(atlas.nodes)==graph.node_count==2
    assert len(atlas.edges)==graph.edge_count==1
    assert atlas.node('ep:synthetic').kind=='episode'

def test_native_cerpa_constructor_contract(view):
    native=pytest.importorskip('core.cerpa.models')
    report=assess(view)
    review=native.Review(**cerpa_review(view,report,claim_id='claim:current',event_id='event:review',domain='test'))
    patches=[native.Patch(**p) for p in patch_proposals(report,review_id=review.id,domain='test')]
    assert review.metadata['status']=='PROPOSED'
    assert len(patches)==len(report.findings)
    assert all(p.metadata['status']=='PROPOSED' for p in patches)
