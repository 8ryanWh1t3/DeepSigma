#!/usr/bin/env python3
"""Recreate the bundled, fully synthetic scenario and offline JS data wrapper."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AS_OF = '2026-09-20T12:00:00Z'
POLICY = {'id': 'DS-ZIPF-PILOT', 'version': 1, 'rarity_cap': 20,
          'min_relevance': 60, 'min_quality': 60, 'min_independent_support': 2,
          'required_evidence_types': ['manifest', 'independent_observation'],
          'max_evidence_age_days': 30, 'reviewer_roles': ['analyst'],
          'authority_roles': ['release_authority'], 'intended_use': 'verified_report_release'}


def claim(cid, concept, statement, relevance=75, consequence=65, quality=80, mandatory=False):
    evidence = [
        {'id': cid + '_ev_a', 'origin_id': cid + '_source_a', 'event_id': cid + '_ev_event_a',
         'kind': 'manifest', 'stance': 'supports', 'claim_version': 1,
         'observed_at': '2026-09-19T09:00:00Z', 'support_assessed': True},
        {'id': cid + '_ev_b', 'origin_id': cid + '_source_b', 'event_id': cid + '_ev_event_b',
         'kind': 'independent_observation', 'stance': 'supports', 'claim_version': 1,
         'observed_at': '2026-09-19T10:00:00Z', 'support_assessed': True}]
    return {'id': cid, 'version': 1, 'concept': concept, 'statement': statement,
            'relevance': relevance, 'consequence': consequence, 'quality': quality,
            'contradiction': False, 'mandatory': mandatory, 'required_evidence_types': [],
            'evidence': evidence,
            'review': {'reviewer_id': 'synthetic_analyst', 'role': 'analyst', 'claim_version': 1,
                       'policy_version': 1, 'decision': 'approved', 'expires_at': '2026-10-20T12:00:00Z'},
            'authority': {'authority_id': 'synthetic_release_officer', 'role': 'release_authority',
                          'claim_version': 1, 'policy_version': 1, 'intended_use': 'verified_report_release',
                          'expires_at': '2026-10-20T12:00:00Z', 'revoked': False}}


def make_demo():
    claims, reports = [], []
    routine_ids, distractor_ids = [], []
    for i in range(20):
        cid = f'routine_{i+1:02d}'
        routine_ids.append(cid)
        claims.append(claim(cid, 'Routine Status' if i % 2 else 'routine report',
                            f'Synthetic routine cargo-status summary {i+1:02d}. No exception reported.'))
        for j in range(50):
            reports.append({'id': f'{cid}_report_{j+1:03d}', 'claim_id': cid,
                            'origin_id': f'{cid}_observation_source_{j%3}', 'event_id': f'{cid}_event_{j+1:03d}'})

    valid = claim('valid_exception', 'cargo exception', 'Synthetic manifest discrepancy has assessed support from two declared independent origins.', 85, 80, 90)
    expired = claim('expired_approval', 'approval expiry', 'A synthetic approval has expired; review is required before verified release.', 85, 80, 85)
    expired['authority']['expires_at'] = '2026-09-19T12:00:00Z'
    conflicting = claim('contradiction', 'cargo conflict', 'Synthetic sources disagree about the cargo description.', 80, 85, 80)
    conflicting['contradiction'] = True
    conflicting['evidence'].append({'id': 'contradiction_ev_c', 'origin_id': 'contradiction_source_c',
                                    'event_id': 'contradiction_ev_event_c', 'kind': 'independent_observation',
                                    'stance': 'contradicts', 'claim_version': 1,
                                    'observed_at': '2026-09-19T11:00:00Z', 'support_assessed': False})
    gap = claim('missing_evidence', 'evidence gap', 'A synthetic cargo assertion lacks the required independent observation.', 80, 78, 70)
    gap['evidence'] = gap['evidence'][:1]
    cargo = claim('cargo_allegation', 'high consequence allegation', 'Illustrative AI cargo allegation: nuclear-program components are asserted without assessed support. This is not a reconstruction of an actual vessel.', 90, 98, 85)
    for ev in cargo['evidence']:
        ev['support_assessed'] = False
    # An apparently impressive rating must never replace evidence support.
    claims += [valid, expired, conflicting, gap, cargo]
    rare_ids = [c['id'] for c in [valid, expired, conflicting, gap, cargo]]
    for c in [valid, expired, conflicting, gap, cargo]:
        reports.append({'id': c['id'] + '_report', 'claim_id': c['id'],
                        'origin_id': c['id'] + '_source_a', 'event_id': c['id'] + '_reported_event'})
    # Fifty copies retain the same origin and event, so score and support do not increase.
    for i in range(50):
        reports.append({'id': f'cargo_copy_{i+1:02d}', 'claim_id': 'cargo_allegation',
                        'origin_id': 'cargo_allegation_source_a', 'event_id': 'cargo_allegation_reported_event'})
    for i in range(6):
        cid = f'distractor_{i+1:02d}'
        distractor_ids.append(cid)
        c = claim(cid, f'unusual topic {i+1}', f'Synthetic unusual but irrelevant formatting detail {i+1}.', 15, 10, 30)
        c['evidence'] = []
        c['review'] = None
        c['authority'] = None
        claims.append(c)
        reports.append({'id': cid + '_report', 'claim_id': cid,
                        'origin_id': cid + '_origin', 'event_id': cid + '_event'})
    mandatory_ids = []
    for i in range(2):
        cid = f'critical_{i+1:02d}'
        mandatory_ids.append(cid)
        claims.append(claim(cid, 'routine_status', f'Synthetic mandatory critical alert {i+1}; always shown outside the discretionary budget.', 90, 100, 90, True))
        for j in range(10):
            reports.append({'id': f'{cid}_report_{j}', 'claim_id': cid,
                            'origin_id': cid + '_origin', 'event_id': f'{cid}_event_{j}'})
    return {'schema_version': '1.0', 'as_of': AS_OF, 'review_budget': 5,
            'policy': POLICY, 'aliases': {'routine report': 'routine_status', 'routine status': 'routine_status'},
            'claims': claims, 'reports': reports,
            'labels': {'rare_relevant_claim_ids': rare_ids,
                       'irrelevant_claim_ids': routine_ids + distractor_ids,
                       'mandatory_claim_ids': mandatory_ids,
                       'gap_claim_ids': ['missing_evidence', 'cargo_allegation']}}


if __name__ == '__main__':
    payload = make_demo()
    (ROOT / 'data' / 'demo.json').write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    js = '// Generated by generate_demo.py. Synthetic scenario; no real operational data.\n'
    js += 'globalThis.DEEP_SIGMA_DEMO = ' + json.dumps(payload, separators=(',', ':')) + ';\n'
    (ROOT / 'web' / 'demo.js').write_text(js, encoding='utf-8')
    print(f'Generated {len(payload["claims"])} claims and {len(payload["reports"])} reports.')
