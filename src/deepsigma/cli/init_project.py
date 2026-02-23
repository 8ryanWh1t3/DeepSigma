"""deepsigma init — scaffold a 5-minute starter project."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

_SAMPLE_EPISODES = [
    {
        "episodeId": "ep-demo-001",
        "decisionType": "deploy",
        "sealedAt": "2026-02-12T10:00:00Z",
        "dteRef": {
            "deadlineIso": "2026-02-12T10:05:00Z",
            "ttlSeconds": 300,
            "freshnessGate": "pass",
        },
        "actions": [
            {
                "type": "deploy_model",
                "blastRadiusTier": "medium",
                "idempotencyKey": "idem-deploy-001",
                "rollbackPlan": "revert to v2.3",
                "authorization": {"mode": "human_approved"},
                "targetRefs": ["model-svc/v2.4"],
            }
        ],
        "verification": {"result": "pass", "verifierId": "smoke-test-v1"},
        "policy": {
            "packId": "policy-pack-prod-v3",
            "packHash": "sha256:abc123def456",
            "evaluatedAt": "2026-02-12T09:59:50Z",
            "result": "allow",
        },
        "outcome": {"code": "success", "detail": "model v2.4 deployed"},
        "degrade": {"step": "none"},
        "context": {"evidenceRefs": ["evidence:deploy-checklist-001"]},
        "seal": {"sealHash": "sha256:seal001aaa", "sealedAt": "2026-02-12T10:00:00Z"},
    },
    {
        "episodeId": "ep-demo-002",
        "decisionType": "scale",
        "sealedAt": "2026-02-12T10:15:00Z",
        "dteRef": {
            "deadlineIso": "2026-02-12T10:20:00Z",
            "ttlSeconds": 300,
            "freshnessGate": "pass",
        },
        "actions": [
            {
                "type": "scale_replicas",
                "blastRadiusTier": "low",
                "idempotencyKey": "idem-scale-002",
                "rollbackPlan": "scale back to 3 replicas",
                "authorization": {"mode": "auto"},
                "targetRefs": ["inference-svc"],
            }
        ],
        "verification": {"result": "pass", "verifierId": "replica-health-check"},
        "policy": {
            "packId": "policy-pack-prod-v3",
            "packHash": "sha256:abc123def456",
            "evaluatedAt": "2026-02-12T10:14:55Z",
            "result": "allow",
        },
        "outcome": {"code": "success", "detail": "scaled to 5 replicas"},
        "degrade": {"step": "none"},
        "context": {"evidenceRefs": ["evidence:load-metrics-002"]},
        "seal": {"sealHash": "sha256:seal002bbb", "sealedAt": "2026-02-12T10:15:00Z"},
    },
    {
        "episodeId": "ep-demo-003",
        "decisionType": "rollback",
        "sealedAt": "2026-02-12T10:30:00Z",
        "dteRef": {
            "deadlineIso": "2026-02-12T10:32:00Z",
            "ttlSeconds": 120,
            "freshnessGate": "pass",
        },
        "actions": [
            {
                "type": "rollback_model",
                "blastRadiusTier": "high",
                "idempotencyKey": "idem-rollback-003",
                "rollbackPlan": "no further rollback available",
                "authorization": {"mode": "human_approved"},
                "targetRefs": ["model-svc/v2.4"],
            }
        ],
        "verification": {"result": "fail", "verifierId": "smoke-test-v1"},
        "policy": {
            "packId": "policy-pack-prod-v3",
            "packHash": "sha256:abc123def456",
            "evaluatedAt": "2026-02-12T10:29:50Z",
            "result": "allow",
        },
        "outcome": {"code": "partial", "detail": "rollback executed but verification failed"},
        "degrade": {"step": "safe_subset"},
        "context": {"evidenceRefs": ["evidence:incident-003", "evidence:deploy-checklist-001"]},
        "seal": {"sealHash": "sha256:seal003ccc", "sealedAt": "2026-02-12T10:30:00Z"},
    },
]

_SAMPLE_DRIFT = [
    {
        "driftId": "drift-001",
        "episodeId": "ep-demo-003",
        "driftType": "verify",
        "severity": "red",
        "detectedAt": "2026-02-12T10:30:05Z",
        "expectedBehaviour": "verification pass after rollback",
        "actualBehaviour": "smoke-test-v1 returned fail",
        "recommendedPatchType": "escalate_to_human",
    }
]

_SAMPLE_CLAIMS = [
    {
        "claim_id": "claim-001",
        "episode_id": "ep-demo-001",
        "text": "Deployment decision prioritized service continuity.",
        "confidence": 0.82,
        "evidence_ref": "evidence:deploy-checklist-001",
    },
    {
        "claim_id": "claim-002",
        "episode_id": "ep-demo-003",
        "text": "Rollback verification failure is a drift signal requiring patch.",
        "confidence": 0.94,
        "evidence_ref": "evidence:incident-003",
    },
]

_SAMPLE_SUMMARY = {
    "baseline_score": 84.0,
    "baseline_grade": "B",
    "patched_score": 92.0,
    "patched_grade": "A",
    "drift_events": 1,
    "patch_applied": True,
    "steps_completed": [
        "connect",
        "normalize",
        "extract",
        "seal",
        "drift",
        "patch",
        "recall",
    ],
    "elapsed_ms": 1430,
    "canonical_records": 3,
    "iris_queries": {
        "WHY": "RESOLVED",
        "WHAT_CHANGED": "RESOLVED",
        "STATUS": "RESOLVED",
    },
}


def _slug(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
    if not s:
        raise ValueError("Project name must contain letters or numbers")
    return s


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("init", help="Scaffold a 5-minute starter lattice project")
    p.add_argument("name", help="Project directory name")
    p.add_argument(
        "--out-dir",
        default=".",
        help="Base output directory where the project folder will be created",
    )
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    project_name = _slug(args.name)
    root = Path(args.out_dir).resolve() / project_name

    root.mkdir(parents=True, exist_ok=True)

    _write_text(
        root / "README.md",
        f"""# {project_name}

Starter project generated by `deepsigma init`.

## Quick run

```bash
make demo
```

This generates:
- `out/score.json` (coherence score)
- `out/iris_why.json` (WHY retrieval query)
- `out/iris_drift.json` (WHAT_DRIFTED query)
- `out/trust_scorecard.json` (trust KPI snapshot)
""",
    )

    _write_text(
        root / "Makefile",
        """PYTHON ?= python

.PHONY: demo score iris trust

demo: score iris trust
\t@echo \"Quickstart complete. See out/*.json artifacts.\"

score:
\tmkdir -p out
\t$(PYTHON) -m coherence_ops score ./data/sample_episodes.json --json > out/score.json

iris:
\tmkdir -p out
\t$(PYTHON) -m coherence_ops iris query ./data/sample_episodes.json --type WHY --target ep-demo-003 --json > out/iris_why.json
\t$(PYTHON) -m coherence_ops iris query ./data/sample_episodes.json --type WHAT_DRIFTED --json > out/iris_drift.json

trust:
\tmkdir -p out
\t$(PYTHON) -m tools.trust_scorecard --input ./data/golden_path_sample --output ./out/trust_scorecard.json
""",
    )

    _write_text(
        root / "scenarios" / "drift_scenario.md",
        """# Drift Scenario

`ep-demo-003` shows a rollback with failed verification.

- Drift type: `verify`
- Severity: `red`
- Expected: verification should pass after rollback
- Actual: verifier stayed in fail state
- Patch path: escalate to human + adjust guardrails
""",
    )

    _write_text(
        root / "queries" / "iris_queries.md",
        """# IRIS Queries

```bash
python -m coherence_ops iris query ./data/sample_episodes.json --type WHY --target ep-demo-003 --json
python -m coherence_ops iris query ./data/sample_episodes.json --type WHAT_DRIFTED --json
```
""",
    )

    _write_json(root / "data" / "sample_episodes.json", _SAMPLE_EPISODES)
    _write_json(root / "data" / "sample_drift.json", _SAMPLE_DRIFT)
    _write_json(root / "data" / "sample_claims.json", _SAMPLE_CLAIMS)
    _write_json(root / "data" / "golden_path_sample" / "summary.json", _SAMPLE_SUMMARY)
    _write_json(root / "data" / "golden_path_sample" / "step_2_normalize" / "validation.json", {"errors": []})

    print(f"Initialized DeepSigma project: {root}")
    print("Next: cd into the project and run `make demo`")
    return 0
