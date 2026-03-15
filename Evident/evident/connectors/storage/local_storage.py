"""
local_storage.py — Writes connector output to local CSV files.

Path pattern:
  data/livedata/<source>/<MMDDYYYY>/<HH>/5M_<GUID>.csv
"""
from __future__ import annotations

import csv
import io
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path


# Resolve to git root/Evident/evident/data/livedata/dataplugs_singnals
# __file__ is c:\PRODDEV\personal\cybersecurity-ai\Evident\evident\connectors\storage\local_storage.py
_PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
_BASE_PATH = _PROJECT_ROOT / "Evident" / "evident" / "data" / "livedata" / "dataplugs_singnals"


class LocalStorage:
    def __init__(self, cfg: dict):
        self.base = Path(cfg.get("base_path", str(_BASE_PATH)))

    def write(
        self,
        connector_id: str,
        api_id: str,
        schema: str,
        source_name: str,
        rows: list[dict],
    ) -> str:
        """Write rows to CSV and return the file path."""
        if not rows:
            return ""

        now = datetime.now(tz=timezone.utc)
        date_str = now.strftime("%m%d%Y")
        hour_str = now.strftime("%H")
        guid     = uuid.uuid4().hex[:12].upper()

        dest_dir = self.base / source_name / date_str / hour_str
        dest_dir.mkdir(parents=True, exist_ok=True)

        file_path = dest_dir / f"5M_{guid}.csv"

        fieldnames = list(rows[0].keys())
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

        return str(file_path)
