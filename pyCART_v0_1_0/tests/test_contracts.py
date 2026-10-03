from dataclasses import FrozenInstanceError, replace
import pytest
from deepsigma_cartography import Atlas, Edge, Evidence, MapView, Node, Predicate, Status, ValidationError
from deepsigma_cartography.sample import AS_OF
from deepsigma_cartography.util import canonical_json, parse_json, timestamp

@pytest.mark.parametrize("value", [-1, 2, float('nan'), float('inf'), True, "0.8"])
def test_invalid_confidence(value):
    with pytest.raises(ValidationError): Node('x', 'X', 'claim', confidence=value)

@pytest.mark.parametrize("value", [0, 1, .45, None])
def test_valid_confidence(value):
    assert Node('x', 'X', 'claim', confidence=value).confidence == value

@pytest.mark.parametrize("value", ['', None, '2026-10-03', '2026-10-03T12:00:00', 'not-a-time'])
def test_bad_timestamps(value):
    with pytest.raises(ValidationError): timestamp(value)

def test_time_normalization():
    assert timestamp('2026-10-03T08:00:00-04:00') == timestamp(AS_OF)

def test_empty_interval():
    with pytest.raises(ValidationError): Node('x','X','claim',valid_from=AS_OF,valid_to=AS_OF)

def test_invalid_status():
    with pytest.raises(ValidationError): Node('x','X','claim',status='guaranteed_true')

def test_deep_immutability():
    attrs = {'nested': {'list': [1]}}
    node = Node('x','X','claim',attributes=attrs)
    attrs['nested']['list'].append(2)
    assert node.attributes['nested']['list'] == (1,)
    with pytest.raises(TypeError): node.attributes['nested']['x'] = 2
    with pytest.raises(FrozenInstanceError): node.label = 'changed'

def test_non_json_attributes():
    with pytest.raises(ValidationError): Node('x','X','claim',attributes={'object': object()})
    with pytest.raises(ValidationError): Node('x','X','claim',attributes={1: 'bad key'})

def test_duplicate_nodes(atlas):
    with pytest.raises(ValidationError): replace(atlas, nodes=atlas.nodes + (atlas.nodes[0],))

def test_cross_record_id_collision(atlas):
    with pytest.raises(ValidationError): replace(atlas,evidence=atlas.evidence+(Evidence(atlas.nodes[0].id,'s'),))

def test_dangling_edge(atlas):
    with pytest.raises(ValidationError): replace(atlas,edges=atlas.edges+(Edge('bad','absent','depends_on',atlas.nodes[0].id),))

def test_missing_evidence_reference():
    with pytest.raises(ValidationError): Atlas('a','A',(Node('x','X','claim',evidence_ids=('missing',)),))

def test_unknown_predicate(atlas):
    with pytest.raises(ValidationError): replace(atlas,edges=(replace(atlas.edges[0],predicate='magic'),))

def test_explicit_custom_predicate(atlas):
    updated = replace(atlas, predicates=atlas.predicates+(Predicate('custom','Custom','Declared relation'),),
                      edges=(replace(atlas.edges[0],predicate='custom'),))
    assert updated.edges[0].predicate == 'custom'

def test_predicate_type_constraint():
    with pytest.raises(ValidationError):
        Atlas('a','A',(Node('x','X','decision'),Node('y','Y','claim')),(Edge('e','x','authorized_by','y'),))

def test_invalid_predicate_orientation():
    with pytest.raises(ValidationError): Predicate('p','P','P',dependency='both')

def test_invalid_evidence_hash():
    with pytest.raises(ValidationError): Evidence('e','s',sha256='bad')

def test_reordered_input_same_digest(atlas):
    reverse = replace(atlas,nodes=atlas.nodes[::-1],edges=atlas.edges[::-1],evidence=atlas.evidence[::-1],predicates=atlas.predicates[::-1])
    assert reverse.fingerprint == atlas.fingerprint

def test_json_roundtrip(atlas,tmp_path):
    assert Atlas.load(atlas.save(tmp_path/'atlas.json')).fingerprint == atlas.fingerprint

def test_canonical_json_roundtrip(atlas):
    assert Atlas.from_dict(parse_json(canonical_json(atlas))).fingerprint == atlas.fingerprint

@pytest.mark.parametrize('payload',['{"a":1,"a":2}','{"value":NaN}','{"value":Infinity}'])
def test_ambiguous_json_rejected(payload):
    with pytest.raises(ValidationError): parse_json(payload)

def test_schema_required(atlas):
    d=atlas.to_dict();del d['schema']
    with pytest.raises(ValidationError): Atlas.from_dict(d)

def test_unknown_fields_rejected(atlas):
    d=atlas.to_dict();d['authoritative']=True
    with pytest.raises(ValidationError): Atlas.from_dict(d)

def test_validity_half_open_and_retraction():
    a=Atlas('a','A',(Node('x','X','claim',valid_from=AS_OF,valid_to='2026-10-04T00:00:00Z'),Node('y','Y','claim',status=Status.RETRACTED)))
    assert [n.id for n in a.view(as_of=AS_OF).nodes] == ['x']
    assert a.view(as_of='2026-10-04T00:00:00Z').nodes == ()

def test_scope_and_layer_filters(atlas):
    assert atlas.view(as_of=AS_OF,scopes=()).nodes == ()
    v=atlas.view(as_of=AS_OF,layers=('meaning',))
    assert all(n.layer=='meaning' for n in v.nodes)
    assert all(e.source in v.atlas._nodes and e.target in v.atlas._nodes for e in v.edges)

def test_inference_filter():
    a=Atlas('a','A',(Node('a','A','claim'),Node('b','B','claim',status=Status.INFERRED)),(Edge('e','a','depends_on','b'),))
    v=a.view(as_of=AS_OF,include_inferred=False)
    assert len(v.nodes)==1 and not v.edges

def test_view_is_time_bound(atlas):
    assert atlas.view(as_of=AS_OF).fingerprint != atlas.view(as_of='2026-10-03T13:00:00Z').fingerprint

def test_bad_manual_view(atlas):
    with pytest.raises(ValidationError): MapView(atlas,AS_OF,'fake')
    with pytest.raises(ValidationError): MapView(atlas,AS_OF,atlas.fingerprint,scopes=('other',))
