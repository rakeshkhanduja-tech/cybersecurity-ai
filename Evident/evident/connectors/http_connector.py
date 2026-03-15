"""
HTTP connector — handles REST/OAuth2-based APIs (CrowdStrike, Active Directory, Okta).
Reads all endpoint definitions from the connector's plug JSON file.
"""
from __future__ import annotations

from typing import Any

import requests

from evident.connectors.base_connector import BaseConnector


class HttpConnector(BaseConnector):
    """
    Generic HTTP connector driven entirely by the plug JSON definition.
    Handles GET and POST requests with Bearer token auth.
    """

    # Shared across all paginated calls so IDs from step-1 can feed step-2
    _prev_results: dict[str, list] = {}

    def _execute_api(
        self, api_def: dict, access_token: str | None, cursor=None
    ) -> tuple[list[dict], Any]:

        method  = api_def.get("method", "GET").upper()
        endpoint = self._substitute_creds(api_def.get("endpoint", ""))
        base     = self._substitute_creds(self.base_url).rstrip("/")
        url      = f"{base}{endpoint}"

        headers = self._build_headers(api_def.get("headers", {}), access_token)
        
        if self.run_logger:
            self.run_logger.info("HTTP", f"Executing {method} {url}")

        # ----- Build query params -----
        params = dict(api_def.get("params", {}))
        pagination = api_def.get("pagination", {})
        if cursor and pagination:
            ptype = pagination.get("type")
            if ptype == "offset":
                params[pagination["param"]] = cursor
            elif ptype == "nextLink":
                url = cursor  # entire next URL provided by Graph API
            elif ptype in ("json_token", "query", "cursor_param"):
                # Google Workspace/Stripe style: put the token/cursor in a query param
                params[pagination.get("param", "pageToken")] = cursor

        # ----- Build body (POST) -----
        body = None
        if method == "POST":
            raw_body = api_def.get("body", {})
            body = self._resolve_body(raw_body)

        # ----- Execute -----
        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, params=params, timeout=30)
            else:
                resp = requests.post(url, headers=headers, json=body, timeout=30)

            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as e:
            error_body = ""
            try:
                error_body = f" | Body: {resp.text}"
            except:
                pass
            msg = f"HTTP {method} failed ({resp.status_code}) for {url}{error_body}"
            if self.run_logger:
                self.run_logger.error("HTTP", msg)
            raise requests.exceptions.HTTPError(msg, response=resp) from e
        except Exception as e:
            if self.run_logger:
                self.run_logger.error("HTTP", f"Request failed: {e}")
            raise

        result_path = api_def.get("result_path", "")
        rows = self.deep_get(data, result_path, []) if result_path else data
        if not isinstance(rows, list):
            rows = [rows]

        # Store for potential chained lookups
        self._prev_results[api_def["id"]] = rows

        # ----- Next cursor -----
        next_cursor = None
        ptype = pagination.get("type", "")
        if ptype == "offset":
            total = data.get("meta", {}).get("total_count", len(rows))
            offset = cursor or 0
            limit  = params.get(pagination.get("limit_param", "limit"), 100)
            next_cursor = offset + limit if offset + limit < total else None
        elif ptype == "nextLink":
            next_cursor = data.get(pagination.get("next_key", "@odata.nextLink"))
        elif ptype == "json_token":
            # Google style: next token in the JSON body
            next_cursor = data.get(pagination.get("next_key", "nextPageToken"))
        elif ptype == "cursor_param":
            # Stripe style: next cursor is the ID of the last record in this batch
            if rows:
                next_cursor = rows[-1].get(pagination.get("cursor_key", "id"))
        elif ptype == "link_header":
            # Okta/Github style: check the HTTP headers for 'Link'
            links = resp.links  # requests library parses this for us
            if pagination.get("rel", "next") in links:
                next_cursor = links[pagination.get("rel", "next")]["url"]

        return rows, next_cursor

    def _resolve_body(self, raw_body: dict) -> dict:
        """
        Replace `{ids_from:<api_id>}` placeholders with actual IDs from
        a previous API call (e.g. CrowdStrike detect IDs → detail lookup).
        """
        resolved = {}
        for k, v in raw_body.items():
            if isinstance(v, str) and v.startswith("{ids_from:"):
                ref_api = v.strip("{}").split(":")[1]
                resolved[k] = self._prev_results.get(ref_api, [])
            else:
                resolved[k] = v
        return resolved
