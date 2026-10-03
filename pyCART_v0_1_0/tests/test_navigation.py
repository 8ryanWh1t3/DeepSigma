from dataclasses import replace
import pytest
from deepsigma_cartography import Atlas, Edge, Node, ValidationError, dependencies, dependency_cycles, fold, impact, reach, trace
from deepsigma_cartography.sample import AS_OF


def test_semantic_route(view):
    result=trace(view,'mission:readiness','evidence:report')
    assert result.found and len(result.steps)==3
    assert [s.predicate for s in result.steps]==['requires','depends_on','supported_by']
    assert result.view_fingerprint==view.fingerprint

def test_reverse_direction_keeps_original_edge(view):
    result=trace(view,'evidence:report','claim:current',direction='in')
    step=result.steps[0]
    assert step.from_id=='evidence:report' and step.stored_source=='claim:current'

def test_not_found_is_not_false_claim(view):
    result=trace(view,'claim:unknown','mission:readiness')
    assert result.status=='NO_RECORDED_ROUTE' and not result.found

def test_depth_limit_disclosed(view):
    result=trace(view,'mission:readiness','evidence:report',max_depth=1)
    assert result.status=='SEARCH_BOUND_REACHED' and result.depth_limited

def test_no_limit_if_frontier_has_no_unvisited_nodes(view):
    assert not reach(view,'claim:unknown',max_depth=0).depth_limited

def test_self_route(view):
    result=trace(view,'claim:current','claim:current',max_depth=0)
    assert result.found and not result.steps

def test_unknown_node_is_input_error(view):
    with pytest.raises(ValidationError): trace(view,'missing','claim:current')
    with pytest.raises(ValidationError): trace(view,'claim:current','missing')

@pytest.mark.parametrize('limit',[-1,True,1.5])
def test_bad_limit(view,limit):
    with pytest.raises(ValidationError): reach(view,'claim:current',max_depth=limit)

def test_unknown_direction(view):
    with pytest.raises(ValidationError): reach(view,'claim:current',mode='magical')

def test_predicate_filter(view):
    assert not trace(view,'mission:readiness','evidence:report',predicates=('depends_on',)).found
    with pytest.raises(ValidationError): reach(view,'claim:current',predicates=('typo',))

def test_impact_follows_dependents(view):
    result=impact(view,'evidence:report')
    assert set(result.node_ids)=={'claim:current','capability:intake','mission:readiness','decision:publish'}
    assert 'event:review' not in result.node_ids

def test_depends_on_vs_supports():
    a=Atlas('a','A',(Node('d','D','decision'),Node('s','S','claim')),(Edge('e','s','supports','d'),))
    v=a.view(as_of=AS_OF)
    assert dependencies(v,'d').node_ids==('s',)
    assert impact(v,'s').node_ids==('d',)

def test_shortest_path_tie_deterministic():
    nodes=tuple(Node(x,x,'concept') for x in ('a','b','c','d'))
    edges=(Edge('z','a','depends_on','c'),Edge('y','c','depends_on','d'),Edge('ea','a','depends_on','b'),Edge('eb','b','depends_on','d'))
    a=Atlas('a','A',nodes,edges)
    assert [s.to_id for s in trace(a.view(as_of=AS_OF),'a','d').steps]==['b','d']

def test_dependency_cycle_and_self_loop():
    a=Atlas('a','A',tuple(Node(x,x,'concept') for x in 'abc'),
            (Edge('e1','a','depends_on','b'),Edge('e2','b','depends_on','a'),Edge('e3','c','depends_on','c')))
    assert dependency_cycles(a.view(as_of=AS_OF)) == (('a','b'),('c',))

def test_unrelated_cycle_is_not_dependency_cycle():
    a=Atlas('a','A',(Node('a','A','concept'),Node('b','B','concept')),
            (Edge('e1','a','relates_to','b'),Edge('e2','b','relates_to','a')))
    assert dependency_cycles(a.view(as_of=AS_OF))==()

def test_long_chain_no_recursion_error():
    nodes=tuple(Node(str(i),str(i),'concept') for i in range(2500))
    edges=tuple(Edge('e'+str(i),str(i),'depends_on',str(i+1)) for i in range(2499))
    assert dependency_cycles(Atlas('a','A',nodes,edges).view(as_of=AS_OF))==()

def test_fold_routes_rejected(view):
    with pytest.raises(ValidationError): reach(fold(view),'claim:current')
