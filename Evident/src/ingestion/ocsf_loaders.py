"""Loaders for OCSF sample data in JSON format"""

import json
import os
import glob
from typing import Dict, Any, List
from datetime import datetime
from src.ingestion.base_source import BaseSource

class OCSFJSONLoader(BaseSource):
    """Loads OCSF structured JSON files from a directory."""
    
    def __init__(self, data_dir: str, source_name: str):
        super().__init__(source_name)
        self.data_dir = data_dir
        
    def load(self) -> List[Dict[str, Any]]:
        self.metadata.status = "loading"
        all_records = []
        
        if not os.path.exists(self.data_dir):
            print(f"  [WARN] OCSF Data directory not found: {self.data_dir}")
            self.metadata.status = "error"
            return []
            
        json_files = glob.glob(os.path.join(self.data_dir, "*.json"))
        # Also check for ndjson or jsonl if they exist
        json_files.extend(glob.glob(os.path.join(self.data_dir, "*.jsonl")))
        
        if not json_files:
            print(f"  [WARN] No JSON files found in {self.data_dir}")
            
        for file_path in json_files:
            try:
                # Handle jsonl
                if file_path.endswith('.jsonl'):
                    with open(file_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                all_records.append(json.loads(line))
                    continue
            
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    if isinstance(data, list):
                        all_records.extend(data)
                    elif isinstance(data, dict):
                        # Detect array payloads
                        if "data" in data and isinstance(data["data"], list):
                            all_records.extend(data["data"])
                        elif "records" in data and isinstance(data["records"], list):
                            all_records.extend(data["records"])
                        else:
                            all_records.append(data)
                            
            except Exception as e:
                print(f"  [ERROR] Failed to load {file_path}: {e}")
                
        self.metadata.record_count = len(all_records)
        self.metadata.last_loaded = datetime.now().isoformat()
        self.metadata.status = "loaded"
        
        return all_records

    def validate(self, data: Dict[str, Any]) -> bool:
        return isinstance(data, dict)
        
    def get_schema(self) -> Dict[str, str]:
        return {"*": "Any"}
