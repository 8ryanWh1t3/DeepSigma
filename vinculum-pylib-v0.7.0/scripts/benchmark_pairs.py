"""Local synthetic smoke benchmark, not an operational scalability guarantee."""
import json, time, platform
from vinculum import PairGraph, Representation, NumericRange, Side, PDProfile
from vinculum.demos import demonstration_scope, declared_support
n=1000
g=PairGraph('SYNTHETIC-BENCHMARK')
scope=demonstration_scope('benchmark')
begin=time.perf_counter()
for i in range(n):
    for side,value,order in [('L',i,i%5+1),('M',i+(i%5==0),(i//5)%5+1)]:
        g.add_node(Representation(f'{side}{i}',side,order,f'entity-{i}','count',NumericRange.point(value),'count',scope,
                                  pd=PDProfile(.1,.9,'benchmark fixture'),support=declared_support(.9)))
    g.add_pair(f'L{i}',f'M{i}',alignment_support=1,alignment_basis='benchmark fixture')
built=time.perf_counter()
r=g.evaluate()
end=time.perf_counter()
assert r.summary['status_counts']['CONFLICT']==200
print(json.dumps({'python':platform.python_version(),'representations':2*n,'selected_pairs':n,
 'build_seconds':built-begin,'evaluation_seconds':end-built,'conflicts':200,
 'description':'one local synthetic run; no production or multi-machine performance claim'},indent=2))
