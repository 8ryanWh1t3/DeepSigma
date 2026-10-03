from dataclasses import replace
import csv
import hashlib
import json
import pytest
from deepsigma_cartography import Atlas, Edge, Evidence, Node, ValidationError, assess, cerpa_review, export_csv, export_jsonl, export_jsonld, export_ntriples, from_memory_graph, import_jsonl, patch_proposals, verify_evidence_file, vinculum_projection
from deepsigma_cartography.exports import BASE, RDF, jsonld_document
from deepsigma_cartography.sample import AS_OF


def test_jsonl_roundtrip(atlas,tmp_path):
    assert import_jsonl(export_jsonl(atlas,tmp_path/'a.jsonl')).fingerprint==atlas.fingerprint

def test_jsonl_duplicate_header_rejected(atlas,tmp_path):
    p=export_jsonl(atlas,tmp_path/'a.jsonl');s=p.read_text();p.write_text(s+s.splitlines()[0]+'\n')
    with pytest.raises(ValidationError): import_jsonl(p)

def test_jsonl_unknown_record_rejected(tmp_path):
    p=tmp_path/'a.jsonl';p.write_text('{"record_type":"magic","payload":{}}')
    with pytest.raises(ValidationError): import_jsonl(p)

def test_csv_literal_formula_neutralized(atlas,tmp_path):
    a=replace(atlas,nodes=tuple(replace(n,label='=HYPERLINK("evil")') if n.id=='claim:current' else n for n in atlas.nodes))
    out=export_csv(a,tmp_path/'csv')
    with (out/'nodes.csv').open() as f: rows=list(csv.DictReader(f))
    assert next(r['label'] for r in rows if r['id']=='claim:current').startswith("'=")
    assert Atlas.load(out/'atlas.json').fingerprint==a.fingerprint

def test_rdf_edges_are_reified_not_bare_facts(view,tmp_path):
    doc=jsonld_document(view)
    statements=[r for r in doc['@graph'] if r['@type']=='rdf:Statement']
    assert len(statements)==len(view.edges)
    p=export_ntriples(view,tmp_path/'a.nt')
    assert 'rdf-syntax-ns#Statement' in p.read_text()
    assert not any(line.split(' ', 2)[1] == '<urn:deep-sigma:cartography:predicate:depends_on>' for line in p.read_text().splitlines())

def test_rdf_parses_and_graphs_agree(view,tmp_path):
    rdflib=pytest.importorskip('rdflib')
    nt=export_ntriples(view,tmp_path/'a.nt');ld=export_jsonld(view,tmp_path/'a.jsonld')
    left=rdflib.Graph().parse(nt,format='nt');right=rdflib.Graph().parse(ld,format='json-ld')
    assert set(left)==set(right)
    assert len(left)>len(view.nodes)+len(view.edges)

def test_rdf_unicode_escaping(tmp_path):
    rdflib=pytest.importorskip('rdflib')
    a=Atlas('a','A',(Node('Ω<>','Σ "quoted" 😀','concept',attributes={'s':'line\nnext'}),))
    p=export_ntriples(a.view(as_of=AS_OF),tmp_path/'u.nt')
    assert len(rdflib.Graph().parse(p,format='nt'))>0

def test_memory_graph_preserves_fields_and_duplicates():
    source={'nodes':[{'node_id':'c','kind':'claim','label':'Claim','timestamp':'not interpreted as validity',
                      'properties':{'confidence':95}}, {'node_id':'ev','kind':'evidence','label':'report:section2','properties':{}}],
            'edges':[{'source_id':'c','target_id':'ev','kind':'claim_evidence','properties':{'why':'declared'}},
                     {'source_id':'c','target_id':'ev','kind':'claim_evidence','properties':{'why':'declared'}}]}
    a=from_memory_graph(source,atlas_id='a',title='A')
    assert len(a.edges)==2 and a.edges[0].id!=a.edges[1].id
    assert a.node('c').attributes['source_record']['properties']['confidence']==95
    assert a.node('c').confidence is None
    assert a.node('c').valid_from is None
    assert not any(f.code=='EVIDENCE_GAP' for f in assess(a.view(as_of=AS_OF)).findings)

def test_memory_graph_unknown_relation_is_not_guessed():
    data={'nodes':[{'node_id':'a','kind':'claim','label':'A'},{'node_id':'b','kind':'claim','label':'B'}],
          'edges':[{'source_id':'a','target_id':'b','kind':'mystery'}]}
    a=from_memory_graph(json.dumps(data),atlas_id='a',title='A')
    assert a._predicates['mystery'].dependency=='none'

def test_memory_graph_native_to_json_shape():
    class Graph:
        def to_json(self): return '{"nodes":[],"edges":[]}'
    assert from_memory_graph(Graph(),atlas_id='a',title='A').nodes==()

def test_bad_memory_graph_rejected():
    with pytest.raises(ValidationError): from_memory_graph({'nodes':[]},atlas_id='a',title='A')

def test_vinculum_is_readonly_contract(view):
    payload=vinculum_projection(view,assess(view))
    assert payload['read_only'] is True
    assert payload['integration_status']=='interchange_contract_only'
    assert payload['authority']=='not_evaluated'

def test_assessment_binding_is_enforced(atlas,view):
    another=atlas.view(as_of='2026-10-03T13:00:00Z')
    with pytest.raises(ValidationError): vinculum_projection(another,assess(view))

def test_cerpa_drafts_do_not_grant_authority(view):
    result=assess(view)
    review=cerpa_review(view,result,claim_id='claim:current',event_id='event:review',domain='test')
    assert review['metadata']['status']=='PROPOSED'
    assert review['drift_detected'] is False and review['metadata']['drift_status']=='not_evaluated'
    proposals=patch_proposals(result,review_id=review['id'],domain='test')
    assert len(proposals)==len(result.findings)
    assert all(p['metadata']['status']=='PROPOSED' for p in proposals)
    assert all(p['action']=='request_review' for p in proposals)

def test_cerpa_requires_explicit_claim_event(view):
    with pytest.raises(ValidationError): cerpa_review(view,assess(view),claim_id='mission:readiness',event_id='event:review',domain='test')

def test_evidence_file_checks_bytes_only(tmp_path):
    p=tmp_path/'data.txt';p.write_bytes(b'example')
    e=Evidence('e','local',sha256=hashlib.sha256(b'example').hexdigest())
    assert verify_evidence_file(e,str(p))['matches'] is True
    p.write_bytes(b'different')
    assert verify_evidence_file(e,str(p))['matches'] is False
    with pytest.raises(ValidationError): verify_evidence_file(Evidence('e','s'),str(p))
