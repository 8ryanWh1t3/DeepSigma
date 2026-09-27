from pathlib import Path
import json, sys
from rdflib import Graph, RDF, OWL, RDFS, Namespace, URIRef
ROOT=Path(__file__).resolve().parents[1]
DOO=Namespace('https://decisionoperations.org/ontology/core#')
results={'parse':{},'checks':{},'examples':{}}
failed=False
for p in sorted(ROOT.rglob('*.ttl')):
    try:
        g=Graph(); g.parse(p, format='turtle'); results['parse'][str(p.relative_to(ROOT))]={'status':'PASS','triples':len(g)}
    except Exception as e:
        results['parse'][str(p.relative_to(ROOT))]={'status':'FAIL','error':str(e)}; failed=True

# Universal isolation: only Coherence Ops profile and migration may mention Deep Sigma/Coherence Ops namespaces.
for p in sorted(ROOT.glob('doo-*.ttl')):
    if p.name=='doo-coherenceops.ttl': continue
    txt=p.read_text(encoding='utf-8')
    bad=('deepsigma.io' in txt or 'coherenceops.io' in txt)
    results['checks'][f'neutral:{p.name}']='FAIL' if bad else 'PASS'
    failed |= bad

# Required public terms
G=Graph()
for p in ROOT.glob('doo-*.ttl'):
    if p.name.startswith('doo-shapes') or p.name=='doo-coherenceops.ttl': continue
    G.parse(p, format='turtle')
required=[DOO.DecisionEpisode,DOO.Decision,DOO.DecisionProblem,DOO.DecisionOption,DOO.Actor,DOO.DecisionRationale,DOO.Claim,DOO.Evidence,DOO.Assumption,DOO.Authority,DOO.Review,DOO.Patch,DOO.DecisionPacket]
for term in required:
    ok=(term,RDF.type,OWL.Class) in G
    results['checks'][f'term:{term.split("#")[-1]}']='PASS' if ok else 'FAIL'; failed |= not ok

# Direct profile acceptance checks for shipped examples.
def objects(g,s,p): return list(g.objects(s,p))
def has(g,s,p): return any(g.objects(s,p))
def typed(g,c): return list(g.subjects(RDF.type,c))

def core_check(path):
    g=Graph(); g.parse(path, format='turtle'); errs=[]
    eps=typed(g,DOO.DecisionEpisode); decs=typed(g,DOO.Decision)
    if not eps: errs.append('no DecisionEpisode')
    for e in eps:
        for p,n in [(DOO.identifier,'identifier'),(DOO.framesProblem,'framesProblem'),(DOO.resultsInDecision,'resultsInDecision'),(DOO.hasParticipant,'hasParticipant')]:
            if not has(g,e,p): errs.append(f'{e} missing {n}')
    for d in decs:
        for p,n in [(DOO.identifier,'identifier'),(DOO.madeBy,'madeBy'),(DOO.decisionTime,'decisionTime')]:
            if not has(g,d,p): errs.append(f'{d} missing {n}')
    return errs

def governed_check(path):
    g=Graph(); g.parse(path, format='turtle'); errs=core_check(path)
    for d in typed(g,DOO.Decision):
        if not has(g,d,DOO.authorizedBy): errs.append(f'{d} missing authorizedBy')
        if not has(g,d,DOO.hasDecisionState): errs.append(f'{d} missing hasDecisionState')
    for c in typed(g,DOO.Claim):
        for v in g.objects(c,DOO.confidence):
            try:
                x=float(v)
                if x<0 or x>1: errs.append(f'{c} confidence out of range')
            except: errs.append(f'{c} confidence not numeric')
    return errs
for rel,fn in [('examples/minimal-decision.ttl',core_check),('examples/governed-decision.ttl',governed_check)]:
    errs=fn(ROOT/rel); results['examples'][rel]={'status':'PASS' if not errs else 'FAIL','errors':errs}; failed |= bool(errs)

out=ROOT/'validation.json'; out.write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps(results,indent=2))
sys.exit(1 if failed else 0)
