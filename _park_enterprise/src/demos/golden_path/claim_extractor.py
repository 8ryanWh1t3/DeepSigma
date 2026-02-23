"""ClaimExtractor — rule-based atomic claim extraction from canonical records."""
from __future__ import annotations

from typing import Any, Dict, List


class ClaimExtractor:
    """Extract one atomic claim per canonical record. No LLM required."""

    def extract(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        claims = []
        for record in records:
            record_id = record.get("record_id", "")
            content = record.get("content", {})
            title = content.get("title", "")
            body = content.get("body", "")

            text = title if title else (body[:200] if body else f"Record {record_id[:8]}")

            confidence = 0.5
            conf_obj = record.get("confidence", {})
            if isinstance(conf_obj, dict):
                confidence = conf_obj.get("score", 0.5)
            elif isinstance(conf_obj, (int, float)):
                confidence = float(conf_obj)

            if confidence >= 0.7:
                status = "green"
            elif confidence >= 0.5:
                status = "yellow"
            else:
                status = "red"

            provenance = record.get("provenance", [])
            source_ref = provenance[0].get("ref", "") if provenance else ""

            claims.append({
                "claim_id": f"CLAIM-{record_id[:8]}",
                "text": text,
                "source_ref": source_ref,
                "confidence": {"score": confidence},
                "status": status,
                "evidence": [{"ref": source_ref, "summary": text[:80]}],
                "record_type": record.get("record_type", "Entity"),
            })

        return claims
