"""Configuration module for Evident

Config is split into two files:
  - user-config.json  : User-facing settings (LLM provider/key, schema, signal source, storage)
  - system-config.json: System/infra settings (vector DB, graph DB, agent tuning)

The ConfigLoader merges both into a single AppConfig at runtime.
"""

import json
import os
from typing import List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables using absolute path to ensure discovery from any CWD
_base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_env_path = os.path.join(_base_dir, ".env")
if os.path.exists(_env_path):
    load_dotenv(_env_path)
    print(f"[DEBUG] ConfigLoader loaded .env from: {_env_path}")
else:
    print(f"[DEBUG] No .env file found at {_env_path}")


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class LLMConfig(BaseModel):
    """Configuration for an LLM provider"""
    name: str = Field(default="Google Gemini")
    provider: str = Field(default="gemini")
    model_id: str = Field(default="gemini-2.0-flash")
    cost_per_token: float = Field(default=0.0000001)
    capabilities: List[str] = Field(default_factory=lambda: ["general", "security"])
    api_key: Optional[str] = None
    endpoint: Optional[str] = None


class VectorDBConfig(BaseModel):
    """Configuration for vector database (system)"""
    path: str = Field(default="data/chroma_db")
    collection_name: str = Field(default="evident_security")
    embedding_model: str = Field(default="all-MiniLM-L6-v2")


class GraphDBConfig(BaseModel):
    """Configuration for graph database (system)"""
    type: str = Field(default="neo4j")
    uri: str = Field(default="bolt://localhost:7687")
    database: str = Field(default="neo4j")
    user: Optional[str] = None
    password: Optional[str] = None


class PostgreSQLConfig(BaseModel):
    """Configuration for PostgreSQL-based Config Store"""
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    database: str = Field(default="evident_db")
    user: str = Field(default="postgres")
    password: str = Field(default="")


class SQLiteConfig(BaseModel):
    """Configuration for SQLite-based Config Store"""
    path: str = Field(default="data/connectors.db")


class ConfigStoreConfig(BaseModel):
    """Configuration for the main application settings/activity store"""
    type: str = Field(default="sqlite")  # sqlite | postgres
    sqlite: SQLiteConfig = Field(default_factory=SQLiteConfig)
    postgres: PostgreSQLConfig = Field(default_factory=PostgreSQLConfig)


class StorageConfig(BaseModel):
    """Configuration for cloud/local storage location (user)"""
    storage_type: str = Field(default="local")
    # Azure
    azure_account_name: Optional[str] = None
    azure_container: Optional[str] = None
    azure_keyvault_url: Optional[str] = None
    azure_secret_name: Optional[str] = None
    # AWS
    aws_s3_bucket: Optional[str] = None
    aws_region: Optional[str] = None
    aws_secret_name: Optional[str] = None
    # GCP
    gcp_project: Optional[str] = None
    gcs_bucket: Optional[str] = None
    gcp_secret_name: Optional[str] = None


class IngestionConfig(BaseModel):
    """Configuration for data ingestion (user)"""
    source_mode: str = Field(default="sample")   # sample | livedata | cloud
    data_path: str = Field(default="./data")
    sources: List[str] = Field(default_factory=list)
    schema_preference: str = Field(default="evident")
    storage_config: Optional[StorageConfig] = Field(default_factory=StorageConfig)


class AgentConfig(BaseModel):
    """Configuration for agent behaviour (system)"""
    max_context_length: int = Field(default=8000)
    retrieval_top_k: int = Field(default=5)
    graph_traversal_depth: int = Field(default=3)
    enable_reasoning_trace: bool = Field(default=True)


# ---------------------------------------------------------------------------
# Composite model — assembled from both files at runtime
# ---------------------------------------------------------------------------

class AppConfig(BaseModel):
    """Full merged application configuration"""
    # User config fields
    llms: List[LLMConfig] = Field(default_factory=list)
    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)
    # System config fields
    vector_db: VectorDBConfig = Field(default_factory=VectorDBConfig)
    graph_db: GraphDBConfig = Field(default_factory=GraphDBConfig)
    config_store: ConfigStoreConfig = Field(default_factory=ConfigStoreConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)


# ---------------------------------------------------------------------------
# Dedicated Pydantic models for each file on disk
# ---------------------------------------------------------------------------

class UserConfig(BaseModel):
    """Schema for user-config.json"""
    llms: List[LLMConfig] = Field(default_factory=list)
    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)


class SystemConfig(BaseModel):
    """Schema for system-config.json"""
    vector_db: VectorDBConfig = Field(default_factory=VectorDBConfig)
    graph_db: GraphDBConfig = Field(default_factory=GraphDBConfig)
    config_store: ConfigStoreConfig = Field(default_factory=ConfigStoreConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)


# ---------------------------------------------------------------------------
# ConfigLoader
# ---------------------------------------------------------------------------

class ConfigLoader:
    """
    Loads and manages split configuration.

    Files
    -----
    user-config.json   — LLM settings, ingestion schema, signal source, storage creds
    system-config.json — vector DB, graph DB, agent tuning knobs
    """

    USER_CONFIG_FILE = "user-config.json"
    SYSTEM_CONFIG_FILE = "system-config.json"

    def __init__(self):
        # Resolve absolute root (Evident/)
        # __file__ == .../Evident/evident/config/__init__.py
        self._root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.user_config_path = os.path.join(self._root, self.USER_CONFIG_FILE)
        self.system_config_path = os.path.join(self._root, self.SYSTEM_CONFIG_FILE)

        # Legacy single-file path — used only by the setup_required check in app.py
        self.config_path = self.user_config_path   # setup wizard writes user-config

        self._config: Optional[AppConfig] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_config(self) -> AppConfig:
        """Merge user + system config into a single AppConfig."""
        if self._config:
            self._update_data_path()
            return self._config

        user = self._load_user_config()
        system = self._load_system_config()

        self._config = AppConfig(
            llms=user.llms,
            ingestion=user.ingestion,
            vector_db=system.vector_db,
            graph_db=system.graph_db,
            config_store=system.config_store,
            agent=system.agent,
        )

        self._update_data_path()
        self._apply_env_overrides()
        return self._config

    def save_config(self, app_config: AppConfig):
        """Persist user and system portions to their respective files."""
        self._config = app_config
        self._update_data_path()
        self._save_user_config(app_config)
        self._save_system_config(app_config)
        self.reload()

    def reload(self):
        """Invalidate the in-memory cache so the next load_config() re-reads from disk."""
        self._config = None
        print("[DEBUG] ConfigLoader cache invalidated — will reload from disk on next access")

    def save_user_config(self, app_config: AppConfig):
        """Save only the user-facing config file."""
        self._config = app_config
        self._update_data_path()
        self._save_user_config(app_config)

    def save_system_config(self, app_config: AppConfig):
        """Save only the system config file."""
        self._save_system_config(app_config)

    def get_llm_config(self, provider: str = None, model_id: str = None) -> Optional[LLMConfig]:
        """Get LLM configuration by provider or model ID."""
        config = self.load_config()
        for llm in config.llms:
            if provider and llm.provider == provider:
                return llm
            if model_id and llm.model_id == model_id:
                return llm
        return config.llms[0] if config.llms else None

    def is_mock_mode(self, component: str = "llm") -> bool:
        """Check if running in mock mode via config or environment variable."""
        config = self.load_config()
        if component == "llm":
            return os.getenv("USE_MOCK_LLM", "False").lower() == "true"
        elif component == "graph":
            # Check env var first, then config
            env_mock = os.getenv("USE_MOCK_GRAPH")
            if env_mock is not None:
                return env_mock.lower() == "true"
            return config.graph_db.type == "mock"
        return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_user_config(self) -> UserConfig:
        if os.path.exists(self.user_config_path):
            print(f"[DEBUG] Loading user-config from: {self.user_config_path}")
            with open(self.user_config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return UserConfig(**data)
        print(f"[DEBUG] user-config.json not found, using defaults")
        return self._default_user_config()

    def _load_system_config(self) -> SystemConfig:
        if os.path.exists(self.system_config_path):
            print(f"[DEBUG] Loading system-config from: {self.system_config_path}")
            with open(self.system_config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return SystemConfig(**data)
        print(f"[DEBUG] system-config.json not found, using defaults")
        return SystemConfig()

    def _save_user_config(self, app_config: AppConfig):
        user = UserConfig(llms=app_config.llms, ingestion=app_config.ingestion)
        try:
            with open(self.user_config_path, "w", encoding="utf-8") as f:
                json.dump(user.model_dump(), f, indent=4)
            print(f"[OK] user-config.json saved to {self.user_config_path}")
        except Exception as e:
            print(f"[ERROR] Failed to save user-config.json: {e}")

    def _save_system_config(self, app_config: AppConfig):
        system = SystemConfig(
            vector_db=app_config.vector_db,
            graph_db=app_config.graph_db,
            config_store=app_config.config_store,
            agent=app_config.agent,
        )
        try:
            with open(self.system_config_path, "w", encoding="utf-8") as f:
                json.dump(system.model_dump(), f, indent=4)
            print(f"[OK] system-config.json saved to {self.system_config_path}")
        except Exception as e:
            print(f"[ERROR] Failed to save system-config.json: {e}")

    def _default_user_config(self) -> UserConfig:
        return UserConfig(
            llms=[LLMConfig(
                name="Google Gemini",
                provider="gemini",
                model_id="gemini-2.0-flash",
                api_key="",
                cost_per_token=0.0000001,
                capabilities=["general", "security"],
            )],
            ingestion=IngestionConfig(
                sources=[
                    "cves", "assets", "logs",
                    "cloud_configs", "signin_logs",
                    "user_roles", "role_permissions",
                ],
                schema_preference="evident",
            ),
        )

    def _update_data_path(self):
        """Derive the effective data_path from source_mode + schema_preference."""
        if not self._config:
            return

        mode = self._config.ingestion.source_mode
        schema = self._config.ingestion.schema_preference

        # Root is c:\PRODDEV\personal\cybersecurity-ai
        root = os.path.dirname(self._root)

        if mode in ("livedata", "cloud"):
            self._config.ingestion.data_path = os.path.join(
                self._root, "data", "livedata", "dataplugs_singnals"
            )
        else:  # sample
            if schema == "ocsf":
                self._config.ingestion.data_path = os.path.join(self._root, "data", "sample_ocsf")
            else:
                self._config.ingestion.data_path = os.path.join(self._root, "data", "sample")

        print(f"[DEBUG] data_path => {self._config.ingestion.data_path} (mode={mode}, schema={schema})")

    def _apply_env_overrides(self):
        """Override sensitive values from environment variables."""
        if not self._config:
            return

        # LLM API keys
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

        # Graph DB credentials
        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_user = os.getenv("NEO4J_USER")
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        if neo4j_uri:
            self._config.graph_db.uri = neo4j_uri
        if neo4j_user:
            self._config.graph_db.user = neo4j_user
        if neo4j_password:
            self._config.graph_db.password = neo4j_password

        # Vector DB path
        chroma_path = os.getenv("CHROMA_DB_PATH")
        if chroma_path:
            self._config.vector_db.path = chroma_path


# ---------------------------------------------------------------------------
# Global singletons
# ---------------------------------------------------------------------------
config_loader = ConfigLoader()
app_config = config_loader.load_config()
