"""Build graph nodes from security entities"""

from typing import Dict, Any, List
from evident.schema import SecurityEntity, EntityType
from evident.smg.schema import NodeType


class SecurityNodeBuilder:
    """Builds graph nodes from normalized security entities"""
    
    def __init__(self):
        self.nodes = {}  # Dictionary to track nodes by ID
    
    def build_nodes(self, entities: List[SecurityEntity]) -> List[Dict[str, Any]]:
        """
        Build graph nodes from security entities
        
        Args:
            entities: List of SecurityEntity objects
        
        Returns:
            List of node dictionaries
        """
        nodes = []
        
        for entity in entities:
            node = self._entity_to_node(entity)
            if node:
                # Avoid duplicates
                node_key = f"{node['label']}:{node['properties'].get('id', node['properties'].get('name'))}"
                if node_key not in self.nodes:
                    self.nodes[node_key] = node
                    nodes.append(node)
        
        return nodes
    
    def _entity_to_node(self, entity: SecurityEntity) -> Dict[str, Any]:
        """Convert security entity to graph node"""
        
        if entity.entity_type == EntityType.VULNERABILITY:
            return {
                "label": NodeType.VULNERABILITY.value,
                "properties": {
                    "id": entity.id,
                    "cve_id": entity.cve_id,
                    "severity": entity.severity.value,
                    "cvss_score": entity.cvss_score,
                    "description": entity.description[:200],  # Truncate for graph storage
                    "remediation_status": entity.remediation_status,
                    "affected_products": ",".join(entity.affected_products) if entity.affected_products else ""
                }
            }
        
        elif entity.entity_type == EntityType.ASSET:
            return {
                "label": NodeType.ASSET.value,
                "properties": {
                    "id": entity.id,
                    "asset_id": entity.asset_id,
                    "hostname": entity.hostname,
                    "asset_type": entity.asset_type,
                    "ip_address": entity.ip_address or "",
                    "os": entity.os or "",
                    "owner": entity.owner or "",
                    "department": entity.department or "",
                    "criticality": entity.criticality
                }
            }
        
        elif entity.entity_type == EntityType.USER:
            return {
                "label": NodeType.USER.value,
                "properties": {
                    "id": entity.id,
                    "user_id": entity.user_id,
                    "username": entity.username,
                    "email": entity.email or "",
                    "department": entity.department or "",
                    "is_active": str(entity.is_active),
                    "risk_score": entity.risk_score
                }
            }
        
        elif entity.entity_type == EntityType.ROLE:
            return {
                "label": NodeType.ROLE.value,
                "properties": {
                    "id": entity.id,
                    "role_id": entity.role_id,
                    "role_name": entity.role_name,
                    "description": entity.description or "",
                    "risk_level": entity.risk_level
                }
            }
        
        elif entity.entity_type == EntityType.PERMISSION:
            return {
                "label": NodeType.PERMISSION.value,
                "properties": {
                    "id": entity.id,
                    "permission_id": entity.permission_id,
                    "role_id": entity.role_id,
                    "resource_type": entity.resource_type,
                    "action": entity.action,
                    "scope": entity.scope,
                    "risk_level": entity.risk_level
                }
            }
        
        elif entity.entity_type == EntityType.EVENT:
            # Check if it's a SignInLog or SecurityEvent
            if hasattr(entity, 'log_id'):
                # SignInLog
                return {
                    "label": NodeType.EVENT.value,
                    "properties": {
                        "id": entity.id,
                        "event_id": entity.log_id,
                        "event_type": "signin",
                        "severity": "info",
                        "source": "signin_logs",
                        "description": f"Sign-in by {entity.username} from {entity.source_ip}",
                        "user_id": entity.user_id,
                        "asset_id": "",
                        "timestamp": str(entity.timestamp) if entity.timestamp else "",
                        "status": entity.status,
                        "risk_score": entity.risk_score
                    }
                }
            else:
                # SecurityEvent
                return {
                    "label": NodeType.EVENT.value,
                    "properties": {
                        "id": entity.id,
                        "event_id": entity.event_id,
                        "event_type": entity.event_type,
                        "severity": entity.severity.value,
                        "source": entity.source,
                        "description": entity.description[:200],
                        "user_id": entity.user_id or "",
                        "asset_id": entity.asset_id or "",
                        "timestamp": str(entity.timestamp) if entity.timestamp else ""
                    }
                }
        
        elif entity.entity_type == EntityType.CLOUD_RESOURCE:
            return {
                "label": NodeType.CLOUD_RESOURCE.value,
                "properties": {
                    "id": entity.id,
                    "resource_id": entity.resource_id,
                    "cloud_provider": entity.cloud_provider,
                    "resource_type": entity.resource_type,
                    "setting_name": entity.setting_name,
                    "setting_value": entity.setting_value,
                    "compliant": str(entity.compliant),
                    "risk_level": entity.risk_level
                }
            }
        
        return None
    
    def get_node_count(self) -> int:
        """Get total number of unique nodes"""
        return len(self.nodes)
