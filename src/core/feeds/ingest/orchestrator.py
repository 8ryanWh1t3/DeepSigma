"""Manifest-first ingest orchestrator for FEEDS packets.

Workflow:
    1. Read manifest.json from packet directory
    2. Verify all declared artifacts exist + hashes match
    3. Schema-validate each artifact
    4. Extract payloads via per-topic extractors
    5. Build envelopes, stage in .staging/<packet_id>/
    6. Atomic move all staged events to inbox/ dirs
    7. On failure: cleanup staging, emit PROCESS_GAP drift signal
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..envelope import build_envelope, compute_payload_hash, load_contract_fingerprint
from ..types import Classification, FeedTopic, RecordType
from ..validate import validate_feed_event
from .extractors import EXTRACTORS


@dataclass
class IngestResult:
    """Result of a packet ingest operation."""

    success: bool
    packet_id: str
    events_published: int = 0
    errors: List[str] = field(default_factory=list)
    drift_signal_id: Optional[str] = None


class IngestOrchestrator:
    """Manifest-first packet ingest with atomic all-or-none semantics.

    Stages events in a temp directory, then atomically moves them to
    topic inboxes. On any failure, staging is cleaned up and a
    PROCESS_GAP drift signal is emitted.
    """

    def __init__(
        self,
        topics_root: str | Path,
        producer: str = "feeds-ingest",
        classification: Classification | str = Classification.LEVEL_0,
    ) -> None:
        self._root = Path(topics_root).resolve()
        self._producer = producer
        self._classification = classification

    def ingest(self, packet_dir: str | Path) -> IngestResult:
        """Ingest a coherence packet from a directory.

        The packet directory must contain a ``manifest.json`` declaring
        the artifacts and their expected hashes.

        Args:
            packet_dir: Path to the packet directory.

        Returns:
            IngestResult with success status, event counts, and any errors.
        """
        packet_path = Path(packet_dir).resolve()
        manifest_file = packet_path / "manifest.json"

        if not manifest_file.exists():
            return self._fail("unknown", [f"manifest.json not found in {packet_path}"])

        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        packet_id = manifest.get("packetId", f"CP-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-0000")

        # Phase 1: Verify artifacts exist + hashes match
        errors = self._verify_artifacts(packet_path, manifest)
        if errors:
            return self._fail(packet_id, errors)

        # Phase 2: Extract payloads and build envelopes
        contract_fp = load_contract_fingerprint()
        envelopes: List[Dict[str, Any]] = []
        errors = []
        sequence = 0

        # Determine which topics have artifacts
        declared = manifest.get("artifacts", {})
        topics_to_ingest = list(declared.keys()) if declared else self._detect_topics(packet_path)

        # Always build packet_index first
        if "packet_index" not in topics_to_ingest:
            topics_to_ingest.insert(0, "packet_index")
        else:
            topics_to_ingest.remove("packet_index")
            topics_to_ingest.insert(0, "packet_index")

        for topic_name in topics_to_ingest:
            extractor = EXTRACTORS.get(topic_name)
            if extractor is None:
                errors.append(f"No extractor for topic: {topic_name}")
                continue

            try:
                payload = extractor(packet_path, manifest)
                if not payload:
                    continue

                envelope = build_envelope(
                    topic=topic_name,
                    payload=payload,
                    packet_id=packet_id,
                    producer=self._producer,
                    classification=self._classification,
                    sequence=sequence,
                    contract_fingerprint=contract_fp,
                )
                # Validate the built envelope
                result = validate_feed_event(envelope)
                if not result.valid:
                    err_msgs = "; ".join(e.message for e in result.errors)
                    errors.append(f"Schema validation failed for {topic_name}: {err_msgs}")
                    continue

                envelopes.append(envelope)
                sequence += 1
            except Exception as exc:
                errors.append(f"Extraction failed for {topic_name}: {exc}")

        if errors:
            return self._fail(packet_id, errors)

        if not envelopes:
            return self._fail(packet_id, ["No events extracted from packet"])

        # Phase 3: Atomic staging + commit
        return self._stage_and_commit(packet_id, envelopes)

    def _verify_artifacts(
        self, packet_path: Path, manifest: Dict[str, Any]
    ) -> List[str]:
        """Verify declared artifacts exist and hashes match."""
        errors: List[str] = []
        artifacts = manifest.get("artifacts", {})

        for topic_name, artifact_meta in artifacts.items():
            expected_file = artifact_meta.get("file")
            expected_hash = artifact_meta.get("hash")

            if expected_file:
                artifact_path = packet_path / expected_file
                if not artifact_path.exists():
                    errors.append(f"Missing artifact: {expected_file}")
                    continue

                if expected_hash:
                    content = json.loads(artifact_path.read_text(encoding="utf-8"))
                    actual_hash = compute_payload_hash(content)
                    if actual_hash != expected_hash:
                        errors.append(
                            f"Hash mismatch for {expected_file}: "
                            f"expected={expected_hash}, actual={actual_hash}"
                        )
        return errors

    def _detect_topics(self, packet_path: Path) -> List[str]:
        """Auto-detect topics from files present in packet directory."""
        topic_files = {
            "truth_snapshot": "truth_snapshot.json",
            "authority_slice": "authority_slice.json",
            "decision_lineage": "decision_lineage.json",
            "drift_signal": "drift_signal.json",
            "canon_entry": "canon_entry.json",
        }
        detected = []
        for topic, filename in topic_files.items():
            if (packet_path / filename).exists():
                detected.append(topic)
        return detected

    def _stage_and_commit(
        self, packet_id: str, envelopes: List[Dict[str, Any]]
    ) -> IngestResult:
        """Stage envelopes to temp dir, then atomically move to inboxes."""
        staging = self._root / ".staging" / packet_id
        staging.mkdir(parents=True, exist_ok=True)

        try:
            # Stage all events
            staged_files: List[tuple] = []  # (staged_path, target_inbox_path)
            for envelope in envelopes:
                topic = envelope["topic"]
                event_id = envelope["eventId"]
                filename = f"{event_id}.json"

                staged_path = staging / f"{topic}_{filename}"
                staged_path.write_text(
                    json.dumps(envelope, indent=2), encoding="utf-8"
                )

                target = self._root / topic / "inbox" / filename
                staged_files.append((staged_path, target))

            # Commit: atomic rename each staged file to inbox
            for staged_path, target_path in staged_files:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                os.rename(str(staged_path), str(target_path))

            return IngestResult(
                success=True,
                packet_id=packet_id,
                events_published=len(envelopes),
            )

        except Exception as exc:
            # Rollback: clean any files that made it to inbox
            for staged_path, target_path in staged_files:
                if target_path.exists():
                    target_path.unlink()
            return self._fail(packet_id, [f"Staging commit failed: {exc}"])

        finally:
            # Always clean staging
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)

    def _fail(self, packet_id: str, errors: List[str]) -> IngestResult:
        """Build a failure result and emit a PROCESS_GAP drift signal."""
        drift_id = f"DS-ingest-{uuid.uuid4().hex[:12]}"

        # Attempt to publish PROCESS_GAP drift signal
        try:
            drift_payload = {
                "driftId": drift_id,
                "driftType": "process_gap",
                "severity": "red",
                "detectedAt": datetime.now(timezone.utc).isoformat(),
                "evidenceRefs": [f"packet:{packet_id}"],
                "recommendedPatchType": "process_fix",
                "fingerprint": {"key": f"ingest:{packet_id}", "version": "1"},
                "notes": "; ".join(errors),
            }
            envelope = build_envelope(
                topic=FeedTopic.DRIFT_SIGNAL,
                payload=drift_payload,
                packet_id=packet_id,
                producer=self._producer,
                classification=self._classification,
                contract_fingerprint=load_contract_fingerprint(),
            )
            ds_inbox = self._root / "drift_signal" / "inbox"
            if ds_inbox.is_dir():
                target = ds_inbox / f"{envelope['eventId']}.json"
                target.write_text(
                    json.dumps(envelope, indent=2), encoding="utf-8"
                )
        except Exception:
            pass  # Best-effort drift emission

        return IngestResult(
            success=False,
            packet_id=packet_id,
            errors=errors,
            drift_signal_id=drift_id,
        )
