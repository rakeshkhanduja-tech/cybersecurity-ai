"""CSV loaders for security data with recursive directory scanning"""

import os
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime
from evident.ingestion.base_source import BaseSource


class RecursiveCSVLoader(BaseSource):
    """Base class for loaders that need to scan directories recursively for CSV files"""
    
    def __init__(self, source_name: str, data_path: str):
        super().__init__(source_name)
        self.data_path = data_path
        
    def _find_all_csvs(self) -> List[str]:
        """Find all .csv files in data_path recursively"""
        csv_files = []
        if not os.path.exists(self.data_path):
            return []
            
        for root, _, files in os.walk(self.data_path):
            for file in files:
                if file.endswith(".csv"):
                    csv_files.append(os.path.join(root, file))
        return csv_files

    def load(self) -> List[Dict[str, Any]]:
        """Load data from all discovered CSVs"""
        self.metadata.status = "loading"
        all_data = []
        
        try:
            csv_files = self._find_all_csvs()
            
            if not csv_files:
                # If no files found, check if it's an error or just empty
                if not os.path.exists(self.data_path):
                    self.metadata.status = "error"
                else:
                    self.metadata.status = "loaded"
                return []
            
            for csv_file in csv_files:
                try:
                    # Robust loading: handle diverse encodings and skip bad lines
                    df = pd.read_csv(csv_file, encoding='utf-8', on_bad_lines='skip')
                    
                    # Filter out rows that are entirely empty or purely NaN
                    df = df.dropna(how='all')
                    
                    if not df.empty:
                        # Use to_dict('records') to get list of dicts
                        all_data.extend(df.to_dict('records'))
                except Exception as e:
                    # Check if file has at least a header (common for empty live files)
                    try:
                        with open(csv_file, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            if len(lines) <= 1: # Only header or empty
                                continue
                    except:
                        pass
                    print(f"  [ERROR] Failed to read {csv_file}: {e}")
            
            self.metadata.record_count = len(all_data)
            self.metadata.last_loaded = datetime.now().isoformat()
            self.metadata.status = "loaded"
            
            return all_data
        except Exception as e:
            self.metadata.status = "error"
            print(f"Error loading {self.source_name} data: {e}")
            return []


class CVELoader(RecursiveCSVLoader):
    """Loader for CVE vulnerability data"""
    def __init__(self, data_path: str = "./data/cves"):
        super().__init__("cves", data_path)
    
    def validate(self, data: Dict[str, Any]) -> bool:
        required_fields = ["cve_id", "severity", "cvss_score", "description"]
        return all(field in data for field in required_fields)
    
    def get_schema(self) -> Dict[str, str]:
        return {
            "cve_id": "str", "severity": "str", "cvss_score": "float",
            "description": "str", "affected_products": "str",
            "published_date": "str", "remediation_status": "str"
        }


class AssetLoader(RecursiveCSVLoader):
    """Loader for asset inventory data"""
    def __init__(self, data_path: str = "./data/assets"):
        super().__init__("assets", data_path)
    
    def validate(self, data: Dict[str, Any]) -> bool:
        required_fields = ["asset_id", "asset_type", "hostname"]
        return all(field in data for field in required_fields)
    
    def get_schema(self) -> Dict[str, str]:
        return {
            "asset_id": "str", "asset_type": "str", "hostname": "str",
            "ip_address": "str", "os": "str", "owner": "str",
            "department": "str", "criticality": "str", "last_scan_date": "str"
        }


class LogEventLoader(RecursiveCSVLoader):
    """Loader for security log events"""
    def __init__(self, data_path: str = "./data/logs"):
        super().__init__("logs", data_path)
    
    def validate(self, data: Dict[str, Any]) -> bool:
        required_fields = ["event_id", "timestamp", "event_type", "severity"]
        return all(field in data for field in required_fields)
    
    def get_schema(self) -> Dict[str, str]:
        return {
            "event_id": "str", "timestamp": "str", "source": "str",
            "event_type": "str", "severity": "str", "user": "str",
            "asset_id": "str", "description": "str", "raw_log": "str"
        }


class CloudConfigLoader(RecursiveCSVLoader):
    """Loader for cloud configuration data"""
    def __init__(self, data_path: str = "./data/cloud_configs"):
        super().__init__("cloud_configs", data_path)
    
    def validate(self, data: Dict[str, Any]) -> bool:
        required_fields = ["config_id", "cloud_provider", "resource_type"]
        return all(field in data for field in required_fields)
    
    def get_schema(self) -> Dict[str, str]:
        return {
            "config_id": "str", "cloud_provider": "str", "resource_type": "str",
            "resource_id": "str", "setting_name": "str", "setting_value": "str",
            "compliant": "str", "risk_level": "str"
        }


class SignInLogLoader(RecursiveCSVLoader):
    """Loader for sign-in logs"""
    def __init__(self, data_path: str = "./data/signin_logs"):
        super().__init__("signin_logs", data_path)
    
    def validate(self, data: Dict[str, Any]) -> bool:
        required_fields = ["log_id", "timestamp", "user_id", "username"]
        return all(field in data for field in required_fields)
    
    def get_schema(self) -> Dict[str, str]:
        return {
            "log_id": "str", "timestamp": "str", "user_id": "str",
            "username": "str", "source_ip": "str", "location": "str",
            "device": "str", "status": "str", "mfa_used": "str", "risk_score": "float"
        }


class UserRoleLoader(RecursiveCSVLoader):
    """Loader for user role assignments"""
    def __init__(self, data_path: str = "./data/user_roles"):
        super().__init__("user_roles", data_path)
    
    def validate(self, data: Dict[str, Any]) -> bool:
        required_fields = ["assignment_id", "user_id", "role_id"]
        return all(field in data for field in required_fields)
    
    def get_schema(self) -> Dict[str, str]:
        return {
            "assignment_id": "str", "user_id": "str", "username": "str",
            "role_id": "str", "role_name": "str", "assigned_date": "str",
            "assigned_by": "str", "expiry_date": "str"
        }


class RolePermissionLoader(RecursiveCSVLoader):
    """Loader for role permissions"""
    def __init__(self, data_path: str = "./data/role_permissions"):
        super().__init__("role_permissions", data_path)
    
    def validate(self, data: Dict[str, Any]) -> bool:
        required_fields = ["permission_id", "role_id", "resource_type", "action"]
        return all(field in data for field in required_fields)
    
    def get_schema(self) -> Dict[str, str]:
        return {
            "permission_id": "str", "role_id": "str", "role_name": "str",
            "resource_type": "str", "action": "str", "scope": "str",
            "risk_level": "str"
        }
