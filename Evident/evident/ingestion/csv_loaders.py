"""CSV loaders for sample security data"""

import os
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime
from evident.ingestion.base_source import BaseSource


class CVELoader(BaseSource):
    """Loader for CVE vulnerability data"""
    
    def __init__(self, data_path: str = "./data/cves"):
        super().__init__("cves")
        self.data_path = data_path
        self.csv_file = os.path.join(data_path, "cves.csv")
    
    def load(self) -> List[Dict[str, Any]]:
        """Load CVE data from CSV"""
        self.metadata.status = "loading"
        
        try:
            if not os.path.exists(self.csv_file):
                self.metadata.status = "error"
                return []
            
            df = pd.read_csv(self.csv_file)
            data = df.to_dict('records')
            
            self.metadata.record_count = len(data)
            self.metadata.last_loaded = datetime.now().isoformat()
            self.metadata.status = "loaded"
            
            return data
        except Exception as e:
            self.metadata.status = "error"
            print(f"Error loading CVE data: {e}")
            return []
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate CVE record"""
        required_fields = ["cve_id", "severity", "cvss_score", "description"]
        return all(field in data for field in required_fields)
    
    def get_schema(self) -> Dict[str, str]:
        """Get CVE schema"""
        return {
            "cve_id": "str",
            "severity": "str",
            "cvss_score": "float",
            "description": "str",
            "affected_products": "str",
            "published_date": "str",
            "remediation_status": "str"
        }


class AssetLoader(BaseSource):
    """Loader for asset inventory data"""
    
    def __init__(self, data_path: str = "./data/assets"):
        super().__init__("assets")
        self.data_path = data_path
        self.csv_file = os.path.join(data_path, "assets.csv")
    
    def load(self) -> List[Dict[str, Any]]:
        """Load asset data from CSV"""
        self.metadata.status = "loading"
        
        try:
            if not os.path.exists(self.csv_file):
                self.metadata.status = "error"
                return []
            
            df = pd.read_csv(self.csv_file)
            data = df.to_dict('records')
            
            self.metadata.record_count = len(data)
            self.metadata.last_loaded = datetime.now().isoformat()
            self.metadata.status = "loaded"
            
            return data
        except Exception as e:
            self.metadata.status = "error"
            print(f"Error loading asset data: {e}")
            return []
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate asset record"""
        required_fields = ["asset_id", "asset_type", "hostname"]
        return all(field in data for field in required_fields)
    
    def get_schema(self) -> Dict[str, str]:
        """Get asset schema"""
        return {
            "asset_id": "str",
            "asset_type": "str",
            "hostname": "str",
            "ip_address": "str",
            "os": "str",
            "owner": "str",
            "department": "str",
            "criticality": "str",
            "last_scan_date": "str"
        }


class LogEventLoader(BaseSource):
    """Loader for security log events"""
    
    def __init__(self, data_path: str = "./data/logs"):
        super().__init__("logs")
        self.data_path = data_path
        self.csv_file = os.path.join(data_path, "log_events.csv")
    
    def load(self) -> List[Dict[str, Any]]:
        """Load log event data from CSV"""
        self.metadata.status = "loading"
        
        try:
            if not os.path.exists(self.csv_file):
                self.metadata.status = "error"
                return []
            
            df = pd.read_csv(self.csv_file)
            data = df.to_dict('records')
            
            self.metadata.record_count = len(data)
            self.metadata.last_loaded = datetime.now().isoformat()
            self.metadata.status = "loaded"
            
            return data
        except Exception as e:
            self.metadata.status = "error"
            print(f"Error loading log event data: {e}")
            return []
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate log event record"""
        required_fields = ["event_id", "timestamp", "event_type", "severity"]
        return all(field in data for field in required_fields)
    
    def get_schema(self) -> Dict[str, str]:
        """Get log event schema"""
        return {
            "event_id": "str",
            "timestamp": "str",
            "source": "str",
            "event_type": "str",
            "severity": "str",
            "user": "str",
            "asset_id": "str",
            "description": "str",
            "raw_log": "str"
        }


class CloudConfigLoader(BaseSource):
    """Loader for cloud configuration data"""
    
    def __init__(self, data_path: str = "./data/cloud_configs"):
        super().__init__("cloud_configs")
        self.data_path = data_path
        self.csv_file = os.path.join(data_path, "cloud_configs.csv")
    
    def load(self) -> List[Dict[str, Any]]:
        """Load cloud config data from CSV"""
        self.metadata.status = "loading"
        
        try:
            if not os.path.exists(self.csv_file):
                self.metadata.status = "error"
                return []
            
            df = pd.read_csv(self.csv_file)
            data = df.to_dict('records')
            
            self.metadata.record_count = len(data)
            self.metadata.last_loaded = datetime.now().isoformat()
            self.metadata.status = "loaded"
            
            return data
        except Exception as e:
            self.metadata.status = "error"
            print(f"Error loading cloud config data: {e}")
            return []
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate cloud config record"""
        required_fields = ["config_id", "cloud_provider", "resource_type"]
        return all(field in data for field in required_fields)
    
    def get_schema(self) -> Dict[str, str]:
        """Get cloud config schema"""
        return {
            "config_id": "str",
            "cloud_provider": "str",
            "resource_type": "str",
            "resource_id": "str",
            "setting_name": "str",
            "setting_value": "str",
            "compliant": "str",
            "risk_level": "str"
        }


class SignInLogLoader(BaseSource):
    """Loader for sign-in logs"""
    
    def __init__(self, data_path: str = "./data/signin_logs"):
        super().__init__("signin_logs")
        self.data_path = data_path
        self.csv_file = os.path.join(data_path, "signin_logs.csv")
    
    def load(self) -> List[Dict[str, Any]]:
        """Load sign-in log data from CSV"""
        self.metadata.status = "loading"
        
        try:
            if not os.path.exists(self.csv_file):
                self.metadata.status = "error"
                return []
            
            df = pd.read_csv(self.csv_file)
            data = df.to_dict('records')
            
            self.metadata.record_count = len(data)
            self.metadata.last_loaded = datetime.now().isoformat()
            self.metadata.status = "loaded"
            
            return data
        except Exception as e:
            self.metadata.status = "error"
            print(f"Error loading sign-in log data: {e}")
            return []
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate sign-in log record"""
        required_fields = ["log_id", "timestamp", "user_id", "username"]
        return all(field in data for field in required_fields)
    
    def get_schema(self) -> Dict[str, str]:
        """Get sign-in log schema"""
        return {
            "log_id": "str",
            "timestamp": "str",
            "user_id": "str",
            "username": "str",
            "source_ip": "str",
            "location": "str",
            "device": "str",
            "status": "str",
            "mfa_used": "str",
            "risk_score": "float"
        }


class UserRoleLoader(BaseSource):
    """Loader for user role assignments"""
    
    def __init__(self, data_path: str = "./data/user_roles"):
        super().__init__("user_roles")
        self.data_path = data_path
        self.csv_file = os.path.join(data_path, "user_roles.csv")
    
    def load(self) -> List[Dict[str, Any]]:
        """Load user role data from CSV"""
        self.metadata.status = "loading"
        
        try:
            if not os.path.exists(self.csv_file):
                self.metadata.status = "error"
                return []
            
            df = pd.read_csv(self.csv_file)
            data = df.to_dict('records')
            
            self.metadata.record_count = len(data)
            self.metadata.last_loaded = datetime.now().isoformat()
            self.metadata.status = "loaded"
            
            return data
        except Exception as e:
            self.metadata.status = "error"
            print(f"Error loading user role data: {e}")
            return []
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate user role record"""
        required_fields = ["assignment_id", "user_id", "role_id"]
        return all(field in data for field in required_fields)
    
    def get_schema(self) -> Dict[str, str]:
        """Get user role schema"""
        return {
            "assignment_id": "str",
            "user_id": "str",
            "username": "str",
            "role_id": "str",
            "role_name": "str",
            "assigned_date": "str",
            "assigned_by": "str",
            "expiry_date": "str"
        }


class RolePermissionLoader(BaseSource):
    """Loader for role permissions"""
    
    def __init__(self, data_path: str = "./data/role_permissions"):
        super().__init__("role_permissions")
        self.data_path = data_path
        self.csv_file = os.path.join(data_path, "role_permissions.csv")
    
    def load(self) -> List[Dict[str, Any]]:
        """Load role permission data from CSV"""
        self.metadata.status = "loading"
        
        try:
            if not os.path.exists(self.csv_file):
                self.metadata.status = "error"
                return []
            
            df = pd.read_csv(self.csv_file)
            data = df.to_dict('records')
            
            self.metadata.record_count = len(data)
            self.metadata.last_loaded = datetime.now().isoformat()
            self.metadata.status = "loaded"
            
            return data
        except Exception as e:
            self.metadata.status = "error"
            print(f"Error loading role permission data: {e}")
            return []
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate role permission record"""
        required_fields = ["permission_id", "role_id", "resource_type", "action"]
        return all(field in data for field in required_fields)
    
    def get_schema(self) -> Dict[str, str]:
        """Get role permission schema"""
        return {
            "permission_id": "str",
            "role_id": "str",
            "role_name": "str",
            "resource_type": "str",
            "action": "str",
            "scope": "str",
            "risk_level": "str"
        }
