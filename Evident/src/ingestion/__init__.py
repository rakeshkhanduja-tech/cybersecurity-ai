"""Source manager for orchestrating data ingestion"""

from typing import Dict, List, Any
from tqdm import tqdm
import os
from src.ingestion.base_source import BaseSource, SourceMetadata
from src.ingestion.csv_loaders import (
    CVELoader, AssetLoader, LogEventLoader, CloudConfigLoader,
    SignInLogLoader, UserRoleLoader, RolePermissionLoader
)
from src.schema.normalizer import SecurityNormalizer, OCSFSemanticNormalizer
from src.schema import SecurityEntity
from src.ingestion.ocsf_loaders import OCSFJSONLoader
from src.config import config_loader


class SourceManager:
    """Manages data ingestion from multiple sources"""
    
    def __init__(self, data_path: str = "./data"):
        self.data_path = data_path
        self.sources: Dict[str, BaseSource] = {}
        
        config = config_loader.load_config()
        self.schema_preference = config.ingestion.schema_preference
        
        if self.schema_preference == "ocsf":
            self.normalizer = OCSFSemanticNormalizer()
        else:
            self.normalizer = SecurityNormalizer()
            
        self._register_default_sources()
    
    def _register_default_sources(self):
        """Register all default loaders based on schema preference"""
        if self.schema_preference == "ocsf":
            # Just look for JSON files mapping to standard connector signals
            signals = ["cves", "assets", "logs", "cloud_configs", "signin_logs", "user_roles", "role_permissions", "detections"]
            for sig in signals:
                path = f"{self.data_path}/{sig}"
                if os.path.exists(path) or True: # It may not exist yet, but we define the source
                    self.register_source(OCSFJSONLoader(path, sig))
        else:
            self.register_source(CVELoader(f"{self.data_path}/cves"))
            self.register_source(AssetLoader(f"{self.data_path}/assets"))
            self.register_source(LogEventLoader(f"{self.data_path}/logs"))
            self.register_source(CloudConfigLoader(f"{self.data_path}/cloud_configs"))
            self.register_source(SignInLogLoader(f"{self.data_path}/signin_logs"))
            self.register_source(UserRoleLoader(f"{self.data_path}/user_roles"))
            self.register_source(RolePermissionLoader(f"{self.data_path}/role_permissions"))
    
    def register_source(self, source: BaseSource):
        """Register a data source"""
        self.sources[source.source_name] = source
    
    def load_all(self) -> Dict[str, List[SecurityEntity]]:
        """
        Load data from all registered sources
        
        Returns:
            Dictionary mapping source names to lists of normalized entities
        """
        all_entities = {}
        
        print("Loading data from all sources...")
        for source_name, source in tqdm(self.sources.items(), desc="Loading sources"):
            try:
                # Load raw data
                raw_data = source.load()
                
                if not raw_data:
                    print(f"  [WARN] No data loaded from {source_name}")
                    all_entities[source_name] = []
                    continue
                
                # Normalize data
                entities = self.normalizer.normalize(raw_data, source_name)
                # Keep entities directly if normalizer bypasses/wraps in OCSFEntity
                all_entities[source_name] = entities
                
                print(f"  [OK] Loaded {len(entities)} entities from {source_name}")
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"  [ERROR] Error loading {source_name}: {e}")
                all_entities[source_name] = []
        
        return all_entities
    
    def load_source(self, source_name: str) -> List[SecurityEntity]:
        """
        Load data from a specific source
        
        Args:
            source_name: Name of the source to load
        
        Returns:
            List of normalized entities
        """
        if source_name not in self.sources:
            raise ValueError(f"Unknown source: {source_name}")
        
        source = self.sources[source_name]
        raw_data = source.load()
        
        if not raw_data:
            return []
        
        entities = self.normalizer.normalize(raw_data, source_name)
        return entities
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata for all sources"""
        return {
            name: source.get_metadata().model_dump()
            for name, source in self.sources.items()
        }
    
    def get_source_status(self) -> Dict[str, str]:
        """Get status of all sources"""
        return {
            name: source.metadata.status
            for name, source in self.sources.items()
        }
    
    def get_total_records(self) -> int:
        """Get total number of records across all sources"""
        return sum(
            source.metadata.record_count
            for source in self.sources.values()
        )
