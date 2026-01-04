"""Build relationships between security entities"""

from typing import Dict, Any, List
from evident.schema import SecurityEntity, EntityType
from evident.smg.schema import RelationshipType, NodeType


class SecurityRelationshipBuilder:
    """Builds relationships between security graph nodes"""
    
    def __init__(self):
        self.relationships = []
        self.entity_map = {}  # Map entity IDs to entities for lookup
    
    def build_relationships(self, entities: List[SecurityEntity]) -> List[Dict[str, Any]]:
        """
        Build relationships from security entities
        
        Args:
            entities: List of SecurityEntity objects
        
        Returns:
            List of relationship dictionaries
        """
        # Build entity map for quick lookup
        self.entity_map = {entity.id: entity for entity in entities}
        
        relationships = []
        
        # Build different types of relationships
        relationships.extend(self._build_vulnerability_relationships(entities))
        relationships.extend(self._build_user_role_relationships(entities))
        relationships.extend(self._build_role_permission_relationships(entities))
        relationships.extend(self._build_asset_ownership_relationships(entities))
        relationships.extend(self._build_event_relationships(entities))
        relationships.extend(self._build_signin_relationships(entities))
        
        self.relationships = relationships
        return relationships
    
    def _build_vulnerability_relationships(self, entities: List[SecurityEntity]) -> List[Dict[str, Any]]:
        """Build AFFECTS relationships between vulnerabilities and assets"""
        relationships = []
        
        vulnerabilities = [e for e in entities if e.entity_type == EntityType.VULNERABILITY]
        assets = [e for e in entities if e.entity_type == EntityType.ASSET]
        
        for vuln in vulnerabilities:
            for asset in assets:
                # Match vulnerability to asset based on affected products
                if self._vulnerability_affects_asset(vuln, asset):
                    relationships.append({
                        "type": RelationshipType.AFFECTS.value,
                        "from_id": vuln.id,
                        "from_label": NodeType.VULNERABILITY.value,
                        "to_id": asset.id,
                        "to_label": NodeType.ASSET.value,
                        "properties": {
                            "confidence": 0.8,  # Confidence score
                            "cve_id": vuln.cve_id,
                            "severity": vuln.severity.value
                        }
                    })
        
        return relationships
    
    def _build_user_role_relationships(self, entities: List[SecurityEntity]) -> List[Dict[str, Any]]:
        """Build HAS_ROLE relationships between users and roles"""
        relationships = []
        
        users = [e for e in entities if e.entity_type == EntityType.USER]
        roles = [e for e in entities if e.entity_type == EntityType.ROLE]
        
        # Create user-role mapping from metadata
        for user in users:
            # Check if user has role information in metadata
            source = user.metadata.get("source", "")
            if source == "user_roles":
                # Find matching role
                for role in roles:
                    # Match based on metadata or IDs
                    if self._user_has_role(user, role):
                        relationships.append({
                            "type": RelationshipType.HAS_ROLE.value,
                            "from_id": user.id,
                            "from_label": NodeType.USER.value,
                            "to_id": role.id,
                            "to_label": NodeType.ROLE.value,
                            "properties": {
                                "assigned_date": str(user.timestamp) if user.timestamp else "",
                                "assigned_by": user.metadata.get("assigned_by", "")
                            }
                        })
        
        return relationships
    
    def _build_role_permission_relationships(self, entities: List[SecurityEntity]) -> List[Dict[str, Any]]:
        """Build HAS_PERMISSION relationships between roles and permissions"""
        relationships = []
        
        roles = [e for e in entities if e.entity_type == EntityType.ROLE]
        permissions = [e for e in entities if e.entity_type == EntityType.PERMISSION]
        
        for perm in permissions:
            # Find role that has this permission
            for role in roles:
                if perm.role_id == role.role_id:
                    relationships.append({
                        "type": RelationshipType.HAS_PERMISSION.value,
                        "from_id": role.id,
                        "from_label": NodeType.ROLE.value,
                        "to_id": perm.id,
                        "to_label": NodeType.PERMISSION.value,
                        "properties": {
                            "scope": perm.scope,
                            "risk_level": perm.risk_level
                        }
                    })
        
        return relationships
    
    def _build_asset_ownership_relationships(self, entities: List[SecurityEntity]) -> List[Dict[str, Any]]:
        """Build OWNS relationships between users and assets"""
        relationships = []
        
        users = [e for e in entities if e.entity_type == EntityType.USER]
        assets = [e for e in entities if e.entity_type == EntityType.ASSET]
        
        for asset in assets:
            if asset.owner:
                # Find user with matching username
                for user in users:
                    if user.username == asset.owner:
                        relationships.append({
                            "type": RelationshipType.OWNS.value,
                            "from_id": user.id,
                            "from_label": NodeType.USER.value,
                            "to_id": asset.id,
                            "to_label": NodeType.ASSET.value,
                            "properties": {
                                "department": asset.department or ""
                            }
                        })
        
        return relationships
    
    def _build_event_relationships(self, entities: List[SecurityEntity]) -> List[Dict[str, Any]]:
        """Build TRIGGERED and INVOLVES relationships for events"""
        relationships = []
        
        events = [e for e in entities if e.entity_type == EntityType.EVENT]
        users = [e for e in entities if e.entity_type == EntityType.USER]
        assets = [e for e in entities if e.entity_type == EntityType.ASSET]
        
        for event in events:
            # TRIGGERED relationship (User -> Event)
            if hasattr(event, 'user_id') and event.user_id:
                for user in users:
                    if user.user_id == event.user_id or user.username == event.user_id:
                        relationships.append({
                            "type": RelationshipType.TRIGGERED.value,
                            "from_id": user.id,
                            "from_label": NodeType.USER.value,
                            "to_id": event.id,
                            "to_label": NodeType.EVENT.value,
                            "properties": {
                                "timestamp": str(event.timestamp) if event.timestamp else ""
                            }
                        })
            
            # INVOLVES relationship (Event -> Asset)
            # Only for SecurityEvent, not SignInLog
            if hasattr(event, 'asset_id') and event.asset_id:
                for asset in assets:
                    if asset.asset_id == event.asset_id:
                        relationships.append({
                            "type": RelationshipType.INVOLVES.value,
                            "from_id": event.id,
                            "from_label": NodeType.EVENT.value,
                            "to_id": asset.id,
                            "to_label": NodeType.ASSET.value,
                            "properties": {
                                "timestamp": str(event.timestamp) if event.timestamp else "",
                                "event_type": event.event_type
                            }
                        })
        
        return relationships
    
    def _build_signin_relationships(self, entities: List[SecurityEntity]) -> List[Dict[str, Any]]:
        """Build LOGGED_ON relationships from signin logs"""
        relationships = []
        
        # Signin logs are stored as EVENT entities with specific metadata
        signin_events = [e for e in entities if e.entity_type == EntityType.EVENT and 
                        e.metadata.get("source") == "signin_logs"]
        users = [e for e in entities if e.entity_type == EntityType.USER]
        assets = [e for e in entities if e.entity_type == EntityType.ASSET]
        
        for signin in signin_events:
            # Find user
            user_id = signin.user_id
            if user_id:
                for user in users:
                    if user.user_id == user_id or user.username == user_id:
                        # For successful logins, we might infer asset from IP or other data
                        # This is a simplified version
                        relationships.append({
                            "type": "SIGNED_IN",
                            "from_id": user.id,
                            "from_label": NodeType.USER.value,
                            "to_id": signin.id,
                            "to_label": NodeType.EVENT.value,
                            "properties": {
                                "timestamp": str(signin.timestamp) if signin.timestamp else "",
                                "status": signin.metadata.get("status", "")
                            }
                        })
        
        return relationships
    
    def _vulnerability_affects_asset(self, vuln, asset) -> bool:
        """Determine if a vulnerability affects an asset"""
        if not vuln.affected_products:
            return False
        
        # Check if asset OS or type matches affected products
        asset_info = f"{asset.os} {asset.asset_type}".lower()
        
        for product in vuln.affected_products:
            product_lower = product.lower()
            if any(keyword in asset_info for keyword in product_lower.split()):
                return True
        
        return False
    
    def _user_has_role(self, user, role) -> bool:
        """Determine if a user has a specific role"""
        # This is simplified - in real implementation, would use proper ID matching
        # For now, check if user and role were created from same source
        return (user.metadata.get("source") == "user_roles" and 
                role.metadata.get("source") == "user_roles")
    
    def get_relationship_count(self) -> int:
        """Get total number of relationships"""
        return len(self.relationships)
