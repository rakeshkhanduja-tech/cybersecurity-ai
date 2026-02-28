"""Configuration module for Evident"""

import json
import os
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables using absolute path to ensure discovery from any CWD
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(base_dir, ".env")
load_dotenv(env_path)
print(f"[DEBUG] ConfigLoader loaded .env from: {env_path}")


class LLMConfig(BaseModel):
    """Configuration for an LLM provider"""
    name: str
    provider: str  # e.g., "gemini", "openai", "mock"
    model_id: str
    cost_per_token: float
    capabilities: List[str]
    api_key: Optional[str] = None
    endpoint: Optional[str] = None


class VectorDBConfig(BaseModel):
    """Configuration for vector database"""
    path: str = Field(default="./chroma_db")
    collection_name: str = Field(default="evident_security")
    embedding_model: str = Field(default="all-MiniLM-L6-v2")


class GraphDBConfig(BaseModel):
    """Configuration for graph database"""
    type: str = Field(default="neo4j")
    uri: str = Field(default="bolt://localhost:7687")
    database: str = Field(default="neo4j")
    user: Optional[str] = None
    password: Optional[str] = None


class IngestionConfig(BaseModel):
    """Configuration for data ingestion"""
    data_path: str = Field(default="./data")
    sources: List[str] = Field(default_factory=list)


class AgentConfig(BaseModel):
    """Configuration for agent behavior"""
    max_context_length: int = Field(default=8000)
    retrieval_top_k: int = Field(default=5)
    graph_traversal_depth: int = Field(default=3)
    enable_reasoning_trace: bool = Field(default=True)


class AppConfig(BaseModel):
    """Main application configuration"""
    llms: List[LLMConfig]
    vector_db: VectorDBConfig
    graph_db: GraphDBConfig
    ingestion: IngestionConfig
    agent: AgentConfig


class ConfigLoader:
    """Loads and manages application configuration"""
    
    def __init__(self, config_path: str = "config.json"):
        # Use absolute path relative to this file to ensure persistence regardless of CWD
        if not os.path.isabs(config_path):
            # Move up two levels from evident/config/__init__.py to root
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.config_path = os.path.join(base_dir, config_path)
        else:
            self.config_path = config_path
            
        self._config: Optional[AppConfig] = None
    
    def load_config(self) -> AppConfig:
        """Load configuration from file and environment"""
        if self._config:
            return self._config
        
        abs_path = os.path.abspath(self.config_path)
        print(f"[DEBUG] ConfigLoader.load_config START (Looking for: {abs_path})")
        
        if not os.path.exists(self.config_path):
            print(f"[DEBUG] Config file NOT FOUND at {abs_path}. Using defaults.")
            self._config = self._get_default_config()
        else:
            print(f"[DEBUG] Config file FOUND at {abs_path}. Loading...")
            with open(self.config_path, "r") as f:
                data = json.load(f)
            self._config = AppConfig(**data)
        
        # Override with environment variables
        self._apply_env_overrides()
        
        return self._config
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides"""
        if not self._config:
            return
        
        # Override LLM API keys from environment (ignore placeholders)
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key and "your_gemini_api_key" not in gemini_key:
            for llm in self._config.llms:
                if llm.provider == "gemini":
                    llm.api_key = gemini_key
        
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and "your_openai_api_key" not in openai_key:
            for llm in self._config.llms:
                if llm.provider == "openai":
                    llm.api_key = openai_key
        
        # Override graph DB credentials
        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_user = os.getenv("NEO4J_USER")
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        
        if neo4j_uri:
            self._config.graph_db.uri = neo4j_uri
        if neo4j_user:
            self._config.graph_db.user = neo4j_user
        if neo4j_password:
            self._config.graph_db.password = neo4j_password
        
        # Override vector DB path
        chroma_path = os.getenv("CHROMA_DB_PATH")
        if chroma_path:
            self._config.vector_db.path = chroma_path
    
    def _get_default_config(self) -> AppConfig:
        """Get default configuration"""
        return AppConfig(
            llms=[
                LLMConfig(
                    name="Google Gemini",
                    provider="gemini",
                    model_id="gemini-2.0-flash",
                    api_key="",
                    cost_per_token=0.0000001,
                    capabilities=["general", "security"]
                )
            ],
            vector_db=VectorDBConfig(),
            graph_db=GraphDBConfig(),
            ingestion=IngestionConfig(
                sources=[
                    "cves",
                    "assets",
                    "logs",
                    "cloud_configs",
                    "signin_logs",
                    "user_roles",
                    "role_permissions"
                ]
            ),
            agent=AgentConfig()
        )
    
    def get_llm_config(self, provider: str = None, model_id: str = None) -> Optional[LLMConfig]:
        """Get LLM configuration by provider or model ID"""
        config = self.load_config()
        
        for llm in config.llms:
            if provider and llm.provider == provider:
                return llm
            if model_id and llm.model_id == model_id:
                return llm
        
        # Return first available LLM as fallback
        return config.llms[0] if config.llms else None
    
    def is_mock_mode(self, component: str = "llm") -> bool:
        """Check if running in mock mode"""
        if component == "llm":
            return os.getenv("USE_MOCK_LLM", "False").lower() == "true"
        elif component == "graph":
            return os.getenv("USE_MOCK_GRAPH", "False").lower() == "true"
        return False

    def save_config(self, app_config: AppConfig):
        """Save configuration to file"""
        self._config = app_config
        try:
            with open(self.config_path, "w") as f:
                json.dump(app_config.model_dump(), f, indent=4)
            print(f"[OK] Configuration saved to {self.config_path}")
        except Exception as e:
            print(f"Error saving configuration: {e}")


# Global config instance
config_loader = ConfigLoader()
app_config = config_loader.load_config()
