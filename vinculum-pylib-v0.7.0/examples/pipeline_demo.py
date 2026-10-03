"""Synthetic cross-order pipeline; run from the extracted source bundle."""
from pathlib import Path
from vinculum import VinculumPipeline

if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    result = VinculumPipeline().run_file(here / "cross_order_pipeline.json")
    result.export(here.parent / "my_pipeline_report")
    print(result.report.summary)
    for pair in result.report.pairs:
        print(pair.pair_id, pair.status.value, pair.discrepancy["signed_delta"],
              pair.raw_collision_score, pair.supported_collision_score)
