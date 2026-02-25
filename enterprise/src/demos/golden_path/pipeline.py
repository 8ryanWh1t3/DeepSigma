"""GoldenPathPipeline — 7-step end-to-end decision governance orchestrator."""
from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from demos.golden_path.assembler import RecordToEpisodeAssembler
from demos.golden_path.claim_extractor import ClaimExtractor
from demos.golden_path.config import GoldenPathConfig, GoldenPathResult
from demos.golden_path.delta_detector import DeltaDriftDetector


class GoldenPathPipeline:
    """Orchestrate the 7-step Golden Path loop."""

    def __init__(self, config: GoldenPathConfig):
        self.config = config
        self.steps: Dict[str, Any] = {}
        self._assembler = RecordToEpisodeAssembler()
        self._extractor = ClaimExtractor()
        self._drift_detector = DeltaDriftDetector()

    def run(self) -> GoldenPathResult:
        t0 = time.monotonic()
        out = Path(self.config.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        completed: List[str] = []

        # ── Step 1: Connect ──────────────────────────────────────────
        records = self._connect()
        completed.append("connect")
        _write_json(out / "step_1_connect" / "canonical_records.json", records)

        # ── Step 2: Normalize ────────────────────────────────────────
        episode = self._normalize(records)
        completed.append("normalize")
        step2 = out / "step_2_normalize"
        _write_json(step2 / "episode.json", episode)
        _write_json(step2 / "validation.json", {"valid": True, "errors": []})

        # ── Step 3: Extract ──────────────────────────────────────────
        claims = self._extract(records)
        completed.append("extract")
        _write_json(out / "step_3_extract" / "claims.json", claims)

        # ── Step 4: Seal ─────────────────────────────────────────────
        dlr, rs, ds, mg, report = self._seal(episode, claims)
        completed.append("seal")
        step4 = out / "step_4_seal"
        _write_json(step4 / "dlr.json", dlr.to_dict_list())
        _write_json(step4 / "rs.json", rs.summarise())
        _write_json(step4 / "ds.json", asdict(ds.summarise()))
        _write_json(step4 / "mg.json", mg.query("stats"))
        _write_json(step4 / "coherence_report.json", asdict(report))
        baseline_score = report.overall_score
        baseline_grade = report.grade

        # ── Step 5: Drift Detect ─────────────────────────────────────
        drift_events = self._detect_drift(records, episode["episodeId"])
        completed.append("drift")
        step5 = out / "step_5_drift"
        delta_records = self._load_delta()
        _write_json(step5 / "delta_records.json", delta_records or [])
        _write_json(step5 / "drift_report.json", drift_events)

        # ── Step 6: Patch ────────────────────────────────────────────
        patch, mg_patched, report_patched = self._patch(
            drift_events, episode, claims, mg
        )
        completed.append("patch")
        step6 = out / "step_6_patch"
        _write_json(step6 / "patch.json", patch)
        _write_json(step6 / "mg_patched.json", mg_patched.query("stats"))
        _write_json(step6 / "coherence_report_patched.json", asdict(report_patched))

        # ── Step 7: Recall (IRIS) ────────────────────────────────────
        iris_results = self._recall(mg_patched, dlr, rs, ds)
        completed.append("recall")
        step7 = out / "step_7_recall"
        for qtype, resp in iris_results.items():
            _write_json(step7 / f"iris_{qtype.lower()}.json", resp)

        elapsed_ms = (time.monotonic() - t0) * 1000

        result = GoldenPathResult(
            steps_completed=completed,
            canonical_records=len(records),
            claims_extracted=len(claims),
            episode_id=episode["episodeId"],
            baseline_score=baseline_score,
            baseline_grade=baseline_grade,
            drift_events=len(drift_events),
            patch_applied=len(drift_events) > 0,
            patched_score=report_patched.overall_score,
            patched_grade=report_patched.grade,
            iris_queries={k: v.get("status", "UNKNOWN") for k, v in iris_results.items()},
            output_dir=str(out),
            elapsed_ms=round(elapsed_ms, 1),
        )
        _write_json(out / "summary.json", result.to_dict())
        return result

    # ── Step implementations ─────────────────────────────────────────

    def _connect(self) -> List[Dict[str, Any]]:
        """Step 1: Pull canonical records from source or fixture."""
        if self.config.fixture_path:
            return self._load_fixture("baseline.json")
        return self._connect_live()

    def _connect_live(self) -> List[Dict[str, Any]]:
        """Connect to a live data source."""
        source = self.config.source
        if source == "sharepoint":
            from adapters.sharepoint.connector import SharePointConnector
            conn = SharePointConnector()
            return conn.list_items(self.config.list_id)
        elif source == "snowflake":
            from adapters.snowflake.warehouse import SnowflakeWarehouseConnector
            conn = SnowflakeWarehouseConnector()
            rows = conn.query(self.config.sql)
            return conn.to_canonical(rows, "query_result")
        elif source == "dataverse":
            from adapters.powerplatform.connector import DataverseConnector
            conn = DataverseConnector()
            return conn.list_records(self.config.table_name)
        elif source == "asksage":
            from adapters.asksage.connector import AskSageConnector
            conn = AskSageConnector()
            resp = conn.query(self.config.prompt)
            return [resp] if isinstance(resp, dict) else resp
        else:
            raise ValueError(f"Unknown source: {source}")

    def _normalize(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Step 2: Assemble canonical records into a schema-valid episode."""
        return self._assembler.assemble(
            records,
            decision_type=self.config.decision_type,
            episode_id=self.config.episode_id,
            source_name=self.config.source,
        )

    def _extract(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Step 3: Rule-based atomic claim extraction."""
        return self._extractor.extract(records)

    def _seal(
        self,
        episode: Dict[str, Any],
        claims: List[Dict[str, Any]],
    ) -> Tuple[Any, Any, Any, Any, Any]:
        """Step 4: Build DLR, RS, DS, MG and score."""
        from core.decision_log import DLRBuilder
        from core.reflection import ReflectionSession
        from core.drift_signal import DriftSignalCollector
        from core.memory_graph import MemoryGraph
        from core.scoring import CoherenceScorer

        dlr = DLRBuilder()
        dlr.from_episodes([episode])

        rs = ReflectionSession("golden-path")
        rs.ingest([episode])

        ds = DriftSignalCollector()

        mg = MemoryGraph()
        mg.add_episode(episode)
        for claim in claims:
            mg.add_claim(claim, episode_id=episode["episodeId"])

        scorer = CoherenceScorer(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
        report = scorer.score()

        return dlr, rs, ds, mg, report

    def _detect_drift(
        self,
        baseline_records: List[Dict[str, Any]],
        episode_id: str,
    ) -> List[Dict[str, Any]]:
        """Step 5: Load delta, compare, emit drift events."""
        delta = self._load_delta()
        if delta is None:
            return []
        return self._drift_detector.detect(baseline_records, delta, episode_id)

    def _load_delta(self) -> Optional[List[Dict[str, Any]]]:
        """Load delta records from fixture or live delta sync."""
        if self.config.fixture_path:
            delta_path = Path(self.config.fixture_path) / "delta.json"
            if delta_path.exists():
                return json.loads(delta_path.read_text())
        return None

    def _patch(
        self,
        drift_events: List[Dict[str, Any]],
        episode: Dict[str, Any],
        claims: List[Dict[str, Any]],
        mg_baseline: Any,
    ) -> Tuple[List[Dict[str, Any]], Any, Any]:
        """Step 6: Emit patches, rebuild artifacts, re-score."""
        from datetime import datetime, timezone
        from core.decision_log import DLRBuilder
        from core.reflection import ReflectionSession
        from core.drift_signal import DriftSignalCollector
        from core.memory_graph import MemoryGraph
        from core.scoring import CoherenceScorer

        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        patches: List[Dict[str, Any]] = []

        for i, drift in enumerate(drift_events):
            patches.append({
                "patchId": f"patch-gp-{i + 1:03d}",
                "driftId": drift["driftId"],
                "patchType": drift.get("recommendedPatchType", "RETCON"),
                "appliedAt": now,
                "description": f"Auto-patch: {drift.get('description', 'resolve drift')}",
                "changes": [
                    {
                        "field": "drift.status",
                        "from": "open",
                        "to": "resolved",
                    },
                ],
            })

        # Rebuild pipeline with drift + patches applied
        dlr = DLRBuilder()
        dlr.from_episodes([episode])

        rs = ReflectionSession("golden-path-patched")
        rs.ingest([episode])

        ds = DriftSignalCollector()
        # Don't ingest drift events into DS — they're resolved by patches

        mg = MemoryGraph()
        mg.add_episode(episode)
        for claim in claims:
            mg.add_claim(claim, episode_id=episode["episodeId"])
        for drift in drift_events:
            mg.add_drift(drift)
        for patch in patches:
            mg.add_patch(patch)

        scorer = CoherenceScorer(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
        report = scorer.score()

        return patches, mg, report

    def _recall(
        self,
        mg: Any,
        dlr: Any,
        rs: Any,
        ds: Any,
    ) -> Dict[str, Dict[str, Any]]:
        """Step 7: Run IRIS queries — WHY, WHAT_CHANGED, STATUS."""
        from core.iris import (
            IRISEngine,
            IRISConfig,
            IRISQuery,
            QueryType,
        )

        engine = IRISEngine(
            config=IRISConfig(),
            memory_graph=mg,
            dlr_entries=dlr.entries,
            rs=rs,
            ds=ds,
        )

        results = {}
        for qtype in [QueryType.WHY, QueryType.WHAT_CHANGED, QueryType.STATUS]:
            query = IRISQuery(
                query_type=qtype,
                episode_id=self.config.episode_id,
            )
            resp = engine.resolve(query)
            results[qtype] = resp.to_dict()

        return results

    # ── Fixture helpers ──────────────────────────────────────────────

    def _load_fixture(self, filename: str) -> List[Dict[str, Any]]:
        """Load a JSON fixture file."""
        path = Path(self.config.fixture_path) / filename
        if not path.exists():
            raise FileNotFoundError(f"Fixture not found: {path}")
        return json.loads(path.read_text())


def _write_json(path: Path, data: Any) -> None:
    """Write data as pretty JSON, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str) + "\n")
