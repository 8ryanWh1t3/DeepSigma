"""INPUT -> RUNTIME -> OUTPUT facade for the diagram-derived architecture.

A job is declarative data. It cannot load Python plugins, execute a model, fetch a
URL, establish authority, or command an operation. Configured auto-pairing selects
only unique, metadata-complete counterparts; unresolved candidates remain visible.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any
from .codec import CodecEvaluator
from .core import HingeCheck, CheckState, NumericRange
from .evidence import EvidenceRegistry, EvidenceSource, EvidenceHingeEvaluator
from .findings import review_findings
from .higher_order import HigherOrderPolicy, pair_order_diagnostics
from .hinge import HingeEvaluator
from .io import LoadLimits, load_config, load_source
from .lang import SemanticRegistry, NumericMeaningRule
from .ontology import OntologyRegistry
from .pairing import PairPlanner, PairingPlan
from .represent import FieldMapping, extract_records
from .serialization import SCHEMA, scenario_from_dict, _strict
from .utils import canonical_json, fingerprint, primitive
from .version import __version__

JOB_SCHEMA='vinculum.pipeline.job/1'


@dataclass(frozen=True)
class PipelineResult:
    scenario: Any
    report: Any
    codecs: tuple
    pairing: Any
    sources: tuple
    extraction: tuple
    normalization: tuple
    source_summaries: tuple
    stage_trace: tuple
    higher_order: dict
    findings: tuple
    job_fingerprint: str
    ontology_fingerprint: str
    warnings: tuple
    replay_job: dict

    def to_dict(self):
        return {'schema':'vinculum.pipeline.result/1','engine_version':__version__,
                'job_fingerprint':self.job_fingerprint,'ontology_fingerprint':self.ontology_fingerprint,
                'report':self.report.to_dict(),'codec_reports':[x.to_dict() for x in self.codecs],
                'pairing':self.pairing.to_dict(),'sources':primitive(self.sources),
                'extraction':primitive(self.extraction),'normalization':primitive(self.normalization),
                'source_summaries':primitive(self.source_summaries),'stage_trace':primitive(self.stage_trace),
                'higher_order':self.higher_order,'findings':primitive(self.findings),'warnings':list(self.warnings),
                'boundary':'representation evaluation, not truth, authority, safety certification, or automatic action'}

    def export(self,directory,*,formats=('json','html','csv','md','ttl')):
        from .exports import export_bundle
        return export_bundle(self,directory,formats=formats)


class VinculumPipeline:
    def __init__(self,*,limits=None,max_nodes=10000,max_pairs=10000):
        self.limits=limits or LoadLimits()
        if any(type(x) is not int or x<1 for x in (max_nodes,max_pairs)):
            raise ValueError('pipeline capacities must be positive integers')
        self.max_nodes,self.max_pairs=max_nodes,max_pairs

    def run_file(self,path):
        path=Path(path).resolve()
        return self.run(load_config(path),base_dir=path.parent,allow_files=True)

    def run(self,job,*,base_dir=None,allow_files=False):
        allowed={'schema','id','scenario','sources','lexicon','ontology','pairing','evidence',
                 'require_registered_sources','higher_order'}
        if not isinstance(job,dict) or set(job)-allowed or job.get('schema')!=JOB_SCHEMA:
            raise ValueError('invalid pipeline job schema or unknown fields')
        # Freeze input semantics through the same strict JSON boundary as saved jobs.
        from .utils import read_json
        job=read_json(canonical_json(job))
        sf=job.get('scenario',{'schema':SCHEMA,'id':job.get('id','VINCULUM')})
        scenario=scenario_from_dict(sf)
        graph=scenario.graph
        if len(graph.nodes)>self.max_nodes or len(graph.pairs)>self.max_pairs:
            raise ValueError('scenario exceeds pipeline node/pair capacity')
        evidence=EvidenceRegistry(EvidenceSource(**_strict(EvidenceSource,x)) for x in job.get('evidence',()))
        registry=SemanticRegistry.default()
        for d in job.get('lexicon',()):
            d=dict(_strict(NumericMeaningRule,d))
            d['quantity']=NumericRange(**_strict(NumericRange,d['quantity']))
            registry.register(NumericMeaningRule(**d))
        ont_cfg=job.get('ontology',{})
        if not isinstance(ont_cfg,dict) or set(ont_cfg)-{'turtle','language','entity_aliases','concept_aliases','resolve_labels'}:
            raise ValueError('invalid ontology configuration')
        kw={k:v for k,v in ont_cfg.items() if k not in {'turtle','resolve_labels'}}
        if 'turtle' in ont_cfg: ontology=OntologyRegistry.from_turtle(ont_cfg['turtle'],**kw)
        else:
            kw.pop('language',None);ontology=OntologyRegistry(**kw)
        if not isinstance(ont_cfg.get('resolve_labels',False),bool):raise ValueError('resolve_labels must be boolean')
        traces,normalization,summaries,warnings=[],[],[],[]
        for src in job.get('sources',()):
            if not isinstance(src,dict) or set(src)-{'id','format','data','path','mapping','sheet','sha256','select'}:
                raise ValueError('invalid source configuration')
            batch=load_source(source_id=src['id'],format=src['format'],data=src.get('data'),path=src.get('path'),
                base_dir=base_dir,allow_files=allow_files,sheet=src.get('sheet'),limits=self.limits,
                expected_sha256=src.get('sha256'))
            evidence.register(batch.source)
            src['sha256']=batch.source.sha256
            total=len(batch.rows)
            if 'select' in src:
                selector=src['select']
                if not isinstance(selector,dict):raise ValueError('source selection must be exact field/value map')
                keep=[i for i,row in enumerate(batch.rows) if all(row.get(k)==v for k,v in selector.items())]
                batch=replace(batch,rows=tuple(batch.rows[i] for i in keep),locators=tuple(batch.locators[i] for i in keep))
            mapping=FieldMapping(**_strict(FieldMapping,src['mapping']))
            nn,tt=extract_records(batch,mapping,registry=registry)
            if len(graph.nodes)+len(nn)>self.max_nodes:raise ValueError('extracted nodes exceed pipeline capacity')
            for n in nn: graph.add_node(n)
            traces.extend(tt);warnings.extend(batch.warnings)
            summaries.append({'source_id':batch.source.id,'format':src['format'],'loaded_records':total,
                'selected_records':len(batch.rows),'represented_records':len(nn),
                'numeric_meanings_resolved':sum(n.quantity is not None for n in nn),
                'extraction_kind':batch.extraction_kind,'warnings':list(batch.warnings),
                'coverage_boundary':'counts refer to explicitly selected parsed records, not all information in the original artifact'})
        # Normalize a fresh graph without mutating the source job or representations.
        from .matrix import PairGraph
        normalized=PairGraph(graph.id,graph.orders_l,graph.orders_m)
        normalized.context=graph.context
        for n in graph.nodes.values():
            new,rr=ontology.normalize(n,resolve_labels=ont_cfg.get('resolve_labels',False))
            normalized.add_node(new)
            for r in rr:
                if r.status!='UNCHANGED':normalization.append({'node_id':n.id,**primitive(r)})
        for p in graph.pairs.values():normalized.add_pair_spec(p)
        for group in graph.groups.values():normalized.add_group(group)
        graph=normalized
        scenario.graph=graph
        evidence.validate()  # cycles rejected even if not referenced by a selected pair
        required=job.get('require_registered_sources',False)
        if not isinstance(required,bool):raise ValueError('require_registered_sources must be boolean')
        evaluator=EvidenceHingeEvaluator.create(evidence,scenario.policy,scenario.units)
        def evidence_check(l,r,p):
            a,b=evidence.closure(l.source_ids),evidence.closure(r.source_ids)
            missing=sorted(set(a['missing']+b['missing']))
            shared=sorted(set(a['roots'])&set(b['roots']))
            reason=('missing sources: '+', '.join(missing)) if missing else 'source IDs registered; factual accuracy/authenticity not established'
            if shared:reason+='; shared evidence roots: '+', '.join(shared)
            state=CheckState.PASS if a['complete'] and b['complete'] else CheckState.UNKNOWN
            return HingeCheck('registered_evidence',3,state,reason,required)
        evaluator.register_check('registered_evidence',evidence_check)
        plan=PairingPlan(**_strict(PairingPlan,job.get('pairing',{})))
        pairing=PairPlanner(evaluator).apply(graph,plan)
        if len(graph.pairs)>self.max_pairs:raise ValueError('selected pairs exceed pipeline capacity')
        report=graph.evaluate(evaluator)
        codecs=tuple(CodecEvaluator(scenario.units).evaluate(graph,report,t) for t in scenario.transformations)
        higher=pair_order_diagnostics(graph,report,HigherOrderPolicy(**_strict(HigherOrderPolicy,job.get('higher_order',{}))))
        findings=review_findings(report,pairing=pairing,extraction=traces,codec_reports=codecs)
        # Input identity includes extraction plan, policy, ontology and exact source hashes.
        job_fp=fingerprint({'job':job,'source_hashes':[(s.id,s.sha256) for s in evidence.sources.values()],
                            'ontology':ontology.fingerprint(),'version':__version__})
        stages=(
            {'stage':'INPUT','sources':len(summaries),'parsed_records':sum(s['loaded_records'] for s in summaries)},
            {'stage':'INGEST','evidence_sources':len(evidence.sources),'warnings':len(warnings)},
            {'stage':'REPRESENT','nodes':len(graph.nodes),'unresolved_numeric_meanings':sum(n.quantity is None for n in graph.nodes.values())},
            {'stage':'PAIR','candidates':len(pairing.candidates),'selected_pairs':len(graph.pairs),'deferred':len(pairing.deferred_candidate_ids)},
            {'stage':'EVALUATE','evaluated_pairs':len(report.pairs),'status':report.summary['status']},
            {'stage':'AGGREGATE','groups':len(report.groups),'codec_audits':len(codecs)},
            {'stage':'OUTPUT','review_findings':len(findings),'automatic_actions':0})
        return PipelineResult(scenario,report,codecs,pairing,tuple(evidence.sources.values()),tuple(traces),
            tuple(normalization),tuple(summaries),stages,higher,findings,job_fp,ontology.fingerprint(),tuple(warnings),job)
