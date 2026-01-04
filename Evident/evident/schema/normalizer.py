"""Normalizer for transforming raw data into unified security schema"""

from typing import Dict, Any, List, Union, Optional
from datetime import datetime
from evident.schema import (
    SecurityEntity, Vulnerability, Asset, User, Role, Permission,
    SecurityEvent, CloudResource, SignInLog, EntityType, Severity
)


class SecurityNormalizer:
    """Normalizes raw security data into unified schema"""
    
    def __init__(self):
        self.entity_count = 0
    
    def normalize(self, raw_data: Dict[str, Any], source_type: str) -> List[SecurityEntity]:
        """
        Normalize raw data based on source type
        
        Args:
            raw_data: Raw data dictionary or list
            source_type: Type of source (cves, assets, logs, etc.)
        
        Returns:
            List of normalized SecurityEntity objects
        """
        normalizer_map = {
            "cves": self._normalize_cve,
            "assets": self._normalize_asset,
            "logs": self._normalize_log_event,
            "cloud_configs": self._normalize_cloud_config,
            "signin_logs": self._normalize_signin_log,
            "user_roles": self._normalize_user_role,
            "role_permissions": self._normalize_role_permission,
        }
        
        normalizer = normalizer_map.get(source_type)
        if not normalizer:
            raise ValueError(f"Unknown source type: {source_type}")
        
        # Handle both single dict and list of dicts
        if isinstance(raw_data, list):
            entities = []
            for item in raw_data:
                entity = normalizer(item)
                if entity:
                    entities.extend(entity if isinstance(entity, list) else [entity])
            return entities
        else:
            result = normalizer(raw_data)
            return result if isinstance(result, list) else [result]
    
    def _normalize_cve(self, data: Dict[str, Any]) -> Vulnerability:
        """Normalize CVE data"""
        self.entity_count += 1
        
        # Parse severity
        severity_map = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
        }
        severity = severity_map.get(data.get("severity", "").lower(), Severity.MEDIUM)
        
        # Parse date
        published_date = self._parse_date(data.get("published_date"))
        
        return Vulnerability(
            id=f"vuln_{self.entity_count}",
            cve_id=data.get("cve_id", ""),
            severity=severity,
            cvss_score=float(data.get("cvss_score", 0.0)),
            description=data.get("description", ""),
            affected_products=self._parse_list(data.get("affected_products", "")),
            published_date=published_date,
            remediation_status=data.get("remediation_status", "open"),
            timestamp=published_date,
            metadata={"source": "cves"}
        )
    
    def _normalize_asset(self, data: Dict[str, Any]) -> Asset:
        """Normalize asset data"""
        self.entity_count += 1
        
        last_scan = self._parse_date(data.get("last_scan_date"))
        
        return Asset(
            id=f"asset_{self.entity_count}",
            asset_id=data.get("asset_id", ""),
            asset_type=data.get("asset_type", "unknown"),
            hostname=data.get("hostname", ""),
            ip_address=data.get("ip_address"),
            os=data.get("os"),
            owner=data.get("owner"),
            department=data.get("department"),
            criticality=data.get("criticality", "medium").lower(),
            last_scan_date=last_scan,
            timestamp=last_scan,
            metadata={"source": "assets"}
        )
    
    def _normalize_log_event(self, data: Dict[str, Any]) -> SecurityEvent:
        """Normalize log event data"""
        self.entity_count += 1
        
        severity_map = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
            "info": Severity.INFO,
        }
        severity = severity_map.get(data.get("severity", "").lower(), Severity.INFO)
        
        event_time = self._parse_date(data.get("timestamp"))
        
        return SecurityEvent(
            id=f"event_{self.entity_count}",
            event_id=data.get("event_id", ""),
            event_type=data.get("event_type", "unknown"),
            severity=severity,
            source=data.get("source", ""),
            user_id=data.get("user"),
            asset_id=data.get("asset_id"),
            description=data.get("description", ""),
            raw_log=data.get("raw_log"),
            timestamp=event_time,
            metadata={"source": "logs"}
        )
    
    def _normalize_cloud_config(self, data: Dict[str, Any]) -> CloudResource:
        """Normalize cloud configuration data"""
        self.entity_count += 1
        
        compliant = str(data.get("compliant", "true")).lower() in ["true", "yes", "1"]
        
        return CloudResource(
            id=f"cloud_{self.entity_count}",
            resource_id=data.get("resource_id", ""),
            cloud_provider=data.get("cloud_provider", "").lower(),
            resource_type=data.get("resource_type", ""),
            setting_name=data.get("setting_name", ""),
            setting_value=data.get("setting_value", ""),
            compliant=compliant,
            risk_level=data.get("risk_level", "low").lower(),
            timestamp=datetime.now(),
            metadata={"source": "cloud_configs", "config_id": data.get("config_id")}
        )
    
    def _normalize_signin_log(self, data: Dict[str, Any]) -> SignInLog:
        """Normalize sign-in log data"""
        self.entity_count += 1
        
        signin_time = self._parse_date(data.get("timestamp"))
        mfa_used = str(data.get("mfa_used", "false")).lower() in ["true", "yes", "1"]
        
        return SignInLog(
            id=f"signin_{self.entity_count}",
            log_id=data.get("log_id", ""),
            user_id=data.get("user_id", ""),
            username=data.get("username", ""),
            source_ip=data.get("source_ip", ""),
            location=data.get("location"),
            device=data.get("device"),
            status=data.get("status", "unknown"),
            mfa_used=mfa_used,
            risk_score=float(data.get("risk_score", 0.0)),
            timestamp=signin_time,
            metadata={"source": "signin_logs"}
        )
    
    def _normalize_user_role(self, data: Dict[str, Any]) -> List[Union[User, Role]]:
        """Normalize user role assignment - creates both User and Role entities"""
        entities = []
        
        # Create User entity
        self.entity_count += 1
        user = User(
            id=f"user_{data.get('user_id', self.entity_count)}",
            user_id=data.get("user_id", ""),
            username=data.get("username", ""),
            timestamp=self._parse_date(data.get("assigned_date")),
            metadata={"source": "user_roles", "assigned_by": data.get("assigned_by")}
        )
        entities.append(user)
        
        # Create Role entity
        self.entity_count += 1
        role = Role(
            id=f"role_{data.get('role_id', self.entity_count)}",
            role_id=data.get("role_id", ""),
            role_name=data.get("role_name", ""),
            timestamp=self._parse_date(data.get("assigned_date")),
            metadata={"source": "user_roles"}
        )
        entities.append(role)
        
        return entities
    
    def _normalize_role_permission(self, data: Dict[str, Any]) -> Permission:
        """Normalize role permission data"""
        self.entity_count += 1
        
        return Permission(
            id=f"perm_{self.entity_count}",
            permission_id=data.get("permission_id", ""),
            role_id=data.get("role_id", ""),
            resource_type=data.get("resource_type", ""),
            action=data.get("action", ""),
            scope=data.get("scope", ""),
            risk_level=data.get("risk_level", "medium").lower(),
            timestamp=datetime.now(),
            metadata={"source": "role_permissions", "role_name": data.get("role_name")}
        )
    
    def _parse_date(self, date_str: Any) -> Optional[datetime]:
        """Parse date string to datetime"""
        if not date_str:
            return None
        
        if isinstance(date_str, datetime):
            return date_str
        
        try:
            # Try common date formats
            for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]:
                try:
                    return datetime.strptime(str(date_str), fmt)
                except ValueError:
                    continue
            return None
        except:
            return None
    
    def _parse_list(self, value: Any) -> List[str]:
        """Parse comma-separated string or list"""
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return []
