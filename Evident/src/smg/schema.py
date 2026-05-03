"""Security graph schema and node/relationship definitions"""

from typing import Dict, Any, List
from enum import Enum


class NodeType(str, Enum):
    """Types of nodes in the security graph"""
    VULNERABILITY = "Vulnerability"
    ASSET = "Asset"
    USER = "User"
    ROLE = "Role"
    PERMISSION = "Permission"
    EVENT = "Event"
    CLOUD_RESOURCE = "CloudResource"


class RelationshipType(str, Enum):
    """Types of relationships in the security graph"""
    AFFECTS = "AFFECTS"  # Vulnerability -> Asset
    HAS_ROLE = "HAS_ROLE"  # User -> Role
    HAS_PERMISSION = "HAS_PERMISSION"  # Role -> Permission
    OWNS = "OWNS"  # User -> Asset
    LOGGED_ON = "LOGGED_ON"  # User -> Asset (from signin logs)
    TRIGGERED = "TRIGGERED"  # User -> Event
    INVOLVES = "INVOLVES"  # Event -> Asset
    MISCONFIGURED = "MISCONFIGURED"  # CloudResource -> Vulnerability
    ASSIGNED_TO = "ASSIGNED_TO"  # Permission -> Resource


class SecurityGraphSchema:
    """Schema definition for the security graph"""
    
    @staticmethod
    def get_node_properties(node_type: NodeType) -> List[str]:
        """Get required properties for a node type"""
        schemas = {
            NodeType.VULNERABILITY: ["cve_id", "severity", "cvss_score", "description"],
            NodeType.ASSET: ["asset_id", "hostname", "asset_type", "criticality"],
            NodeType.USER: ["user_id", "username"],
            NodeType.ROLE: ["role_id", "role_name"],
            NodeType.PERMISSION: ["permission_id", "action", "resource_type"],
            NodeType.EVENT: ["event_id", "event_type", "severity"],
            NodeType.CLOUD_RESOURCE: ["resource_id", "cloud_provider", "resource_type"],
        }
        return schemas.get(node_type, [])
    
    @staticmethod
    def get_relationship_rules() -> Dict[str, Dict[str, Any]]:
        """Get rules for creating relationships"""
        return {
            RelationshipType.AFFECTS: {
                "from": NodeType.VULNERABILITY,
                "to": NodeType.ASSET,
                "properties": ["confidence"]
            },
            RelationshipType.HAS_ROLE: {
                "from": NodeType.USER,
                "to": NodeType.ROLE,
                "properties": ["assigned_date", "assigned_by"]
            },
            RelationshipType.HAS_PERMISSION: {
                "from": NodeType.ROLE,
                "to": NodeType.PERMISSION,
                "properties": ["scope"]
            },
            RelationshipType.OWNS: {
                "from": NodeType.USER,
                "to": NodeType.ASSET,
                "properties": ["department"]
            },
            RelationshipType.LOGGED_ON: {
                "from": NodeType.USER,
                "to": NodeType.ASSET,
                "properties": ["timestamp", "source_ip", "status"]
            },
            RelationshipType.TRIGGERED: {
                "from": NodeType.USER,
                "to": NodeType.EVENT,
                "properties": ["timestamp"]
            },
            RelationshipType.INVOLVES: {
                "from": NodeType.EVENT,
                "to": NodeType.ASSET,
                "properties": ["timestamp"]
            },
        }
