"""Security schema definitions for normalized data"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class EntityType(str, Enum):
    """Types of security entities"""
    VULNERABILITY = "vulnerability"
    ASSET = "asset"
    USER = "user"
    ROLE = "role"
    PERMISSION = "permission"
    EVENT = "event"
    CLOUD_RESOURCE = "cloud_resource"


class Severity(str, Enum):
    """Severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class SecurityEntity(BaseModel):
    """Base class for all security entities"""
    id: str
    entity_type: EntityType
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Vulnerability(SecurityEntity):
    """Normalized CVE/vulnerability data"""
    entity_type: EntityType = EntityType.VULNERABILITY
    cve_id: str
    severity: Severity
    cvss_score: float
    description: str
    affected_products: List[str] = Field(default_factory=list)
    published_date: Optional[datetime] = None
    remediation_status: str = "open"
    remediation_steps: Optional[str] = None


class Asset(SecurityEntity):
    """Normalized asset data"""
    entity_type: EntityType = EntityType.ASSET
    asset_id: str
    asset_type: str  # server, workstation, database, network_device, etc.
    hostname: str
    ip_address: Optional[str] = None
    os: Optional[str] = None
    owner: Optional[str] = None
    department: Optional[str] = None
    criticality: str = "medium"  # critical, high, medium, low
    last_scan_date: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)


class User(SecurityEntity):
    """Normalized user data"""
    entity_type: EntityType = EntityType.USER
    user_id: str
    username: str
    email: Optional[str] = None
    department: Optional[str] = None
    is_active: bool = True
    risk_score: float = 0.0


class Role(SecurityEntity):
    """Normalized role data"""
    entity_type: EntityType = EntityType.ROLE
    role_id: str
    role_name: str
    description: Optional[str] = None
    risk_level: str = "medium"


class Permission(SecurityEntity):
    """Normalized permission data"""
    entity_type: EntityType = EntityType.PERMISSION
    permission_id: str
    role_id: str
    resource_type: str
    action: str  # read, write, execute, admin, etc.
    scope: str  # global, department, personal, etc.
    risk_level: str = "medium"


class SecurityEvent(SecurityEntity):
    """Normalized security event/log data"""
    entity_type: EntityType = EntityType.EVENT
    event_id: str
    event_type: str  # login, logout, file_access, privilege_escalation, etc.
    severity: Severity
    source: str
    user_id: Optional[str] = None
    asset_id: Optional[str] = None
    description: str
    raw_log: Optional[str] = None
    indicators: Dict[str, Any] = Field(default_factory=dict)


class CloudResource(SecurityEntity):
    """Normalized cloud configuration data"""
    entity_type: EntityType = EntityType.CLOUD_RESOURCE
    resource_id: str
    cloud_provider: str  # aws, azure, gcp, etc.
    resource_type: str  # s3_bucket, vm, database, etc.
    setting_name: str
    setting_value: str
    compliant: bool = True
    risk_level: str = "low"
    recommendation: Optional[str] = None


class SignInLog(SecurityEntity):
    """Normalized sign-in log data"""
    entity_type: EntityType = EntityType.EVENT
    log_id: str
    user_id: str
    username: str
    source_ip: str
    location: Optional[str] = None
    device: Optional[str] = None
    status: str  # success, failed, blocked
    mfa_used: bool = False
    risk_score: float = 0.0
    failure_reason: Optional[str] = None


# Type mapping for entity creation
ENTITY_TYPE_MAP = {
    EntityType.VULNERABILITY: Vulnerability,
    EntityType.ASSET: Asset,
    EntityType.USER: User,
    EntityType.ROLE: Role,
    EntityType.PERMISSION: Permission,
    EntityType.EVENT: SecurityEvent,
    EntityType.CLOUD_RESOURCE: CloudResource,
}
