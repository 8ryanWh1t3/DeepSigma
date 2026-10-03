"""Batch-wide pairing decisions. Matching never uses numeric agreement as evidence."""
from __future__ import annotations
from dataclasses import dataclass, field, replace
from .core import CheckState, PairSpec, Side
from .hinge import HingeEvaluator
from .matrix import PairGraph
from .utils import fingerprint, identifier, primitive, unit_score


@dataclass(frozen=True)
class PairingPlan:
    mode: str = 'manual'
    policy_id: str | None = None
    basis: str | None = None
    choices: tuple[tuple[str,str], ...] = ()
    language_orders: tuple[int,...] = ()
    mathematics_orders: tuple[int,...] = ()
    max_candidates: int = 10000
    alignment_support: float | None = None
    alignment_basis: str | None = None

    def __post_init__(self):
        object.__setattr__(self,'alignment_support',unit_score(self.alignment_support,'pair alignment support'))
        if self.alignment_support is not None and not self.alignment_basis:
            raise ValueError('declared alignment support needs a separate attributed basis')
        if self.mode not in {'manual','guided','auto'}: raise ValueError('unknown pairing mode')
        if self.mode=='auto' and (not self.policy_id or not self.basis):
            raise ValueError('auto pairing requires an explicit named policy and basis')
        if type(self.max_candidates) is not int or self.max_candidates<1:
            raise ValueError('max_candidates must be positive')
        choices=tuple(tuple(x) for x in self.choices)
        if any(len(x)!=2 or any(not isinstance(y,str) or not y for y in x) for x in choices):
            raise ValueError('choices must contain two node IDs')
        if len(set(choices))!=len(choices): raise ValueError('duplicate pairing choice')
        object.__setattr__(self,'choices',choices)
        for key in ('language_orders','mathematics_orders'):
            v=tuple(getattr(self,key))
            if len(set(v))!=len(v) or any(type(x) is not int or x<1 for x in v):
                raise ValueError('order filters must be distinct positive integers')
            object.__setattr__(self,key,v)


@dataclass(frozen=True)
class PairCandidate:
    id: str
    left_id: str
    right_id: str
    state: str
    matched: tuple[str,...]
    pending: tuple[str,...]
    rejected: tuple[str,...]
    metadata_coverage: float
    ambiguous: bool
    basis: str = 'exact identity and context checks; not a calibrated probability; values excluded'


@dataclass(frozen=True)
class PairingAudit:
    mode: str
    policy_id: str | None
    candidates: tuple[PairCandidate,...]
    selected_pair_ids: tuple[str,...]
    deferred_candidate_ids: tuple[str,...]
    unmatched_node_ids: tuple[str,...]
    input_graph_fingerprint: str
    policy_fingerprint: str

    def to_dict(self): return primitive(self)


class PairPlanner:
    """Indexed exact joins, with ambiguity assessed on BOTH endpoints over the batch.

    Auto selection is limited to metadata-complete, globally unique, one-to-one
    candidate edges under an explicit application policy. Many-to-many requires
    explicit choices or existing manual PairSpecs. Selection does not claim truth.
    """
    def __init__(self,evaluator=None):
        self.evaluator=evaluator or HingeEvaluator()

    def apply(self,graph: PairGraph,plan: PairingPlan):
        before=graph.structure_fingerprint()
        existing={(p.left_id,p.right_id) for p in graph.pairs.values()}
        if plan.mode=='manual':
            for l,r in plan.choices:
                if l not in graph.nodes or r not in graph.nodes or l==r:raise ValueError('manual pairing references invalid endpoints')
            selected=[]
            for l,r in plan.choices:
                if (l,r) not in existing:
                    graph.add_pair(l,r,rationale=plan.basis or 'explicit manual input-runtime-output pairing',
                        alignment_support=plan.alignment_support,alignment_basis=plan.alignment_basis)
                    selected.append(graph.pairs[next(reversed(graph.pairs))].id)
            paired={i for p in graph.pairs.values() for i in (p.left_id,p.right_id)}
            return PairingAudit(plan.mode,plan.policy_id,(),tuple(selected),(),
                tuple(sorted(set(graph.nodes)-paired)),before,fingerprint(plan))
        index={}
        for node in graph.nodes.values():
            if node.side is Side.MATHEMATICS and (not plan.mathematics_orders or node.order in plan.mathematics_orders):
                if node.entity is not None and node.concept is not None:
                    index.setdefault((node.entity,node.concept),[]).append(node)
        raw=[]
        for left in sorted(graph.nodes.values(),key=lambda n:n.id):
            if left.side is not Side.LANGUAGE or (plan.language_orders and left.order not in plan.language_orders): continue
            for right in sorted(index.get((left.entity,left.concept),()),key=lambda n:n.id):
                if len(raw)>=plan.max_candidates: raise ValueError('candidate cap reached; narrow the pairing contract')
                spec=PairSpec('candidate:'+fingerprint([left.id,right.id])[:24],left.id,right.id,'candidate metadata assessment')
                # A hinge object can assess a selected candidate for comparison eligibility;
                # numeric result is discarded here and never used to select endpoints.
                result=self.evaluator.evaluate(replace(left,quantity=None),replace(right,quantity=None),spec)
                checks=[c for c in result.checks if c.required and c.name not in {'numeric_meaning'}
                        and c.state is not CheckState.NOT_APPLICABLE]
                matched=tuple(c.name for c in checks if c.state is CheckState.PASS)
                pending=tuple(c.name for c in checks if c.state is CheckState.UNKNOWN)
                failed=tuple(c.name for c in checks if c.state is CheckState.FAIL)
                raw.append((spec,matched,pending,failed))
        degrees={}
        for spec,matched,pending,failed in raw:
            if not failed:
                for key in (spec.left_id,spec.right_id):degrees[key]=degrees.get(key,0)+1
        candidates=[];selected=[];deferred=[];available=set();staged=[]
        for spec,matched,pending,failed in raw:
            edge=(spec.left_id,spec.right_id)
            ambiguous=not failed and (degrees[spec.left_id]>1 or degrees[spec.right_id]>1)
            state='NOT_COMPARABLE' if failed else ('UNRESOLVED' if pending else 'ELIGIBLE')
            candidate=PairCandidate(spec.id,*edge,state,matched,pending,failed,
                len(matched)/max(1,len(matched)+len(pending)+len(failed)),ambiguous)
            candidates.append(candidate)
            if not failed: available.add(edge)
            should_select=(plan.mode=='guided' and edge in plan.choices) or (
                plan.mode=='auto' and not failed and not pending and not ambiguous)
            if should_select and edge not in existing:
                if failed: raise ValueError('guided selection contains an incompatible candidate')
                staged.append(edge)
                existing.add(edge);selected.append('pair:'+fingerprint(edge)[:24])
            elif not failed and edge not in existing:deferred.append(spec.id)
        if plan.mode=='guided' and not set(plan.choices)<=available:
            raise ValueError('guided choice was not an eligible candidate; use an explicit manual pair for diagnostic mismatches')
        for edge in staged:
            graph.add_pair(*edge,rationale=plan.basis or 'explicitly selected guided candidate',
                id='pair:'+fingerprint(edge)[:24],alignment_support=plan.alignment_support,
                alignment_basis=plan.alignment_basis or 'explicit policy/selection; metadata completeness is not a match probability')
        paired={i for p in graph.pairs.values() for i in (p.left_id,p.right_id)}
        return PairingAudit(plan.mode,plan.policy_id,tuple(candidates),tuple(selected),tuple(deferred),
                           tuple(sorted(set(graph.nodes)-paired)),before,fingerprint(plan))
