"""
evident_mapper.py — Maps raw API rows to Evident CSV schema columns.
Field paths like "behaviors[0].description" are resolved via deep_get.
"""
from __future__ import annotations

import re
from typing import Any


def map_evident(plug: dict, api_id: str, rows: list[dict]) -> list[dict]:
    """
    Returns a list of dicts with Evident column names as keys.
    The field_map comes from plug['source_mapping']['evident'][api_id].
    """
    source_mapping = plug.get("source_mapping", {}).get("evident", {})
    field_map = source_mapping.get(api_id)

    if not field_map:
        # No mapping defined — return rows as-is (flat)
        return [_flatten(row) for row in rows]

    mapped = []
    for row in rows:
        record = {}
        for dest_col, src_path in field_map.items():
            record[dest_col] = _deep_get(row, src_path)
        mapped.append(record)
    return mapped


# ── helpers ──────────────────────────────────────────────────────────────────

def _deep_get(obj: Any, path: str, default="") -> Any:
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


def _flatten(row: dict, prefix: str = "", sep: str = "_") -> dict:
    """Flatten nested dicts/lists to a single-level dict."""
    out = {}
    for k, v in row.items():
        key = f"{prefix}{sep}{k}" if prefix else k
        if isinstance(v, dict):
            out.update(_flatten(v, key, sep))
        elif isinstance(v, list):
            out[key] = str(v)
        else:
            out[key] = v
    return out
