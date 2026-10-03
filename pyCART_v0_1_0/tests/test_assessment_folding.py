from dataclasses import replace
import pytest
from deepsigma_cartography import Atlas, CoverageRequirement, Edge, Evidence, FoldedMap, Node, Status, ValidationError, assess, compare, fold
from deepsigma_cartography.sample import AS_OF, sample_candidate
from deepsigma_cartography.util import canonical_json, parse_json


def test_demo_expected_gaps(view):
    report=assess(view)
    codes=[f.code for f in report.findings]
    assert len(codes)==6
    assert codes.count('EVIDENCE_GAP')==2
    assert {'AUTHORITY_GAP','TEMPORAL_GAP','SEMANTIC_ORPHAN','UNCERTAINTY'}<=set(codes)

def test_candidate_changes_are_visible(atlas):
    candidate=sample_candidate(atlas)
    assert len(assess(candidate.view(as_of=AS_OF)).findings)==3
    assert len(compare(atlas,candidate).deltas)==4

def test_empty_is_not_perfect():
    result=assess(Atlas('a','A').view(as_of=AS_OF))
    assert result.metrics['recorded_evidence_coverage'] is None
    assert result.metrics['recorded_authority_reference_coverage'] is None
    assert result.metrics['requirement_coverage'] is None

def test_expired_evidence_does_not_count(view):
    assert any(f.code=='EVIDENCE_GAP' and f.subject_ids==('claim:current',) for f in assess(view).findings)

def test_unknown_authority_does_not_count():
    a=Atlas('a','A',(Node('d','D','decision'),Node('r','R','authority',status=Status.UNKNOWN)),(Edge('e','d','authorized_by','r'),))
    assert any(f.code=='AUTHORITY_GAP' for f in assess(a.view(as_of=AS_OF)).findings)

def test_explicit_coverage(view):
    r=assess(view,requirements=(CoverageRequirement('mission:readiness','requires','capability'),CoverageRequirement('decision:publish','authorized_by','authority')))
    assert r.metrics['requirements_evaluated']==2
    assert r.metrics['requirements_satisfied']==1
    assert r.metrics['requirement_coverage']==.5

def test_multiple_edges_not_multiple_coverage_targets():
    a=Atlas('a','A',(Node('a','A','concept'),Node('b','B','concept')),(Edge('e1','a','depends_on','b'),Edge('e2','a','depends_on','b')))
    r=assess(a.view(as_of=AS_OF),requirements=(CoverageRequirement('a','depends_on',minimum=2),))
    assert any(f.code=='COVERAGE_GAP' for f in r.findings)

def test_requirement_out_of_view_fails(view):
    with pytest.raises(ValidationError): assess(view,requirements=(CoverageRequirement('missing','depends_on'),))
    with pytest.raises(ValidationError): assess(view,requirements=(CoverageRequirement('claim:current','missing'),))

def test_no_natural_language_contradiction_inference():
    a=Atlas('a','A',(Node('a','The system is ready','claim'),Node('b','The system is not ready','claim')))
    v=a.view(as_of=AS_OF)
    assert not any(f.code=='CONTRADICTION_RECORDED' for f in assess(v).findings)
    a=replace(a,edges=(Edge('e','a','contradicts','b'),))
    assert any(f.code=='CONTRADICTION_RECORDED' for f in assess(a.view(as_of=AS_OF)).findings)

def test_explicit_cycle_report():
    a=Atlas('a','A',(Node('a','A','claim'),),(Edge('e','a','depends_on','a'),))
    assert any(f.code=='DEPENDENCY_CYCLE' for f in assess(a.view(as_of=AS_OF)).findings)

def test_report_deterministic(view):
    assert canonical_json(assess(view)) == canonical_json(assess(view))

def test_fold_every_node_and_edge(view):
    f=fold(view)
    assert sorted(n for g in f.groups for n in g.member_ids)==sorted(n.id for n in view.nodes)
    assert sorted(e for l in f.links for e in l.edge_ids)==sorted(e.id for e in view.edges)
    assert f.unfold().fingerprint==view.fingerprint

def test_fold_internal_edges_preserved():
    a=Atlas('a','A',(Node('a','A','concept'),Node('b','B','concept')),(Edge('e','a','depends_on','b'),))
    f=fold(a.view(as_of=AS_OF))
    assert f.links[0].internal and f.links[0].edge_ids==('e',)

def test_fold_json_roundtrip(view):
    f=fold(view,by='kind')
    result=FoldedMap.from_dict(parse_json(canonical_json(f)))
    assert result.unfold().fingerprint==view.fingerprint

def test_fold_tamper_detected(view):
    d=fold(view).to_dict();d['groups'][0]['member_ids']=[]
    with pytest.raises(ValidationError): FoldedMap.from_dict(d)

def test_bad_fold_key(view):
    with pytest.raises(ValidationError): fold(view,by='guessed-truth')

def test_no_mutation_from_assessment_or_fold(atlas):
    before=atlas.fingerprint
    view=atlas.view(as_of=AS_OF);assess(view);fold(view)
    assert atlas.fingerprint==before

def test_diff_metadata_and_no_change(atlas):
    assert not compare(atlas,atlas).deltas
    d=compare(atlas,replace(atlas,title='New title'))
    assert d.deltas[0].changed_fields==('title',)
    with pytest.raises(ValidationError): compare(atlas,replace(atlas,id='different'))
