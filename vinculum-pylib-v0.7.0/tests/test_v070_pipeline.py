import copy
import json
from pathlib import Path
import subprocess
import sys
import pytest
from vinculum import VinculumPipeline,SupportFactor,SupportProfile,PDProfile,NumericRange
from vinculum.higher_order import HigherOrderPolicy,assess_factors,freshness_index
from vinculum.evidence import EvidenceSource,EvidenceRegistry
from vinculum.ontology import OntologyRegistry
from vinculum.serialization import load_scenario
from vinculum.exports import pipeline_html,result_turtle
from vinculum.utils import primitive

EX=Path(__file__).resolve().parents[1]/'examples'

def bakery():return json.loads((EX/'bakery_pipeline.json').read_text())
def stress():return json.loads((EX/'cross_order_pipeline.json').read_text())

def test_pipeline_bakery_raw_correct():
    r=VinculumPipeline().run(bakery())
    assert r.report.pairs[0].status.value=='CONFLICT'
    assert r.report.pairs[0].discrepancy['signed_delta']=='-1'
    assert len(r.sources)==2 and len(r.extraction)==2
    assert [s['stage']for s in r.stage_trace]==['INPUT','INGEST','REPRESENT','PAIR','EVALUATE','AGGREGATE','OUTPUT']
    assert r.stage_trace[-1]['automatic_actions']==0
    assert r.sources[0].sha256 is not None
    assert r.report.pairs[0].supported_collision_score is None

def test_pipeline_replay_identity():
    job=bakery();before=copy.deepcopy(job)
    a=VinculumPipeline().run(job);b=VinculumPipeline().run(a.replay_job)
    assert job==before
    assert a.to_dict()==b.to_dict()
    assert a.job_fingerprint==b.job_fingerprint

def test_stress_baseline_statuses_unchanged():
    result=VinculumPipeline().run(stress())
    old=load_scenario(EX/'cross_order_scenario.json').evaluate()
    assert [(p.pair_id,p.status.value,p.discrepancy,p.raw_collision_score)for p in result.report.pairs]==[(p.pair_id,p.status.value,p.discrepancy,p.raw_collision_score)for p in old.pairs]
    assert result.report.summary['status_counts']=={'ALIGNED':3,'PARTIAL':1,'CONFLICT':4,'UNRESOLVED':0,'NOT_COMPARABLE':1}
    assert result.codecs and result.higher_order and result.findings

def test_missing_source_requirement_yields_unresolved():
    job=stress();job['evidence']=[]
    r=VinculumPipeline().run(job)
    assert any(p.status.value=='UNRESOLVED' for p in r.report.pairs)
    assert all(p.raw_collision_score is None for p in r.report.pairs)

def test_context_unscored():
    j=stress();r=VinculumPipeline().run(j)
    j['scenario']['context']=None
    s=VinculumPipeline().run(j)
    assert r.report.input_fingerprint==s.report.input_fingerprint
    assert r.report.summary==s.report.summary

def test_cross_order_ontology_pipeline():
    r=VinculumPipeline().run(json.loads((EX/'coverage_pipeline.json').read_text()))
    assert r.report.pairs[0].status.value=='CONFLICT'
    assert (r.report.pairs[0].language_order,r.report.pairs[0].mathematics_order)==(1,4)
    assert r.report.pairs[0].discrepancy['signed_delta_left_unit']=='-40'
    assert any(n['canonical']=='urn:metric:coverage' for n in r.normalization)

def test_unknown_segment_not_disappearing():
    j=bakery();j['sources'][0]['data']="baker's dozen\nprobably a good order"
    r=VinculumPipeline().run(j)
    assert len(r.report.representations)==3
    assert r.source_summaries[0]['numeric_meanings_resolved']==1
    assert any(x['category']=='DEFINE_NUMERIC_MEANING' for x in r.findings)

def test_explicit_record_selection_is_reported():
    j=bakery();j['sources'][1]['format']='json';j['sources'][1]['data']=[{'quantity':12,'defense':.99,'use':'yes'},{'quantity':99,'defense':.5,'use':'no'}]
    j['sources'][1]['select']={'use':'yes'}
    r=VinculumPipeline().run(j)
    assert r.source_summaries[1]['loaded_records']==2 and r.source_summaries[1]['selected_records']==1
    assert len(r.report.pairs)==1

def test_pipeline_cap_and_unknown_keys():
    with pytest.raises(ValueError):VinculumPipeline(max_nodes=1).run(bakery())
    j=bakery();j['auto_execute']=True
    with pytest.raises(ValueError):VinculumPipeline().run(j)

def test_all_portable_exports(tmp_path):
    r=VinculumPipeline().run(stress());paths=r.export(tmp_path)
    assert all(p.exists() for p in paths)
    assert {'JOB.json','pipeline.json','report.json','report.html','REPORT.md','scenario.ttl','findings.ttl','OUTPUT_MANIFEST.json'}<={p.name for p in paths}
    import hashlib
    manifest=json.loads((tmp_path/'OUTPUT_MANIFEST.json').read_text())
    assert all(hashlib.sha256((tmp_path/k).read_bytes()).hexdigest()==v for k,v in manifest.items())
    assert VinculumPipeline().run_file(tmp_path/'JOB.json').report.summary==r.report.summary
    from rdflib import Graph
    g=Graph().parse(data=(tmp_path/'findings.ttl').read_text(),format='turtle')
    assert len(g)>20

def test_html_escaping():
    j=bakery();j['sources'][0]['data']='</pre><script>alert(1)</script>'
    text=pipeline_html(VinculumPipeline().run(j))
    assert '<script>' not in text and '&lt;script&gt;' in text
    assert 'Content-Security-Policy' in text

def test_cli_exit_codes(tmp_path):
    assert subprocess.run([sys.executable,'-m','vinculum.pipeline_cli','--version'],capture_output=True).returncode==0
    a=subprocess.run([sys.executable,'-m','vinculum.pipeline_cli','run',str(EX/'bakery_pipeline.json'),'--summary','--strict-exit'],capture_output=True,text=True)
    assert a.returncode==2 and 'CONFLICT' in a.stdout
    b=subprocess.run([sys.executable,'-m','vinculum.pipeline_cli','run',str(tmp_path/'missing')],capture_output=True)
    assert b.returncode==1

def test_higher_orders_product_is_opt_in():
    with pytest.raises(ValueError):HigherOrderPolicy('product')
    s=SupportProfile((SupportFactor('SL',.95,'example',source_id='a'),SupportFactor('CL',.8,'example',source_id='b')))
    assert assess_factors(s)['strength']==.8
    assert assess_factors(s,HigherOrderPolicy('product','illustrative coefficient product, not probability'))['strength']==pytest.approx(.76)

def test_dependency_group_not_repeatedly_multiplied():
    s=SupportProfile((SupportFactor('a',.8,'x',dependency_group='shared'),SupportFactor('b',.7,'x',dependency_group='shared')))
    assert assess_factors(s,HigherOrderPolicy('product','test'))['strength']==.7

def test_missing_higher_order_not_imputed():
    s=SupportProfile((SupportFactor('a',None,'unknown'),SupportFactor('b',.9,'known')))
    out=assess_factors(s);assert out['strength'] is None and out['factor_coverage']==.5
    assert assess_factors(SupportProfile())['strength'] is None

@pytest.mark.parametrize('age,expected',[(0,1),(50,.5),(100,0),(200,0)])
def test_freshness_diagnostic(age,expected):assert freshness_index(age_seconds=age,horizon_seconds=100)==expected

@pytest.mark.parametrize('age,horizon',[(-1,100),(0,0),(0,-1)])
def test_bad_freshness(age,horizon):
    with pytest.raises(ValueError):freshness_index(age_seconds=age,horizon_seconds=horizon)

def test_evidence_identity_and_closure():
    a=EvidenceSource.from_bytes('a',b'a',basis='test')
    b=EvidenceSource('b',None,'derived',parents=('a',))
    r=EvidenceRegistry([a,b]);assert r.closure(('b',))['roots']==['a']
    assert r.closure(('b',))['unhashed']==['b']
    with pytest.raises(ValueError):r.register(EvidenceSource.from_bytes('a',b'changed',basis='test'))
    assert r.closure(('missing',))['missing']==['missing']

def test_evidence_cycle_rejected():
    r=EvidenceRegistry([EvidenceSource('a',None,'test',parents=('b',)),EvidenceSource('b',None,'test',parents=('a',))])
    with pytest.raises(ValueError):r.validate()

def test_evidence_deep_dag():
    rr=[EvidenceSource(str(i),None,'test',parents=(str(i-1),)if i else ())for i in range(1100)]
    r=EvidenceRegistry(rr);assert r.closure(('1099',))['roots']==['0']

def test_skos_label_ambiguity_and_broader():
    ttl='''@prefix skos:<http://www.w3.org/2004/02/skos/core#>. <urn:a> skos:prefLabel "coverage"@en; skos:broader <urn:parent>. <urn:b> skos:altLabel "coverage"@en. <urn:c> skos:prefLabel "only"@en.'''
    r=OntologyRegistry.from_turtle(ttl)
    assert r.resolve('coverage',labels=True).canonical is None
    assert r.resolve('only',labels=True).canonical=='urn:c'
    assert r.resolve('urn:a').canonical=='urn:a'
    assert r.resolve('urn:a').canonical!='urn:parent'

def test_explicit_alias_cycle():
    with pytest.raises(ValueError):OntologyRegistry(entity_aliases={'a':'b','b':'a'})
    r=OntologyRegistry(entity_aliases={'old':'new'})
    assert r.resolve('old',kind='entity').canonical=='new'

def test_image_product_is_diagnostic_not_new_truth_probability():
    from vinculum.higher_order import pair_order_diagnostics
    from vinculum import PairGraph,Scope,measurement,SemanticRegistry,HingeOrderState
    scope=Scope('x','cookies','order','line',timeless=True)
    l=SemanticRegistry.default().representation("baker's dozen",id='l',entity='x',scope=scope,source_ids=('words',))
    m=measurement(id='m',entity='x',concept='item_count',value=12,unit='count',scope=scope,defense=.8,defense_basis='test',source_ids=('numbers',))
    g=PairGraph('g').add_node(l).add_node(m).add_pair('l','m',alignment_support=.9,alignment_basis='test')
    r=g.evaluate()
    diagnostic=pair_order_diagnostics(g,r,HigherOrderPolicy('product','diagram formula as non-probabilistic index','product'))
    item=diagnostic['l::m']
    assert item['diagnostic_supported_score']==pytest.approx(72)
    assert r.pairs[0].supported_collision_score==80
    assert r.pairs[0].raw_collision_score==100
    assert m.quantity==NumericRange.point(12)

def test_pipeline_turtle_numeric_input_with_explicit_predicate_selection():
    j=bakery()
    src=j['sources'][1]
    src['format']='ttl'
    src['data']='@prefix x:<urn:x:>. <order-001> x:quantity 12; x:note "not a count".'
    # same entity supplied by mapping defaults; source's arbitrary IRI is not guessed as the entity
    src['select']={'predicate':'urn:x:quantity'}
    src['mapping']['columns']={'value':'value'}
    src['mapping']['defaults']['defense']=.9
    r=VinculumPipeline().run(j)
    assert r.report.pairs[0].status.value=='CONFLICT'
    assert r.source_summaries[1]['loaded_records']==2
    assert r.source_summaries[1]['selected_records']==1


def test_registered_evidence_ancestry_prevents_independent_product():
    j=bakery()
    j['evidence']=[{'id':'root','sha256':None,'basis':'synthetic shared root'},
                  {'id':'left-derived','sha256':None,'basis':'derived','parents':['root']},
                  {'id':'right-derived','sha256':None,'basis':'derived','parents':['root']}]
    j['sources'][0]['mapping']['defaults']['source_ids']=['left-derived']
    j['sources'][1]['mapping']['defaults']['source_ids']=['right-derived']
    j['pairing'].update(alignment_support=.9,alignment_basis='synthetic coefficient')
    j['scenario']={'schema':'vinculum.crossorder.scenario/1','id':'SHARED',
                   'policy':{'support_aggregation':'product','product_basis':'illustrative engineering index'}}
    j['higher_order']={'joint_aggregation':'product','product_basis':'illustrative engineering index'}
    r=VinculumPipeline().run(j)
    p=r.report.pairs[0]
    assert p.status.value=='CONFLICT'
    assert p.support['aggregation']=='minimum'
    assert p.support['registered_evidence']['shared_roots']==['root']
    assert r.higher_order[p.pair_id]['dependency_adjusted'] is True
    assert r.higher_order[p.pair_id]['joint_aggregation']=='minimum'

def test_missing_registered_ancestry_withholds_support_not_raw():
    j=bakery();j['require_registered_sources']=False
    j['sources'][0]['mapping']['defaults']['source_ids']=['missing-parent']
    j['pairing'].update(alignment_support=.9,alignment_basis='synthetic coefficient')
    r=VinculumPipeline().run(j)
    p=r.report.pairs[0]
    assert p.status.value=='CONFLICT' and p.raw_collision_score==100
    assert p.supported_collision_score is None
