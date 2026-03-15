"""
aws_connector.py — boto3-based connector for AWS services (CloudTrail, etc.).
Reads operation definitions from the plug JSON file.
"""
from __future__ import annotations

from typing import Any

from evident.connectors.base_connector import BaseConnector


class AwsConnector(BaseConnector):
    """Drives boto3 operations from plug JSON definitions."""

    def _authenticate(self) -> None:
        return None   # boto3 uses creds directly, not a token

    def _execute_api(
        self, api_def: dict, access_token: None, cursor=None
    ) -> tuple[list[dict], Any]:
        import boto3

        auth = self.plug.get("auth", {})
        param_map = auth.get("param_mapping", {})

        session_kwargs = {}
        for cfg_key, boto_key in param_map.items():
            if cfg_key in self.creds:
                session_kwargs[boto_key] = self.creds[cfg_key]

        service   = api_def.get("service", "cloudtrail")
        operation = api_def.get("operation")
        region    = self.creds.get("region", "us-east-1")

        client = boto3.client(service, region_name=region, **session_kwargs)

        call_params = dict(api_def.get("params", {}))
        if cursor:
            call_params["NextToken"] = cursor

        response = getattr(client, operation)(**call_params)

        result_path = api_def.get("result_path", "")
        rows = self.deep_get(response, result_path, []) if result_path else []
        if not isinstance(rows, list):
            rows = [rows]

        # Serialize any non-JSON-safe values (e.g. datetime objects)
        rows = _serialize_rows(rows)

        pag = api_def.get("pagination", {})
        next_cursor = response.get(pag.get("next_key", "NextToken")) if pag else None

        return rows, next_cursor


def _serialize_rows(rows: list) -> list:
    """Convert datetime objects etc. to strings for JSON/CSV compat."""
    import json
    from datetime import datetime, date

    def default(o):
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        return str(o)

    serialized = json.loads(json.dumps(rows, default=default))
    return serialized
