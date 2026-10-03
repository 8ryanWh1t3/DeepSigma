"""Run from an installed v0.6 wheel: python examples/cross_order_demo.py"""
from pathlib import Path
from vinculum.demos import codec_stress
from vinculum.codec import CodecEvaluator
from vinculum.report import write_csv, write_html, write_json
from vinculum.rdf import to_turtle
from vinculum.serialization import save_scenario

out = Path('vinculum_cross_order_output')
out.mkdir(exist_ok=True)
scenario = codec_stress()
report = scenario.evaluate()
codec = CodecEvaluator().evaluate(scenario.graph, report, scenario.transformations[0])
write_json(report, out / 'report.json')
write_json(codec, out / 'codec.json')
write_html(report, out / 'report.html', context=scenario.graph.context, codec_reports=(codec,))
write_csv(report, out / 'excel_csv')
save_scenario(scenario, out / 'scenario.json')
(out / 'scenario.ttl').write_text(to_turtle(scenario), encoding='utf-8')
for pair in report.pairs:
    print(f'{pair.pair_id:24} {pair.status.value:16} delta={pair.discrepancy.get("signed_delta")}')
print('Codec:', codec.status)
print('Reports:', out.resolve())
