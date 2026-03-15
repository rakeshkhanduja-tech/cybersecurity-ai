"""
base_connector.py — Abstract base class for all Data Plug connectors.
Each connector reads its API definitions from its plug JSON file, fetches
raw data via those definitions, maps to Evident or OCSF schema, and writes
to storage.
"""
from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CONNECTORS_DIR = Path(__file__).parent


class BaseConnector(ABC):
    """
    Generic plug-driven connector.  Sub-classes only need to override
    `_execute_api(api_def, creds)` to call the right SDK / HTTP library.
    Everything else (auth, mapping, storage dispatch) is handled here.
    """

    def __init__(self, plug_def: dict, creds: dict, run_logger=None):
        """
        plug_def  — the entry from data_plugs.json (id, name, plug_file …)
        creds     — dict of { param_name: value } saved in SQLite
        run_logger — optional ConnectorLogger instance for CSV logging
        """
        self.plug_def = plug_def
        self.creds = creds
        self.connector_id: str = plug_def["id"]
        self.display_name: str = plug_def["name"]
        self.run_logger = run_logger

        # Load the detailed plug JSON file
        plug_file = CONNECTORS_DIR / "dataplugs" / plug_def["plug_file"]
        with open(plug_file, encoding="utf-8") as f:
            self.plug: dict = json.load(f)

        self.base_url: str = self.plug.get("base_url", "")

    # ------------------------------------------------------------------
    # Public interface called by the scheduler
    # ------------------------------------------------------------------

    def run(self, schema: str, storage, selected_signals: list[str] = None) -> int:
        """
        Full pipeline: fetch → map → store.
        Returns total records written.
        """
        schema = schema.lower()
        if self.run_logger:
            msg = f"Starting run for {self.connector_id} with schema {schema}"
            if selected_signals:
                msg += f" (Signals: {', '.join(selected_signals)})"
            self.run_logger.info("Connector", msg)
        
        total = 0
        try:
            access_token = self._authenticate()
            if self.run_logger:
                auth_status = "Success" if access_token or self.plug.get("auth", {}).get("type") in ("api_key", "aws_credentials", "ssws") else "No token needed"
                self.run_logger.info("Auth", f"Authentication status: {auth_status}")

            for api_def in self.plug.get("apis", []):
                api_id = api_def["id"]
                api_signal = api_def.get("signal")

                # Filter by signal if specified
                if selected_signals and api_signal and api_signal not in selected_signals:
                    if self.run_logger:
                        self.run_logger.info("API", f"Skipping API: {api_id} (Signal '{api_signal}' not selected)")
                    continue

                if self.run_logger:
                    self.run_logger.info("API", f"Fetching data for API: {api_id}")
                
                raw_rows = self._fetch_all(api_def, access_token)
                if not raw_rows:
                    if self.run_logger:
                        self.run_logger.info("API", f"No records found for {api_id}")
                    continue
                
                if self.run_logger:
                    self.run_logger.info("API", f"Fetched {len(raw_rows)} raw records for {api_id}")

                mapped = self._map(api_id, raw_rows, schema)
                if mapped:
                    if self.run_logger:
                        self.run_logger.info("Mapping", f"Successfully mapped {len(mapped)} records to {schema}")
                    
                    storage.write(
                        connector_id=self.connector_id,
                        api_id=api_id,
                        schema=schema,
                        source_name=self._source_name(api_id, schema),
                        rows=mapped,
                    )
                    total += len(mapped)
                    if self.run_logger:
                        self.run_logger.info("Storage", f"Stored {len(mapped)} records")
        except Exception as exc:
            msg = f"Run failed: {exc}"
            logger.error("[%s] %s", self.connector_id, msg, exc_info=True)
            if self.run_logger:
                self.run_logger.error("Connector", msg)
        
    def test_connection(self) -> dict:
        """
        Verifies credentials by attempting authentication.
        Returns {"status": "success"} or {"status": "error", "message": "..."}.
        """
        try:
            self._authenticate()
            return {"status": "success", "message": "Authentication successful"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _authenticate(self) -> str | None:
        """Return an access token (or None for credential-based auth)."""
        auth = self.plug.get("auth", {})
        auth_type = auth.get("type", "")

        if auth_type == "oauth2_client_credentials":
            return self._oauth2_token(auth)
        if auth_type in ("aws_credentials", "api_key", "ssws", ""):
            return None          # handled per-api in sub-class
        raise ValueError(f"Unknown auth type: {auth_type}")

    def _oauth2_token(self, auth: dict) -> str:
        import requests

        token_url = self._substitute_creds(auth["token_endpoint"])

        # Build payload from param_mapping + extra_params
        payload = {}
        for cfg_key, api_key in auth.get("param_mapping", {}).items():
            payload[api_key] = self.creds.get(cfg_key, "")
            
        # Add extra_params, performing substitutions on string values
        for k, v in auth.get("extra_params", {}).items():
            payload[k] = self._substitute_creds(v)
            
        # Skip parameters that are still placeholders or empty
        import re
        final_payload = {}
        for k, v in payload.items():
            if isinstance(v, str):
                if re.fullmatch(r"\{[a-zA-Z0-9_-]+\}", v) or v == "":
                    continue
            final_payload[k] = v
        
        final_payload.setdefault("grant_type", "client_credentials")

        auth_format = auth.get("auth_format", "form") # default to form-encoded

        try:
            if auth_format == "json":
                resp = requests.post(token_url, json=final_payload, timeout=15)
            else:
                resp = requests.post(token_url, data=final_payload, timeout=15)
                
            resp.raise_for_status()
            return resp.json()["access_token"]
        except requests.exceptions.HTTPError as e:
            error_body = ""
            try:
                error_body = f" | Body: {resp.text}"
            except:
                pass
            msg = f"OAuth2 token request failed ({resp.status_code}) for {token_url}{error_body}"
            if self.run_logger:
                self.run_logger.error("Auth", msg)
            raise requests.exceptions.HTTPError(msg, response=resp) from e
        except Exception as e:
            if self.run_logger:
                self.run_logger.error("Auth", f"Token request failed: {e}")
            raise

    # ------------------------------------------------------------------
    # Fetch (with pagination)
    # ------------------------------------------------------------------

    def _fetch_all(self, api_def: dict, access_token: str | None) -> list[dict]:
        """Repeatedly calls the API until all pages are fetched."""
        rows: list[dict] = []
        next_cursor = None

        while True:
            batch, next_cursor = self._fetch_page(api_def, access_token, next_cursor)
            rows.extend(batch)
            if not next_cursor:
                break
        return rows

    def _fetch_page(
        self, api_def: dict, access_token: str | None, cursor=None
    ) -> tuple[list[dict], Any]:
        """Single page fetch — delegated to concrete sub-class."""
        return self._execute_api(api_def, access_token, cursor)

    @abstractmethod
    def _execute_api(
        self, api_def: dict, access_token: str | None, cursor=None
    ) -> tuple[list[dict], Any]:
        """
        Execute one API call.  Return (rows, next_cursor).
        next_cursor=None means no more pages.
        """

    # ------------------------------------------------------------------
    # Mapping
    # ------------------------------------------------------------------

    def _map(self, api_id: str, rows: list[dict], schema: str) -> list[dict]:
        from evident.connectors.mapper import map_rows
        return map_rows(self.plug, api_id, rows, schema)

    def _source_name(self, api_id: str, schema: str) -> str:
        """Return the Evident source name (e.g. 'signin_logs') for path building."""
        # First, try to find the signal field in the API definition itself
        for api in self.plug.get("apis", []):
            if api.get("id") == api_id and api.get("signal"):
                return api["signal"]

        # Fallback to mapping lookup or api_id
        mapping = self.plug.get("source_mapping", {}).get(schema, {})
        if api_id in mapping:
            return api_id
        return list(mapping.keys())[0] if mapping else api_id

    # ------------------------------------------------------------------
    # Header construction helper
    # ------------------------------------------------------------------

    def _build_headers(self, header_template: dict, access_token: str | None) -> dict:
        headers = {}
        for k, v in header_template.items():
            val = str(v)
            if "{access_token}" in val:
                val = val.replace("{access_token}", access_token or "")
            
            val = self._substitute_creds(val)
            headers[k] = val
        return headers

    def _substitute_creds(self, text: str) -> str:
        """Replace {param_name} placeholders with values from self.creds."""
        if not text or not isinstance(text, str):
            return text
        for k, v in self.creds.items():
            text = text.replace(f"{{{k}}}", str(v))
        return text

    # ------------------------------------------------------------------
    # Deep-get helper for nested field paths like "behaviors[0].description"
    # ------------------------------------------------------------------

    @staticmethod
    def deep_get(obj: Any, path: str, default="") -> Any:
        if not path or path == "$":
            return obj
        
        import re
        parts = re.split(r"[.\[\]]+", path)
        for part in parts:
            if part == "":
                continue
            if isinstance(obj, list):
                try:
                    obj = obj[int(part)]
                except (IndexError, ValueError):
                    return default
            elif isinstance(obj, dict):
                obj = obj.get(part, default)
            else:
                return default
        return obj if obj is not None else default
