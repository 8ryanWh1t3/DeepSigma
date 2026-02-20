#!/usr/bin/env python3
"""Σ OVERWATCH OTel Sidecar — watch a data directory and export episodes/drift to OTLP.

Watches /app/data/episodes/ and /app/data/drift/ for new JSON files,
exports each to the configured OTLP endpoint, then moves them to
/app/data/exported/ to avoid re-processing.

Environment variables:
    OTEL_EXPORTER_OTLP_ENDPOINT  OTLP gRPC (default) or HTTP endpoint
                                  e.g. http://otel-collector:4317
    OTEL_SERVICE_NAME            Service name tag (default: sigma-overwatch)
    SIDECAR_POLL_INTERVAL        Seconds between directory polls (default: 5)
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path

# Ensure the app root is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from adapters.otel.exporter import OtelExporter  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATA_ROOT = Path(os.environ.get("SIDECAR_DATA_DIR", "/app/data"))
EPISODES_DIR = DATA_ROOT / "episodes"
DRIFT_DIR = DATA_ROOT / "drift"
EXPORTED_DIR = DATA_ROOT / "exported"
POLL_INTERVAL = int(os.environ.get("SIDECAR_POLL_INTERVAL", "5"))


def _ensure_dirs() -> None:
    for d in (EPISODES_DIR, DRIFT_DIR, EXPORTED_DIR):
        d.mkdir(parents=True, exist_ok=True)


def _export_file(path: Path, exporter: OtelExporter, kind: str) -> None:
    try:
        data = json.loads(path.read_text())
        items = data if isinstance(data, list) else [data]
        for item in items:
            if kind == "episode":
                exporter.export_episode(item)
            else:
                exporter.export_drift(item)
        dest = EXPORTED_DIR / path.name
        path.rename(dest)
        logger.info("Exported %s → %s", path.name, dest)
    except Exception as exc:
        logger.error("Failed to export %s: %s", path, exc)


def run() -> None:
    _ensure_dirs()
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    logger.info("Starting OTel sidecar | endpoint=%s | poll=%ss", endpoint or "console", POLL_INTERVAL)
    exporter = OtelExporter()

    while True:
        for ep_file in sorted(EPISODES_DIR.glob("*.json")):
            _export_file(ep_file, exporter, "episode")
        for dr_file in sorted(DRIFT_DIR.glob("*.json")):
            _export_file(dr_file, exporter, "drift")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run()
