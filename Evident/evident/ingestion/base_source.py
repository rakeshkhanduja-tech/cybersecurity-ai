"""Base interface for data sources"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pydantic import BaseModel


class SourceMetadata(BaseModel):
    """Metadata about a data source"""
    source_name: str
    source_type: str
    record_count: int = 0
    last_loaded: str = ""
    status: str = "not_loaded"  # not_loaded, loading, loaded, error


class BaseSource(ABC):
    """Abstract base class for all data sources"""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.metadata = SourceMetadata(
            source_name=source_name,
            source_type=self.__class__.__name__
        )
    
    @abstractmethod
    def load(self) -> List[Dict[str, Any]]:
        """
        Load data from the source
        
        Returns:
            List of dictionaries containing raw data
        """
        pass
    
    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> bool:
        """
        Validate a single data record
        
        Args:
            data: Raw data dictionary
        
        Returns:
            True if valid, False otherwise
        """
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, str]:
        """
        Get the expected schema for this source
        
        Returns:
            Dictionary mapping field names to types
        """
        pass
    
    def get_metadata(self) -> SourceMetadata:
        """Get source metadata"""
        return self.metadata
