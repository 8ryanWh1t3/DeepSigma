"""Explain findings and review needs; never issue command, permission or clinical advice."""
from .core import PairStatus


def review_findings(report, *, pairing=None, extraction=(), codec_reports=()):
    findings=[]
    actions={
        PairStatus.CONFLICT:('REVIEW_DISCREPANCY','Comparable representations have disjoint admissible values; inspect both sources.'),
        PairStatus.PARTIAL:('RESOLVE_OVERLAP','The observation allows both satisfying and nonsatisfying cases; obtain tighter evidence.'),
        PairStatus.UNRESOLVED:('SUPPLY_MISSING_CONTEXT','Supply missing context or an explicit numeric representation; do not invent a value.'),
        PairStatus.NOT_COMPARABLE:('REPAIR_PAIRING','Revise the pairing contract or provide a justified inference bridge; do not call this numerical agreement.'),
    }
    for p in report.pairs:
        if p.status in actions:
            category,reason=actions[p.status]
            findings.append({'id':'finding:'+p.pair_id,'pair_id':p.pair_id,'category':category,'reason':reason,
                             'status':p.status.value,'raw_collision_score':p.raw_collision_score,
                             'support':p.support['joint_strength'],'numeric_values_preserved':True,
                             'unknown_checks':[x.name for x in p.checks if x.required and x.state.value=='UNKNOWN']})
        if p.support['joint_strength'] is None:
            findings.append({'id':'support:'+p.pair_id,'pair_id':p.pair_id,'category':'ASSESS_SUPPORT',
                             'reason':'Support is incomplete. A missing support-weighted score is not zero risk.'})
    if pairing:
        for c in pairing.candidates:
            if c.id in pairing.deferred_candidate_ids:
                findings.append({'id':'pairing:'+c.id,'category':'SELECT_PAIR',
                    'candidate_id':c.id,'reason':'Multiple possible counterparts or incomplete context; explicit selection required.',
                    'ambiguous':c.ambiguous,'pending':list(c.pending)})
    for t in extraction:
        if t.status=='UNRESOLVED':
            findings.append({'id':'extraction:'+t.node_id,'category':'DEFINE_NUMERIC_MEANING','node_id':t.node_id,
                             'reason':'No unambiguous numeric meaning resolved; original material retained.',
                             'source_id':t.source_id,'locator':t.locator})
    for c in codec_reports:
        if c.status!='PRESERVED_WITHIN_DECLARED_SCOPE':
            findings.append({'id':'codec:'+c.transformation_id,'category':'REVIEW_TRANSFORMATION',
                             'reason':'Material meaning, scope, uncertainty or support was not shown to be preserved.',
                             'codec_status':c.status})
    return tuple(findings)
