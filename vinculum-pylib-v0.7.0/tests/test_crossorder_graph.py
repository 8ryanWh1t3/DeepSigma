import pytest
from dataclasses import replace
from vinculum import *
from vinculum.demos import bakers_dozen, codec_stress, demonstration_scope, declared_support


def test_unpaired_nodes_are_not_scored():
    g=PairGraph(); g.add_node(next(iter(bakers_dozen().graph.nodes.values())))
    r=g.evaluate()
    assert not r.pairs and r.summary['status']=='UNMEASURED'
    assert len(r.matrix['cells'])==25 and all(c['status']=='UNPAIRED' for c in r.matrix['cells'])
    assert r.summary['max_raw_collision_score'] is None


def test_cross_order_pair_is_not_forced_to_diagonal():
    g=PairGraph(); l,m=bakers_dozen().graph.nodes.values()
    g.add_node(l).add_node(replace(m,order=4)).add_pair(l.id,m.id)
    r=g.evaluate()
    c=next(c for c in r.matrix['cells'] if c['language_order']==1 and c['mathematics_order']==4)
    assert c['pair_ids'] and c['status']=='CONFLICT'
    assert r.matrix['evaluated_order_slots']==1


def test_orders_beyond_five_extend_matrix():
    g=PairGraph(); l,m=bakers_dozen().graph.nodes.values()
    g.add_node(replace(l,order=6)).add_node(m).add_pair(l.id,m.id)
    assert g.evaluate().matrix['rows']==6


def test_hinge_higher_order_p_and_d_are_pair_local():
    g=PairGraph(); l,m=bakers_dozen().graph.nodes.values()
    state=HingeOrderState(3,PDProfile(.4,.6,'hypothesis about the mapping'),declared_support(.7,order=3))
    g.add_node(l).add_node(m).add_pair(l.id,m.id,hinge_states=(state,),alignment_support=1,alignment_basis='test')
    r=g.evaluate().pairs[0]
    assert r.supported_collision_score==70
    a=next(a for a in r.hinge_assessments if a['order']==3)
    assert a['pd']['P']==.4 and a['pair_id']==r.pair_id


def test_higher_order_hinge_unknown_does_not_hide_raw_discrepancy():
    g=PairGraph(); l,m=bakers_dozen().graph.nodes.values()
    g.add_node(l).add_node(m).add_pair(l.id,m.id,hinge_states=(HingeOrderState(5),),alignment_support=1,alignment_basis='test')
    r=g.evaluate().pairs[0]
    assert r.status is PairStatus.CONFLICT and r.raw_collision_score==100 and r.supported_collision_score is None


def test_no_duplicate_ids_or_duplicate_ordered_pairs():
    g=bakers_dozen().graph
    with pytest.raises(ValueError): g.add_node(g.nodes['L-order'])
    with pytest.raises(ValueError): g.add_pair('L-order','M-receipt',id='other')


def test_missing_pair_endpoint():
    with pytest.raises(ValueError): PairGraph().add_pair('not','there')


def test_narrative_changes_do_not_change_the_measured_result():
    g=bakers_dozen().graph
    a=g.evaluate().to_dict(); g.context=NarrativeContext.deep_sigma(); b=g.evaluate().to_dict()
    assert a==b


def test_dependency_cycle_rejected():
    l,m=bakers_dozen().graph.nodes.values(); g=PairGraph()
    g.add_node(replace(l,depends_on=(m.id,))).add_node(replace(m,depends_on=(l.id,)))
    with pytest.raises(ValueError): g.evaluate()


def test_missing_dependency_marks_support_unknown_not_discrepancy_zero():
    l,m=bakers_dozen().graph.nodes.values(); g=PairGraph()
    g.add_node(replace(l,depends_on=('missing',))).add_node(m).add_pair(l.id,m.id,alignment_support=1,alignment_basis='test')
    r=g.evaluate().pairs[0]
    assert r.raw_collision_score==100 and r.supported_collision_score is None
    assert r.support['missing_dependencies']


def test_shared_provenance_never_claims_independence():
    l,m=bakers_dozen().graph.nodes.values(); g=PairGraph()
    g.add_node(replace(l,source_ids=('one',))).add_node(replace(m,source_ids=('one',))).add_pair(l.id,m.id)
    assert any('shared source' in w for w in g.evaluate().pairs[0].dependency_warnings)


def test_nested_groups_do_not_double_count_pairs():
    g=bakers_dozen().graph
    g.add_group(ObjectGroup('doc','document',tuple(g.nodes),children=('episode-1','claim-1')))
    r=g.evaluate()
    assert r.groups['doc']['summary']['selected_pairs']==1


def test_group_cycle_rejected():
    g=PairGraph();g.add_group(ObjectGroup('a','doc',children=('b',))).add_group(ObjectGroup('b','doc',children=('a',)))
    with pytest.raises(ValueError):g.evaluate()


def test_replay_is_deterministic_across_insertion_order():
    s=codec_stress(); g=PairGraph(s.graph.id)
    for n in reversed(tuple(s.graph.nodes.values())):g.add_node(n)
    for p in reversed(tuple(s.graph.pairs.values())):g.add_pair_spec(p)
    for group in reversed(tuple(s.graph.groups.values())):g.add_group(group)
    assert g.evaluate().to_dict()==s.evaluate().to_dict()


def test_codec_stress_covers_all_language_orders_and_separates_issues():
    r=codec_stress().evaluate()
    assert {n.order for n in r.representations if n.side is Side.LANGUAGE}=={1,2,3,4,5}
    assert r.pair('coverage-overclaim').status is PairStatus.CONFLICT
    assert r.pair('unsupported-absence').status is PairStatus.NOT_COMPARABLE
    assert r.pair('uncertain-count').status is PairStatus.PARTIAL
    assert r.pair('zero-preserved').status is PairStatus.ALIGNED
    assert r.summary['max_raw_collision_score']==100


def test_extreme_finite_weights_do_not_overflow_summary():
    l,m=bakers_dozen().graph.nodes.values();g=PairGraph()
    g.add_node(l).add_node(m).add_pair(l.id,m.id,weight=1e308)
    assert g.evaluate().summary['weighted_mean_raw_collision_score']==100


def test_declared_id_sequences_cannot_be_strings():
    with pytest.raises(TypeError): Representation('n','L',1,'e','c',source_ids='abc')
