#!/usr/bin/env python3
"""Model Exchange Engine demo — run APEX + Mock adapters and compare.

Usage:
    python src/core/examples/model_exchange_demo.py
    python -m core.cli mee demo
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.model_exchange import ModelExchangeEngine  # noqa: E402
from core.model_exchange.adapters import (  # noqa: E402
    ApexAdapter,
    ClaudeAdapter,
    GGUFAdapter,
    MockAdapter,
    OpenAIAdapter,
)


def run_demo() -> None:
    """Run the Model Exchange Engine demo."""
    print("=" * 66)
    print("  MODEL EXCHANGE ENGINE — Demo")
    print("  Models produce exhaust. Deep Sigma produces judgment.")
    print("=" * 66)
    print()

    # 1. Create engine and register adapters
    engine = ModelExchangeEngine()
    engine.registry.register("apex", ApexAdapter())
    engine.registry.register("mock", MockAdapter())
    engine.registry.register("openai", OpenAIAdapter())
    engine.registry.register("claude", ClaudeAdapter())
    engine.registry.register("gguf", GGUFAdapter())

    print(f"Registered adapters: {engine.registry.list_adapters()}")
    print()

    # 2. Build a sample reasoning packet
    packet = {
        "request_id": "REQ-DEMO-001",
        "topic": "SLA Compliance Review",
        "question": "Is the current deployment within SLA targets for latency and error rate?",
        "evidence": [
            "EVIDENCE-LATENCY-P99-2026-Q1",
            "EVIDENCE-ERROR-RATE-2026-Q1",
            "EVIDENCE-UPTIME-SLA-2026-Q1",
        ],
        "ttl": 3600,
        "context": {
            "environment": "production",
            "service": "decision-engine",
        },
    }

    # 3. Run all five adapters
    adapter_names = ["apex", "mock", "openai", "claude", "gguf"]
    print(f"Running adapters: {adapter_names}")
    print("-" * 66)

    evaluation = engine.run(packet, adapter_names)

    # 4. Print per-adapter summaries
    for result in evaluation.adapter_results:
        print(f"\n  Adapter: {result.adapter_name}")
        print(f"    Model:      {result.model_meta.model}")
        print(f"    Provider:   {result.model_meta.provider}")
        print(f"    Confidence: {result.confidence:.2f}")
        print(f"    Claims:     {len(result.claims)}")
        for claim in result.claims:
            print(f"      [{claim.claim_type}] {claim.text[:70]}")
        print(f"    Reasoning:  {len(result.reasoning)} steps")

    # 5. Print evaluation summary
    print()
    print("=" * 66)
    print("  EVALUATION SUMMARY")
    print("=" * 66)
    print(f"  Agreement Score:         {evaluation.agreement_score:.4f}")
    print(f"  Contradiction Score:     {evaluation.contradiction_score:.4f}")
    print(f"  Novelty Score:           {evaluation.novelty_score:.4f}")
    print(f"  Evidence Coverage:       {evaluation.evidence_coverage_score:.4f}")
    print(f"  Drift Likelihood:        {evaluation.drift_likelihood:.4f}")
    print(f"  Escalation:              {evaluation.recommended_escalation}")
    if evaluation.notes:
        for note in evaluation.notes:
            print(f"  Note: {note}")
    print()

    # 6. Health check
    health = engine.health()
    print(f"  Engine healthy: {health['ok']}")
    print(f"  Adapter count:  {health['adapter_count']}")
    print()

    print("Models produce exhaust. Deep Sigma produces judgment.")


if __name__ == "__main__":
    run_demo()
