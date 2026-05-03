"""
ocsf_mapper.py — Maps raw API rows to OCSF (Open Cybersecurity Schema Framework) format.
Classes and field names follow OCSF v1.1.
"""
from __future__ import annotations

import re
from typing import Any


def map_ocsf(plug: dict, api_id: str, rows: list[dict]) -> list[dict]:
    """
    Returns a list of dicts with OCSF field names as keys.
    Source mapping comes from plug['source_mapping']['ocsf'].
    """
    ocsf_cfg = plug.get("source_mapping", {}).get("ocsf", {})
    field_map = ocsf_cfg.get("field_map", {})
    class_uid  = ocsf_cfg.get("class_uid", 0)
    class_name = ocsf_cfg.get("class_name", "Unknown")

    if not field_map:
        return rows  # no mapping defined

    mapped = []
    for row in rows:
        record: dict = {
            "class_uid":  class_uid,
            "class_name": class_name,
            "type_uid":   class_uid * 100 + 1,  # OCSF type_uid convention
        }
        for ocsf_field, src_path in field_map.items():
            record[ocsf_field] = _deep_get(row, src_path)
        mapped.append(record)

    return mapped


# ── helpers ──────────────────────────────────────────────────────────────────

def _deep_get(obj: Any, path: str, default="") -> Any:
    if not isinstance(path, str):
        return path   # literal value (e.g. "AWS", 1)
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
