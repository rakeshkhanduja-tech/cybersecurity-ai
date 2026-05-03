"""Base definitions for OCSF entities."""

from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class OCSFEntity(BaseModel):
    """A generic wrapper for any OCSF-format event/finding."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    class_name: str
    class_uid: int
    activity_id: int = 0
    time: Optional[datetime] = None
    severity: Optional[str] = None
    raw_data: Dict[str, Any]
    
    # Track the metadata for embedding or graphs
    metadata: Dict[str, Any] = {}
    
    @property
    def id(self) -> str:
        """Derive a stable ID from metadata or uid in raw_data."""
        uid = self.metadata.get("id") or self.raw_data.get("uid") or self.raw_data.get("id", f"ocsf_{self.class_uid}")
        return str(uid)
    
    @property
    def entity_type(self) -> str:
        """Expose entity_type as class_name for API compatibility."""
        return self.class_name
    
    def get_property(self, path: str, default: Any = None) -> Any:
        """Fetch a property from raw OCSF dictionary using dot notation."""
        if not path:
            return self.raw_data
        
        parts = path.split('.')
        current = self.raw_data
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part, None)
            else:
                return default
            
            if current is None:
                return default
                
        return current
