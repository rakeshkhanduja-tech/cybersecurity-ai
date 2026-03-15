"""
mapper/__init__.py — entry point for schema mapping.
Dispatches to evident_mapper or ocsf_mapper based on the schema param.
"""
from __future__ import annotations

from evident.connectors.mapper.evident_mapper import map_evident
from evident.connectors.mapper.ocsf_mapper import map_ocsf


def map_rows(plug: dict, api_id: str, rows: list[dict], schema: str) -> list[dict]:
    """
    Map raw API rows to the requested schema.

    plug    — full plug JSON dict (contains source_mapping)
    api_id  — e.g. 'detections', 'users'
    rows    — raw API response list
    schema  — 'evident' | 'ocsf'
    """
    schema = schema.lower()
    if schema == "ocsf":
        return map_ocsf(plug, api_id, rows)
    return map_evident(plug, api_id, rows)
