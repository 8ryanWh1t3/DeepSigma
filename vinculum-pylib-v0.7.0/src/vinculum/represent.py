"""Explicit source-field maps -> typed representations, with extraction trace."""
from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Any
from .core import NumericRange, PDProfile, Representation, Scope, Side, SupportFactor, SupportProfile, TimeWindow
from .io import SourceBatch
from .lang import SemanticRegistry
from .serialization import representation_from_dict, _strict
from .utils import number, primitive


@dataclass(frozen=True)
class ExtractionTrace:
    node_id: str
    source_id: str
    locator: str
    status: str
    mapping: dict[str,Any]
    warnings: tuple[str,...]
    resolution: dict[str,Any] | None = None


@dataclass(frozen=True)
class FieldMapping:
    side: str
    order: int = 1
    columns: dict[str,str] | None = None
    defaults: dict[str,Any] | None = None

    def __post_init__(self):
        Side(self.side)
        if type(self.order) is not int or self.order<1: raise ValueError('mapping order must be positive')
        cols=dict(self.columns or {})
        valid={'id','entity','concept','text','unit','value','lower','upper','order','defense','method',
               'pd.probabilistic','pd.deterministic','scope.scope_id','scope.population',
               'scope.denominator','scope.granularity','scope.location','scope.definition_version',
               'scope.window.start','scope.window.end'}
        if set(cols)-valid: raise ValueError('unknown mapped fields: '+str(sorted(set(cols)-valid)))
        if any(not isinstance(v,str) or not v for v in cols.values()): raise ValueError('column paths must be strings')
        defaults=dict(self.defaults or {})
        allowed={'id','entity','concept','text','unit','value','lower','upper','order','defense','defense_basis',
                 'method','pd','scope','support','depends_on','material','source_ids'}
        if set(defaults)-allowed: raise ValueError('unknown mapping defaults')
        object.__setattr__(self,'columns',cols);object.__setattr__(self,'defaults',defaults)


def _lookup(row,path):
    if path in row: return row[path]
    value=row
    for key in path.split('.'):
        if not isinstance(value,dict) or key not in value: return None
        value=value[key]
    return value


def _put(target,path,value):
    parts=path.split('.')
    for key in parts[:-1]:
        if key not in target: target[key]={}
        if not isinstance(target[key],dict): raise ValueError('incompatible nested mapping')
        target=target[key]
    target[parts[-1]]=value


def extract_records(batch: SourceBatch, mapping: FieldMapping, *, registry=None):
    """No learned entity or reference resolution. Unknown phrases remain nodes.

    Source line values and qualifications are preserved in trace. An explicit L
    numeric mapping is allowed, but is labeled caller-supplied; known lexical
    expectations may not be silently replaced by a contradictory supplied value.
    """
    registry=registry or SemanticRegistry.default()
    nodes,traces=[],[]
    for i,(row,locator) in enumerate(zip(batch.rows,batch.locators),1):
        import copy
        d=copy.deepcopy(mapping.defaults)
        if not mapping.columns and 'text' in row: d['text']=row['text']
        missing=[]
        for field,path in mapping.columns.items():
            v=_lookup(row,path)
            if v is None or v=='':
                missing.append(f'missing mapped field {field} ({path})')
                # A missing field does not silently inherit an unrelated default value.
                _put(d,field,None)
            else: _put(d,field,v)
        rid=d.pop('id',None) or f'{batch.source.id}:{i}'
        order=d.pop('order',mapping.order)
        if order is None: order=mapping.order
        q_order=number(order)
        if q_order.denominator!=1 or q_order<1: raise ValueError('record order must be positive integer')
        order=int(q_order)
        scope=dict(d.pop('scope',{}))
        if scope.get('window') is not None:
            if any(scope['window'].get(k) is None for k in ('start','end')):
                scope['window']=None;missing.append('incomplete time window retained as unknown')
            else: scope['window']=TimeWindow(**_strict(TimeWindow,scope['window']))
        scope=Scope(**_strict(Scope,scope))
        pd=PDProfile(**_strict(PDProfile,d.pop('pd',{})))
        text=d.pop('text','') or ''
        if not isinstance(text,str): raise ValueError('mapped text must be a string')
        value,lo,hi=d.pop('value',None),d.pop('lower',None),d.pop('upper',None)
        if value is not None and (lo is not None or hi is not None):
            raise ValueError('numeric record cannot contain both point and interval columns')
        incomplete_interval = any(k in mapping.columns and (lo if k=='lower' else hi) is None for k in ('lower','upper'))
        quantity=NumericRange.point(value) if value is not None else (
            NumericRange(lo,hi) if not incomplete_interval and (lo is not None or hi is not None) else None)
        if incomplete_interval: missing.append('mapped interval endpoint absent; interval not widened silently')
        defense=d.pop('defense',None)
        basis=d.pop('defense_basis','caller-supplied support coefficient; no calibration inferred')
        factors=[]
        support=d.pop('support',{})
        if support:
            support=_strict(SupportProfile,support)
            factors=[SupportFactor(**_strict(SupportFactor,x)) for x in support.get('factors',())]
        entity,concept,unit=d.pop('entity',None),d.pop('concept',None),d.pop('unit',None)
        resolution=None
        if Side(mapping.side) is Side.LANGUAGE:
            r=registry.resolve(text,concept=concept)
            resolution=primitive(r)
            if r.status=='RESOLVED':
                if quantity is not None and quantity!=r.quantity:
                    raise ValueError(f'{rid}: supplied language value contradicts resolved phrase')
                if unit is not None and unit!=r.unit:
                    raise ValueError(f'{rid}: supplied language unit differs from resolved unit; normalize explicitly')
                quantity,concept,unit=r.quantity,r.concept,r.unit
                factors.append(SupportFactor('semantic_mapping',r.semantic_strength,r.basis,
                                             source_id=r.rule_id))
            elif quantity is not None:
                factors.append(SupportFactor('semantic_mapping',defense,
                    'explicit caller mapping from text to number; not inferred by the parser'))
            else:
                factors.append(SupportFactor('semantic_mapping',None,r.basis))
                missing.append('no unambiguous numeric meaning for this text')
        else:
            factors.append(SupportFactor('numeric_defense',defense,basis,source_id=batch.source.id))
        sources=d.pop('source_ids',())
        if isinstance(sources,str): raise ValueError('source_ids must be an array')
        node=Representation(rid,Side(mapping.side),order,entity,concept,quantity,unit,scope,text,pd,
            SupportProfile(tuple(factors)),tuple(dict.fromkeys((*sources,batch.source.id))),
            tuple(d.pop('depends_on',())),method=d.pop('method',None),material=d.pop('material',True),
            definition_id=resolution.get('rule_id') if resolution else None)
        if d: raise ValueError('unconsumed mapping fields: '+str(sorted(d)))
        nodes.append(node)
        traces.append(ExtractionTrace(node.id,batch.source.id,locator,
            'RESOLVED' if node.quantity is not None else 'UNRESOLVED',primitive(mapping),tuple(missing),resolution))
    return tuple(nodes),tuple(traces)
