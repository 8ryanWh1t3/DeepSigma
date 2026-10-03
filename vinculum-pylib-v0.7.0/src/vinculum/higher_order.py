"""Higher-order factor diagnostics from the graphics; separate from numeric discrepancy.

The product is an explicitly selected engineering index, never a probability claim.
Repeated evidence groups are bottlenecked before product. Unknown stays unknown.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
from .core import SupportProfile
from .utils import primitive, number


@dataclass(frozen=True)
class HigherOrderPolicy:
    aggregation: str = 'minimum'
    product_basis: str | None = None
    joint_aggregation: str = 'minimum'

    def __post_init__(self):
        if self.aggregation not in {'minimum','product'}:raise ValueError('unknown higher-order aggregation')
        if self.joint_aggregation not in {'minimum','product'}:raise ValueError('unknown joint higher-order aggregation')
        if (self.aggregation=='product' or self.joint_aggregation=='product') and not self.product_basis:
            raise ValueError('multiplicative higher orders require an explicit engineering basis')


def assess_factors(profile: SupportProfile,policy: HigherOrderPolicy | None=None):
    policy=policy or HigherOrderPolicy()
    groups={}; missing=[]
    for f in profile.factors:
        key=f.dependency_group or f.source_id or 'factor:'+f.name
        groups.setdefault(key,[]).append(f)
        if f.value is None:missing.append(f.name)
    group_values={k:(None if any(f.value is None for f in fs) else min(f.value for f in fs))
                  for k,fs in groups.items()}
    vals=list(group_values.values())
    if not vals or any(x is None for x in vals):strength=None
    elif policy.aggregation=='minimum':strength=min(vals)
    else:strength=math.prod(vals)
    return {'strength':strength,'aggregation':policy.aggregation,'basis':policy.product_basis,
            'groups':group_values,'missing':missing,'factors':primitive(profile.factors),
            'factor_coverage':(len(profile.factors)-len(missing))/len(profile.factors) if profile.factors else 0.0,
            'interpretation':'support index; not probability, truth, safety, or a rescaled measurement'}


def pair_order_diagnostics(graph,report,policy=None):
    policy=policy or HigherOrderPolicy()
    out={}
    for p in report.pairs:
        left,right=graph.nodes[p.left_id],graph.nodes[p.right_id]
        spec=graph.pairs[p.pair_id]
        lp=assess_factors(left.support,policy);rp=assess_factors(right.support,policy)
        hp=[assess_factors(h.support,policy) for h in spec.hinge_states]
        strengths=[lp['strength'],rp['strength'],spec.alignment_support]+[h['strength'] for h in hp]
        # The displayed product formula can be selected as a declared index.
        # Known cross-endpoint dependence forces bottleneck, never independent votes.
        joint=None if any(x is None for x in strengths) or p.support.get('missing_dependencies') else min(strengths)
        dependency_adjusted=bool(p.dependency_warnings)
        if joint is not None and policy.joint_aggregation=='product' and not dependency_adjusted:
            joint=math.prod(strengths)
        out[p.pair_id]={'left':lp,'right':rp,'hinge':hp,'alignment_support':spec.alignment_support,
            'joint_strength':joint,'joint_aggregation':('minimum' if dependency_adjusted else policy.joint_aggregation),
            'dependency_adjusted':dependency_adjusted,'product_basis':policy.product_basis,'raw_collision_score':p.raw_collision_score,
            'diagnostic_supported_score':None if joint is None or p.raw_collision_score is None else joint*p.raw_collision_score,
            'raw_value_unchanged':True,'orders_are_not_certainty_rankings':True,
            'dependency_warnings':list(p.dependency_warnings)}
    return out


def freshness_index(*,age_seconds,horizon_seconds):
    """Explicit linear age index for diagnostics; not a calibrated probability.

    This does not replace HingePolicy's hard stale/unknown check.
    """
    age,horizon=number(age_seconds),number(horizon_seconds)
    if age<0 or horizon<=0:raise ValueError('age must be nonnegative and horizon positive')
    return max(0.0,1.0-float(age/horizon))
