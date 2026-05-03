"""Build graph relationships from OCSF entities."""

from typing import Dict, Any, List
from src.schema.ocsf_schema import OCSFEntity

class OCSFRelationshipBuilder:
    """Builds relationships tying main events to nested objects like Devices, Users."""
    
    def __init__(self):
        self.relationships = []
        
    def build_relationships(self, entities: List[OCSFEntity]) -> List[Dict[str, Any]]:
        rels = []
        
        for entity in entities:
            event_id = str(entity.id)
            
            # Device relationship
            device = entity.get_property("device")
            if device:
                dev_id = str(device.get("uid") or device.get("hostname") or "unknown_device")
                rels.append({
                    "start_node_id": event_id,
                    "end_node_id": dev_id,
                    "type": "AFFECTS_DEVICE",
                    "properties": {}
                })
                
            # Actor/User relationship
            user = entity.get_property("actor.user") or entity.get_property("user")
            if user and isinstance(user, dict):
                user_id = str(user.get("uid") or user.get("email_addr") or user.get("name") or "unknown_user")
                rels.append({
                    "start_node_id": user_id,
                    "end_node_id": event_id,
                    "type": "INITIATED",
                    "properties": {}
                })

        # Deduplicate
        unique_rels = []
        seen = set()
        for r in rels:
            k = f"{r['start_node_id']}-{r['type']}-{r['end_node_id']}"
            if k not in seen:
                seen.add(k)
                unique_rels.append(r)
                
        self.relationships.extend(unique_rels)
        return unique_rels
        
    def get_relationship_count(self) -> int:
        return len(self.relationships)
