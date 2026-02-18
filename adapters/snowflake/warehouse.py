"""Snowflake Data Warehouse connector.

Uses the Snowflake SQL REST API (``POST /api/v2/statements``) for queries.

Usage::

    connector = SnowflakeWarehouseConnector()
    rows = connector.query("SELECT * FROM my_table LIMIT 10")
    tables = connector.list_tables()
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any, Dict, List, Optional

from adapters._connector_helpers import to_iso, uuid_from_hash
from adapters.snowflake._auth import SnowflakeAuth

logger = logging.getLogger(__name__)


class SnowflakeWarehouseConnector:
    """Snowflake SQL REST API connector.

    Configuration via environment variables:

    - ``SNOWFLAKE_ACCOUNT``
    - ``SNOWFLAKE_DATABASE``
    - ``SNOWFLAKE_SCHEMA`` (default: ``PUBLIC``)
    - ``SNOWFLAKE_WAREHOUSE``
    """

    def __init__(self, auth: Optional[SnowflakeAuth] = None) -> None:
        self._auth = auth or SnowflakeAuth()
        self._database = os.environ.get("SNOWFLAKE_DATABASE", "")
        self._schema = os.environ.get("SNOWFLAKE_SCHEMA", "PUBLIC")
        self._warehouse = os.environ.get("SNOWFLAKE_WAREHOUSE", "")

    # ── Public API ───────────────────────────────────────────────

    def query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute a SQL query and return rows as list of dicts."""
        result = self._execute_statement(sql)
        return self._parse_result(result)

    def list_tables(self) -> List[Dict[str, Any]]:
        """List tables in the configured database/schema."""
        sql = f"SHOW TABLES IN {self._database}.{self._schema}"
        result = self._execute_statement(sql)
        return self._parse_result(result)

    def get_table_schema(self, table: str) -> List[Dict[str, Any]]:
        """Describe a table's column definitions."""
        sql = f"DESCRIBE TABLE {self._database}.{self._schema}.{table}"
        result = self._execute_statement(sql)
        return self._parse_result(result)

    def to_canonical(self, rows: List[Dict[str, Any]], table_name: str) -> List[Dict[str, Any]]:
        """Transform SQL rows to canonical records."""
        records = []
        for row in rows:
            pk = self._find_pk(row)
            fqn = f"{self._database}.{self._schema}.{table_name}"
            record_id = uuid_from_hash("snowflake", f"{fqn}.{pk}") if pk else ""

            records.append({
                "record_id": record_id,
                "record_type": self._infer_type(row),
                "created_at": to_iso(str(row.get("CREATED_AT", row.get("created_at", "")))),
                "observed_at": to_iso(str(row.get("UPDATED_AT", row.get("updated_at", "")))),
                "source": {
                    "system": "snowflake",
                    "actor": {"id": "", "type": "system"},
                },
                "provenance": [
                    {
                        "type": "source",
                        "ref": f"snowflake://{self._auth.account}/{fqn}/{pk}",
                    }
                ],
                "confidence": {"score": 0.90},
                "ttl": 86400000,  # 24h default for warehouse data
                "content": {k: v for k, v in row.items()},
                "labels": {"tags": [f"table:{table_name}"]},
            })
        return records

    def sync_table(self, table_name: str, since: Optional[str] = None) -> Dict[str, Any]:
        """Sync rows from a table, optionally since a timestamp."""
        fqt = f"{self._database}.{self._schema}.{table_name}"
        if since:
            sql = f"SELECT * FROM {fqt} WHERE UPDATED_AT > '{since}' ORDER BY UPDATED_AT"
        else:
            sql = f"SELECT * FROM {fqt} ORDER BY UPDATED_AT DESC LIMIT 1000"

        rows = self.query(sql)
        records = self.to_canonical(rows, table_name)
        return {
            "synced": len(records),
            "records": records,
        }

    # ── SQL REST API ─────────────────────────────────────────────

    def _execute_statement(self, sql: str) -> Dict[str, Any]:
        url = f"{self._auth.base_url}/api/v2/statements"
        payload = {
            "statement": sql,
            "timeout": 60,
            "database": self._database,
            "schema": self._schema,
            "warehouse": self._warehouse,
        }

        headers = self._auth.get_headers()
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"

        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())

    @staticmethod
    def _parse_result(result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Snowflake SQL REST API response into row dicts."""
        columns = [col["name"] for col in result.get("resultSetMetaData", {}).get("rowType", [])]
        rows = []
        for data_row in result.get("data", []):
            rows.append(dict(zip(columns, data_row)))
        return rows

    @staticmethod
    def _find_pk(row: Dict[str, Any]) -> str:
        """Find primary key value from a row."""
        for key in ("ID", "id", "PK", "pk", "PRIMARY_KEY"):
            if key in row and row[key]:
                return str(row[key])
        # Fallback: first column
        for v in row.values():
            if v:
                return str(v)
        return ""

    @staticmethod
    def _infer_type(row: Dict[str, Any]) -> str:
        """Infer canonical record_type from row content."""
        keys = {k.lower() for k in row.keys()}
        if any(k in keys for k in ("metric", "value", "measurement", "score")):
            return "Metric"
        if any(k in keys for k in ("name", "entity", "account", "customer")):
            return "Entity"
        return "Claim"
