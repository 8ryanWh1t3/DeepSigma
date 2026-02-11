"""Policy Pack loader (Scaffold)."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict

def load_policy_pack(path: str) -> Dict[str, Any]:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8"))

def get_rules(pack: Dict[str, Any], decision_type: str) -> Dict[str, Any]:
    return pack.get("rules", {}).get(decision_type, {})
