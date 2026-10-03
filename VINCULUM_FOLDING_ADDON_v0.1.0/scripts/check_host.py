"""Verify against an installed host and an existing job; never disguise a missing host as PASS.

Usage: python scripts/check_host.py /path/to/existing_job.json
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("job")
    args = parser.parse_args(argv)
    try:
        import vinculum
        from vinculum import VinculumPipeline
        import vinculum_folding
        from vinculum_folding import from_pipeline, host_pair_results
        from vinculum_folding.model import canonical
        run = VinculumPipeline().run_file(args.job)
        before = canonical({"scenario": run.scenario.to_dict(), "result": run.to_dict()})
        episode = from_pipeline(run, episode_id="EP-HOST-INTEGRATION-CHECK",
            mission_id="HOST-INTEGRATION-CHECK", title="Explicit host compatibility check",
            recorded_at=datetime.now(timezone.utc).isoformat())
        after = canonical({"scenario": run.scenario.to_dict(), "result": run.to_dict()})
        if before != after:
            raise RuntimeError("host result changed during capture")
        copied = host_pair_results(episode)
        statuses = {p.pair_id: p.status.value for p in run.report.pairs}
        if statuses != {pid: result["status"] for pid, result in copied.items()}:
            raise RuntimeError("host pair results changed in projection")
        print(json.dumps({"status": "PASS", "host_module": vinculum.__file__,
            "addon_module": vinculum_folding.__file__, "selected_pairs": len(statuses),
            "host_unchanged": True, "episode_digest": episode.digest,
            "scope": "This job and installed host build only; not the complete host regression suite."}, indent=2))
        return 0
    except (ImportError, OSError, ValueError, RuntimeError, AttributeError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "NOT_PASSED", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
