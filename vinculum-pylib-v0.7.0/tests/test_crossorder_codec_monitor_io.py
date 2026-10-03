import io,json
from contextlib import redirect_stdout,redirect_stderr
from dataclasses import replace
from pathlib import Path
import pytest
from vinculum import *
from vinculum.demos import bakers_dozen,codec_stress,demonstration_scope,declared_support
from vinculum.serialization import Scenario,scenario_from_dict,save_scenario,load_scenario,representation_from_dict
from vinculum.rdf import to_turtle,from_turtle,project_turtle,RDFFieldMap
from vinculum.report import html_report,write_csv,write_json
from vinculum.lattice_cli import main
from vinculum.utils import canonical_json,read_json,primitive


def test_codec_preserves_zero_and_detects_changed_coverage():
    s=codec_stress();r=s.evaluate();c=CodecEvaluator().evaluate(s.graph,r,s.transformations[0])
    assert c.status=='DISTORTION_OR_SUPPORT_GAP'
    kinds={f.kind for f in c.findings}
    assert {'NUMERIC_CONTENT_PRESERVED','VALUE_CHANGED','SCOPE_OR_MEANING_CHANGED'}<=kinds


def codec_pair(source_range,target_range,source_strength=.42,target_strength=.42):
    g=PairGraph();scope=demonstration_scope()
    for id,r,st in [('source',source_range,source_strength),('target',target_range,target_strength)]:
        g.add_node(Representation(id,'L',1,'e','c',r,'count',scope,support=declared_support(st)))
    g.add_pair('source','target')
    t=Transformation('tx',('source',),('target',))
    return g,t


def test_uncertain_source_preserved_faithfully_is_not_a_codec_error():
    g,t=codec_pair(NumericRange(0,1),NumericRange(0,1))
    c=CodecEvaluator().evaluate(g,g.evaluate(),t)
    assert c.status=='PRESERVED_WITHIN_DECLARED_SCOPE'


def test_codec_uncertainty_loss_not_hidden_by_range_containment():
    g,t=codec_pair(NumericRange(0,1),NumericRange.point(0))
    c=CodecEvaluator().evaluate(g,g.evaluate(),t)
    assert any(f.kind=='UNCERTAINTY_NARROWED' for f in c.findings)


def test_codec_declared_material_omission_and_addition():
    g,t=codec_pair(NumericRange.point(1),NumericRange.point(1))
    s=g.nodes['source'];x=replace(s,id='omitted');y=replace(s,id='added')
    g.add_node(x).add_node(y)
    t=Transformation('tx',('source','omitted'),('target','added'))
    c=CodecEvaluator().evaluate(g,g.evaluate(),t)
    assert c.material_source_coverage==.5 and c.material_target_coverage==.5
    assert {f.kind for f in c.findings}>={'MATERIAL_SOURCE_UNPAIRED','TARGET_ADDITION_UNSUPPORTED'}


def test_codec_stale_report_rejected_after_graph_changes():
    s=codec_stress();r=s.evaluate();s.graph.add_node(replace(next(iter(s.graph.nodes.values())),id='extra'))
    with pytest.raises(ValueError):CodecEvaluator().evaluate(s.graph,r,s.transformations[0])


def test_monitor_does_not_pair_on_value_and_does_not_evaluate_automatically():
    monitor=PairingMonitor();s=bakers_dozen();l,m=s.graph.nodes.values()
    assert monitor.ingest(l)==()
    proposals=monitor.ingest(m)
    assert len(proposals)==1 and proposals[0].match_score==1
    assert 'not a calibrated' in proposals[0].explanation
    g=PairGraph();assert not g.evaluate().pairs
    monitor.select(g,proposals[0],rationale='explicit review')
    assert g.evaluate().pairs[0].status is PairStatus.CONFLICT


def test_monitor_entity_mismatch_not_proposed():
    m=PairingMonitor();l,r=bakers_dozen().graph.nodes.values();m.ingest(l)
    assert m.ingest(replace(r,entity='another'))==()


def test_monitor_ambiguous_candidates_are_exposed():
    m=PairingMonitor();l,r=bakers_dozen().graph.nodes.values();m.ingest(l);m.ingest(replace(l,id='L2'))
    proposals=m.ingest(r)
    assert len(proposals)==2 and all(p.ambiguous for p in proposals)


def test_monitor_changed_id_and_buffer_exhaustion():
    m=PairingMonitor(max_nodes=1);l,r=bakers_dozen().graph.nodes.values();m.ingest(l)
    assert m.ingest(l)==()
    with pytest.raises(ValueError):m.ingest(replace(l,text='changed'))
    with pytest.raises(OverflowError):m.ingest(r)


def test_monitor_expiration_explicit():
    m=PairingMonitor();l,_=bakers_dozen().graph.nodes.values()
    l=replace(l,scope=replace(l.scope,timeless=False,window=TimeWindow.instant('2026-10-02T12:00Z')))
    m.ingest(l)
    assert m.expire_before('2026-10-02T13:00Z')==(l.id,)


def test_json_and_native_turtle_roundtrip_preserve_report():
    s=codec_stress()
    for restored in [scenario_from_dict(s.to_dict()),from_turtle(to_turtle(s))]:
        assert restored.evaluate().to_dict()==s.evaluate().to_dict()
        assert restored.graph.context==s.graph.context


def test_hinge_order_states_roundtrip():
    s=bakers_dozen();g=PairGraph();l,r=s.graph.nodes.values()
    h=HingeOrderState(3,PDProfile(.2,.8,'test'),declared_support(.7))
    g.add_node(l).add_node(r).add_pair(l.id,r.id,hinge_states=(h,))
    ss=Scenario(g,HingePolicy(),UnitRegistry.default())
    assert scenario_from_dict(ss.to_dict()).evaluate().to_dict()==ss.evaluate().to_dict()


def test_turtle_projection_tamper_rejected():
    text=to_turtle(bakers_dozen())
    assert 'vx:order 1' in text
    with pytest.raises(ValueError):from_turtle(text.replace('vx:order 1','vx:order 9',1))


def test_generic_ttl_requires_an_explicit_mapping():
    text='@prefix ex: <urn:example:> . ex:order ex:label "baker\'s dozen" ; ex:quantity 12 .'
    with pytest.raises(ValueError):from_turtle(text)
    mapping=RDFFieldMap('urn:example:label','urn:example:quantity','item_count','count',demonstration_scope())
    s=project_turtle(text,mapping,pair_unique=True)
    assert s.evaluate().pairs[0].status is PairStatus.CONFLICT
    assert s.evaluate().pairs[0].supported_collision_score is None


def test_ttl_multiple_values_not_auto_paired():
    text='@prefix ex: <urn:example:> . ex:order ex:label "baker\'s dozen" ; ex:quantity 12, 13 .'
    mapping=RDFFieldMap('urn:example:label','urn:example:quantity','item_count','count',demonstration_scope())
    assert not project_turtle(text,mapping,pair_unique=True).evaluate().pairs


def test_json_unknown_fields_and_duplicate_keys_rejected():
    d=bakers_dozen().to_dict();d['authoritative']=True
    with pytest.raises(ValueError):scenario_from_dict(d)
    with pytest.raises(ValueError):read_json('{"a":1,"a":2}')
    with pytest.raises(ValueError):read_json('{"a":NaN}')


def test_reports_escape_untrusted_text_and_csv_formulas(tmp_path):
    g=PairGraph();l,r=bakers_dozen().graph.nodes.values()
    l=replace(l,text='<script>alert(1)</script>',id='=1+1')
    g.add_node(l).add_node(r).add_pair(l.id,r.id)
    report=g.evaluate();h=html_report(report)
    assert '<script>alert' not in h and '&lt;script&gt;' in h
    paths=write_csv(report,tmp_path)
    assert len(paths)==5
    text=(tmp_path/'representations.csv').read_text(encoding='utf-8-sig')
    assert "'=1+1" in text


def test_cli_reports_and_strict_exit(tmp_path):
    s=bakers_dozen();p=tmp_path/'scenario.json';save_scenario(s,p)
    with redirect_stdout(io.StringIO()):
        assert main(['evaluate',str(p),'--out-dir',str(tmp_path/'out'),'--summary'])==0
        assert main(['evaluate',str(p),'--strict-exit'])==2
    assert (tmp_path/'out/report.html').is_file()
    with redirect_stderr(io.StringIO()):assert main(['evaluate',str(tmp_path/'missing.json')])==1


def test_semantic_negation_and_approximation_not_discarded():
    r=SemanticRegistry.default()
    for text in ["not a baker's dozen","about a dozen","probably a pair","airspace clear","couple"]:
        assert r.resolve(text).status=='UNRESOLVED'
    assert r.resolve("baker's dozen").quantity==NumericRange.point(13)
    assert r.resolve('within 30 days',concept='elapsed_time').quantity==NumericRange(0,30)


def test_ambiguous_semantic_rules_do_not_pick_a_winner():
    r=SemanticRegistry.default()
    r.register(NumericMeaningRule('other',r"baker's dozen",'item_count','count',NumericRange.point(14),'explicit competing rule',1))
    assert r.resolve("baker's dozen").status=='UNRESOLVED'


def test_adapter_contract_keeps_unhandled_segments_visible():
    from vinculum.adapters import AdapterRegistry,ExtractionBatch
    class Adapter:
        def extract(self,source,*,source_id):
            return ExtractionBatch('test',source_id,(),(source,))
    r=AdapterRegistry().register('test',Adapter()).extract('test','unhandled',source_id='source')
    assert r.unresolved_segments==('unhandled',)


def test_report_delta_preserves_percentage_points_not_just_base_ratio():
    p=codec_stress().evaluate().pair('coverage-overclaim')
    assert p.discrepancy['signed_delta']=='-0.4'
    assert p.discrepancy['signed_delta_left_unit']=='-40'
