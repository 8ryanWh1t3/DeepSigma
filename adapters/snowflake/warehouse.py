"""Snowflake Data Warehouse connector.

Uses the Snowflake SQL REST API (``POST /api/v2/statements``).

Production features:
- ConnectorV1 contract compliance (list_records, get_record)
- Column mapping configuration for evidence field extraction
- Table, view, and query source modes
- JWT, OAuth, and PAT authentication

Usage::

    connector = SnowflakeWarehouseConnector()
    records = connector.list_records(table="users")
    record  = connector.get_record("rec-id", table="users")
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

# Default column mapping: Snowflake column → canonical field
_DEFAULT_COLUMN_MAP: Dict[str, str] = {
    "ID": "record_id",
    "CREATED_AT": "created_at",
    "UPDATED_AT": "observed_at",
    "TITLE": "content.title",
    "BODY": "content.body",
    "TAGS": "labels.tags",
}


class SnowflakeWarehouseConnector:
    """Snowflake SQL REST API connector.

    Configuration via environment variables:

    - ``SNOWFLAKE_ACCOUNT``
    - ``SNOWFLAKE_DATABASE``
    - ``SNOWFLAKE_SCHEMA`` (default: ``PUBLIC``)
    - ``SNOWFLAKE_WAREHOUSE``

    Implements ConnectorV1 contract (v0.6.0+).
    """

    source_name = "snowflake"

    def __init__(
        self,
        auth: Optional[SnowflakeAuth] = None,
        column_map: Optional[Dict[str, str]] = None,
    ) -> None:
        self._auth = auth or SnowflakeAuth()
        self._database = os.environ.get(
            "SNOWFLAKE_DATABASE", "",
        )
        self._schema = os.environ.get(
            "SNOWFLAKE_SCHEMA", "PUBLIC",
        )
        self._warehouse = os.environ.get(
            "SNOWFLAKE_WAREHOUSE", "",
        )
        self._column_map = column_map or dict(
            _DEFAULT_COLUMN_MAP,
        )

    # ── ConnectorV1 contract ─────────────────────────────────────

    def list_records(
        self, **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """List canonical records from a Snowflake table.

        Parameters
        ----------
        table : str
            Table name (required keyword argument).
        sql : str, optional
            Custom SQL query (overrides table).
        limit : int, optional
            Max rows to return (default 1000).
        """
        sql = kwargs.get("sql", "")
        table = kwargs.get("table", "")
        limit = kwargs.get("limit", 1000)

        if sql:
            rows = self.query(sql)
            tbl = table or "query"
        elif table:
            fqt = (
                f"{self._database}"
                f".{self._schema}.{table}"
            )
            stmt = (
                f"SELECT * FROM {fqt}"
                f" ORDER BY 1 DESC LIMIT {limit}"
            )
            rows = self.query(stmt)
            tbl = table
        else:
            raise ValueError(
                "table or sql is required "
                "for list_records()"
            )
        return self.to_canonical(rows, tbl)

    def get_record(
        self, record_id: str, **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get a single canonical record by primary key.

        Parameters
        ----------
        record_id : str
            Primary key value.
        table : str
            Table name (required keyword argument).
        pk_column : str, optional
            Primary key column name (default ``ID``).
        """
        table = kwargs.get("table", "")
        if not table:
            raise ValueError(
                "table is required for get_record()"
            )
        pk_col = kwargs.get("pk_column", "ID")
        fqt = (
            f"{self._database}"
            f".{self._schema}.{table}"
        )
        sql = (
            f"SELECT * FROM {fqt}"
            f" WHERE {pk_col} = '{record_id}'"
            f" LIMIT 1"
        )
        rows = self.query(sql)
        if not rows:
            raise LookupError(
                f"Record {record_id} not found "
                f"in {table}"
            )
        return self.to_canonical(rows, table)[0]

    # ── Public API ───────────────────────────────────────────────

    def query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute a SQL query and return rows as list of dicts."""
        result = self._execute_statement(sql)
        return self._parse_result(result)

    def list_tables(self) -> List[Dict[str, Any]]:
        """List tables in the configured database/schema."""
        sql = (
            f"SHOW TABLES IN"
            f" {self._database}.{self._schema}"
        )
        result = self._execute_statement(sql)
        return self._parse_result(result)

    def get_table_schema(
        self, table: str,
    ) -> List[Dict[str, Any]]:
        """Describe a table's column definitions."""
        fqt = (
            f"{self._database}"
            f".{self._schema}.{table}"
        )
        sql = f"DESCRIBE TABLE {fqt}"
        result = self._execute_statement(sql)
        return self._parse_result(result)

    def to_envelopes(
        self, records: List[Dict[str, Any]],
    ) -> list:
        """Wrap canonical records in RecordEnvelopes."""
        from connectors.contract import canonical_to_envelope
        inst = (
            self._auth.account if self._auth
            else "unknown"
        )
        return [
            canonical_to_envelope(
                r, source_instance=inst,
            )
            for r in records
        ]

    def to_canonical(
        self,
        rows: List[Dict[str, Any]],
        table_name: str,
    ) -> List[Dict[str, Any]]:
        """Transform SQL rows to canonical records."""
        records = []
        for row in rows:
            pk = self._find_pk(row)
            fqn = (
                f"{self._database}"
                f".{self._schema}.{table_name}"
            )
            rec_id = (
                uuid_from_hash("snowflake", f"{fqn}.{pk}")
                if pk else ""
            )

            # Use column mapping for dates
            created_col = self._mapped_value(
                row, "created_at",
            )
            updated_col = self._mapped_value(
                row, "observed_at",
            )

            prov_ref = (
                f"snowflake://{self._auth.account}"
                f"/{fqn}/{pk}"
            )
            records.append({
                "record_id": rec_id,
                "record_type": self._infer_type(row),
                "created_at": to_iso(str(created_col)),
                "observed_at": to_iso(str(updated_col)),
                "source": {
                    "system": "snowflake",
                    "actor": {
                        "id": "", "type": "system",
                    },
                },
                "provenance": [{
                    "type": "source",
                    "ref": prov_ref,
                }],
                "confidence": {"score": 0.90},
                "ttl": 86400000,
                "content": dict(row.items()),
                "labels": {
                    "tags": [f"table:{table_name}"],
                },
            })
        return records

    def sync_table(
        self,
        table_name: str,
        since: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Sync rows from a table, optionally since a timestamp."""
        fqt = (
            f"{self._database}"
            f".{self._schema}.{table_name}"
        )
        if since:
            sql = (
                f"SELECT * FROM {fqt}"
                f" WHERE UPDATED_AT > '{since}'"
                f" ORDER BY UPDATED_AT"
            )
        else:
            sql = (
                f"SELECT * FROM {fqt}"
                f" ORDER BY UPDATED_AT DESC"
                f" LIMIT 1000"
            )

        rows = self.query(sql)
        records = self.to_canonical(rows, table_name)
        return {
            "synced": len(records),
            "records": records,
        }

    def _mapped_value(
        self, row: Dict[str, Any], field: str,
    ) -> Any:
        """Resolve a canonical field via column map.

        Checks mapped column name and case variants.
        Falls back to default map if instance was
        created without __init__ (mock testing).
        """
        col_map = getattr(
            self, "_column_map", _DEFAULT_COLUMN_MAP,
        )
        # Reverse lookup: canonical field → source col
        for src_col, tgt_field in col_map.items():
            if tgt_field == field:
                if src_col in row:
                    return row[src_col]
                lower = src_col.lower()
                if lower in row:
                    return row[lower]
        return ""

    # ── SQL REST API ─────────────────────────────────────────────

    def _execute_statement(
        self, sql: str,
    ) -> Dict[str, Any]:
        url = (
            f"{self._auth.base_url}"
            f"/api/v2/statements"
        )
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
        req = urllib.request.Request(
            url, data=data,
            headers=headers, method="POST",
        )

        with urllib.request.urlopen(
            req, timeout=60,
        ) as resp:
            return json.loads(resp.read())

    @staticmethod
    def _parse_result(
        result: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Parse Snowflake SQL REST API response."""
        meta = result.get("resultSetMetaData", {})
        columns = [
            col["name"]
            for col in meta.get("rowType", [])
        ]
        rows = []
        for data_row in result.get("data", []):
            rows.append(dict(zip(columns, data_row)))
        return rows

    @staticmethod
    def _find_pk(row: Dict[str, Any]) -> str:
        """Find primary key value from a row."""
        pk_names = (
            "ID", "id", "PK", "pk", "PRIMARY_KEY",
        )
        for key in pk_names:
            if key in row and row[key]:
                return str(row[key])
        for v in row.values():
            if v:
                return str(v)
        return ""

    @staticmethod
    def _infer_type(row: Dict[str, Any]) -> str:
        """Infer canonical record_type from row content."""
        keys = {k.lower() for k in row.keys()}
        metric_keys = (
            "metric", "value", "measurement", "score",
        )
        entity_keys = (
            "name", "entity", "account", "customer",
        )
        if any(k in keys for k in metric_keys):
            return "Metric"
        if any(k in keys for k in entity_keys):
            return "Entity"
        return "Claim"
