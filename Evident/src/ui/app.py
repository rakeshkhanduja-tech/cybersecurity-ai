"""Flask web application for Evident UI"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import threading
import json
from src.agent import EvidentAgent
from src.connectors import db
from src.connectors.db import reload_db, init_db as initialize_schema

# Initialize Flask app
app = Flask(__name__,
           static_folder='static',
           template_folder='templates')
CORS(app)

from src.agent.audit_logger import audit_logger
from src.config import config_loader, LLMConfig
from src.securityagents.agent_manager import agent_manager
from src.securityagents.lab_manager import lab_manager
from src.securityagents.notifications import notification_manager

# Shared initialization state — written by background thread, read by /api/status
_init_state = {
    "status": "initializing",
    "step": "Starting up...",
    "details": "Agent is starting up...",
    "progress": 10,
    "ready": False,
    "log": ["Initializing Evident Agent..."]
}

def _initialize_agent():
    """Background thread to initialize the heavy agent components"""
    global _init_state
    try:
        _init_state["step"] = "Loading components"
        _init_state["details"] = "Loading security components..."
        _init_state["progress"] = 30
        _init_state["log"].append("Loading security components...")
        
        # This will now use lazy loading for RAG/SMG
        _do_rebuild()
        
        # Initialize MCP servers for active agents
        try:
            from src.mcp.manager import mcp_manager
            all_agents = agent_manager.get_all_agents()
            for agent_info in all_agents:
                if agent_info.get("is_active") and not agent_info.get("is_paused"):
                    mcp_manager.start_server(agent_info["id"])
        except Exception as e:
            print(f"[ERROR] Failed to initialize MCP servers: {e}")
        
        _init_state["status"] = "ready"
        _init_state["step"] = "Ready"
        _init_state["details"] = "Agent is ready."
        _init_state["progress"] = 100
        _init_state["ready"] = True
        _init_state["log"].append("Agent is ready.")
    except Exception as e:
        _init_state["status"] = "error"
        _init_state["details"] = f"Initialization failed: {e}"
        print(f"[ERROR] Agent initialization failed: {e}")

def _do_rebuild():
    """Shared logic for initialization and manual refresh"""
    # Use mock flags from config
    use_mock_llm = config_loader.is_mock_mode("llm")
    use_mock_graph = config_loader.is_mock_mode("graph")
    
    # Initialize agent - this will trigger ingestion and component builds
    global agent
    agent = EvidentAgent(use_mock_llm=use_mock_llm, use_mock_graph=use_mock_graph)
    
    # Run initial ingestion
    agent.rebuild_dataset()

# -----------------------------------------------------------------------
# Setup detection helper — evaluated on every request, not just at startup
# -----------------------------------------------------------------------
def _needs_setup() -> bool:
    """
    Returns True if infrastructure setup is required (system-config.json missing).
    """
    return not os.path.exists(config_loader.system_config_path)


def _enter_setup_mode():
    """Reset global state to setup_required and stop any stale 'ready' flag."""
    global _init_state
    _init_state["status"]  = "setup_required"
    _init_state["ready"]   = False
    _init_state["step"]    = "Setup Required"
    _init_state["details"] = "Waiting for initial infrastructure configuration..."
    _init_state["progress"] = 0
    _init_state["log"]     = ["Waiting for user to complete infrastructure setup."]
    print("[INFO] Setup mode activated — system-config.json not found.")


# One-time startup boot decision
if _needs_setup():
    _enter_setup_mode()
else:
    _init_thread = threading.Thread(target=_initialize_agent, daemon=True)
    _init_thread.start()

import atexit
@atexit.register
def _shutdown_mcp():
    """Ensure all MCP processes are killed on exit"""
    try:
        from src.mcp.manager import mcp_manager
        mcp_manager.stop_all()
    except:
        pass


@app.route('/')
def landing():
    """Branded landing page"""
    return render_template('landing.html')


@app.route('/dashboard')
def index():
    """Main dashboard page"""
    # If infra setup is missing, forced redirect to setup wizard
    if _needs_setup():
        from flask import redirect, url_for
        return redirect(url_for('setup'))
    return render_template('index.html')

@app.route('/setup')
def setup():
    """First-run and settings setup wizard."""
    return render_template('setup.html')

@app.route('/api/config/check')
def check_config():
    """Check if system is configured"""
    return jsonify({
        "is_configured": not _needs_setup(),
        "has_user_config": os.path.exists(config_loader.user_config_path)
    })

@app.route('/configure')
def configure():
    """Unified Settings and Configuration page."""
    return render_template('setup.html')

@app.route('/agent-view/<agent_id>')
def agent_view(agent_id):
    """Detailed view for a specific security agent"""
    from src.mcp.manager import mcp_manager
    agent_data = agent_manager.get_agent_by_id(agent_id)
    if not agent_data:
        return "Agent not found", 404
    
    # Inject MCP endpoint
    if agent_data:
        agent_data["mcp_endpoint"] = mcp_manager.get_endpoint_for_agent(agent_id)
        
    return render_template('agent_view.html', agent=agent_data)


@app.route('/api/status')
def get_status():
    """Get agent initialization status"""
    return jsonify(_init_state)

@app.route('/api/sources')
def get_sources():
    """Get list of security data sources"""
    if not _init_state["ready"]:
        return jsonify({"sources": []})
    
    metadata = agent.get_source_metadata()
    sources = []
    for name, meta in metadata.items():
        sources.append({
            "name": name,
            "display_name": meta.get("display_name", name),
            "record_count": meta.get("record_count", 0)
        })
    return jsonify({"sources": sources})

@app.route('/api/source-data/<source_name>')
def get_source_data(source_name):
    """Get normalized data for a specific source"""
    if not _init_state["ready"]:
        return jsonify({"data": [], "error": "Agent not ready"})
    
    try:
        entities = agent.source_manager.load_source(source_name)
        
        # Convert to list of dicts with 'id' and 'type' for the frontend
        data = []
        for entity in entities:
            # Dump the model to a dict
            d = entity.model_dump()
            
            # Pydantic v2 model_dump doesn't include @property by default.
            # We explicitly inject 'id' and 'type' for the Cytoscape graph.
            if hasattr(entity, 'id'):
                d['id'] = entity.id
            
            # Determine 'type' from entity_type or class_name
            if hasattr(entity, 'entity_type'):
                d['type'] = entity.entity_type
            elif 'class_name' in d:
                d['type'] = d['class_name']
            
            # Additional safety mapping for fields requested by buildCyElements
            if 'event_type' in d and 'type' not in d: d['type'] = d['event_type']
            if 'asset_type' in d and 'type' not in d: d['type'] = d['asset_type']
            
            data.append(d)
            
        return jsonify({"data": data})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"data": [], "error": str(e)}), 500

@app.route('/api/connectors')
def list_connectors():
    """List available data plug specifications"""
    try:
        # Resolve data_plugs.json path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        plug_path = os.path.join(os.path.dirname(current_dir), "connectors", "dataplugs", "data_plugs.json")
        
        if os.path.exists(plug_path):
            with open(plug_path, "r", encoding="utf-8") as f:
                connectors = json.load(f)
                return jsonify({"connectors": connectors})
        return jsonify({"connectors": []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/api/models', methods=['POST'])
def list_models():
    """List available models for a provider"""
    data = request.json
    provider = data.get("provider", "gemini")
    api_key = data.get("api_key")
    
    # If key is masked or missing, try to find it in config
    if not api_key or "your_gemini_api_key_here" in api_key or "***" in api_key:
        cfg = config_loader.get_llm_config(provider=provider)
        if cfg and cfg.api_key:
            api_key = cfg.api_key
            
    if not api_key:
        return jsonify({"models": [], "error": "API Key required"}), 400
        
    try:
        if provider == "gemini":
            from google.genai import Client, types
            client = Client(api_key=api_key, http_options=types.HttpOptions(api_version='v1'))
            models = []
            for m in client.models.list():
                # Extract clean name
                name = m.name.replace('models/', '')
                
                # Filter for generative models
                methods = getattr(m, 'supported_methods', [])
                if not methods or 'generateContent' in methods or 'generate_content' in str(methods).lower():
                    models.append(name)
            
            return jsonify({"models": models})
        else:
            return jsonify({"models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]})
    except Exception as e:
        return jsonify({"models": [], "error": str(e)}), 500

@app.route('/api/connectors/active')
def list_active_connectors():
    """List connectors that are currently marked as active"""
    configs = db.get_all_configs()
    active = []
    for cid, info in configs.items():
        if info.get("is_active"):
            # Minimal info for UI summary
            active.append({
                "connector_id": cid,
                "config": info.get("config", {}),
                "records_generated": info.get("records_generated", 0),
                "last_run": info.get("last_run"),
                "scheduler_paused": info.get("scheduler_paused", False),
                "interval_minutes": info.get("interval_minutes", 5)
            })
    return jsonify({"active": active})

@app.route('/api/connectors/config')
def get_connector_configs():
    """Get all saved connector configurations from DB"""
    configs = db.get_all_configs()
    return jsonify({"configs": configs})

@app.route('/api/connectors/test', methods=['POST'])
def test_connector():
    """Test a connector connection (placeholder)"""
    data = request.json
    connector_id = data.get("connector_id")
    # In a real app, we would instantiate the connector and call .test_connection()
    # For now, we simulate success
    return jsonify({"status": "success", "message": f"Simulated connection to {connector_id} successful"})
@app.route('/api/connectors/save', methods=['POST'])
def save_connector_config():
    """Save or update a connector configuration in the DB"""
    data = request.json
    cid = data.get("connector_id")
    config = data.get("config", {})
    
    if not cid:
        return jsonify({"status": "error", "message": "Missing connector_id"}), 400
        
    try:
        # Extract is_active and interval_minutes from the config if present
        # This ensures they are saved in the dedicated DB columns
        is_active = config.pop('is_active', False)
        interval = int(config.pop('interval_minutes', 5))
        
        # Save to DB
        db.save_config(cid, config, is_active=is_active, interval=interval)
        return jsonify({"status": "success", "message": f"Configuration for {cid} saved"})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/connectors/pause/<connector_id>', methods=['POST'])
def pause_connector(connector_id):
    """Pause a connector's scheduler"""
    from src.connectors.scheduler import scheduler
    scheduler.pause_connector(connector_id)
    return jsonify({"status": "success"})

@app.route('/api/connectors/resume/<connector_id>', methods=['POST'])
def resume_connector(connector_id):
    """Resume a connector's scheduler"""
    from src.connectors.scheduler import scheduler
    scheduler.resume_connector(connector_id)
    return jsonify({"status": "success"})

@app.route('/api/connectors/run/<connector_id>', methods=['POST'])
def run_connector(connector_id):
    """Trigger an immediate run of a connector"""
    from src.connectors.scheduler import scheduler
    scheduler.run_now(connector_id)
    return jsonify({"status": "success"})

@app.route('/api/rebuild-graph', methods=['POST'])
def rebuild_graph():
    """Alias for rebuild_agent to match frontend expectations"""
    return rebuild_agent()

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration — always reads from disk for freshness."""
    config_loader.reload()
    config = config_loader.load_config()
    active_llm = config.llms[0] if config.llms else None

    return jsonify({
        "provider":        active_llm.provider if active_llm else "gemini",
        "api_key":         active_llm.api_key  if active_llm else "",
        "model_id":        active_llm.model_id if active_llm else "",
        "schema_preference": config.ingestion.schema_preference,
        "source_mode":     config.ingestion.source_mode,
        "storage_config":  config.ingestion.storage_config.model_dump()
                           if config.ingestion.storage_config else {},
    })

@app.route('/api/config', methods=['POST'])
def save_config():
    """Save updated configuration — called by both Setup wizard and Settings modal."""
    try:
        data = request.json

        # Always reload from disk first so we never work on a stale cache,
        # especially on first-run when user-config.json doesn't exist yet.
        config_loader.reload()
        config = config_loader.load_config()

        # --- LLM ---
        provider  = data.get("provider", "gemini")
        api_key   = data.get("api_key", "")
        model_id  = data.get("model_id", "gemini-2.0-flash")
        llm_names = {"gemini": "Google Gemini", "openai": "OpenAI GPT", "claude": "Anthropic Claude"}

        if config.llms:
            # Update the primary LLM slot in-place
            config.llms[0].provider = provider
            config.llms[0].api_key  = api_key
            config.llms[0].model_id = model_id
            config.llms[0].name     = llm_names.get(provider, provider.title())
        else:
            # No LLMs at all (e.g. after a clean delete of user-config) — create one
            from src.config import LLMConfig as _LLMConfig
            config.llms = [_LLMConfig(
                name=llm_names.get(provider, provider.title()),
                provider=provider,
                model_id=model_id,
                api_key=api_key,
                cost_per_token=0.0000001,
                capabilities=["general", "security"],
            )]

        # --- Ingestion ---
        config.ingestion.schema_preference = data.get("schema_preference", config.ingestion.schema_preference)
        config.ingestion.source_mode       = data.get("source_mode",       config.ingestion.source_mode)
        if "data_path" in data and data["data_path"]:
            config.ingestion.data_path = data["data_path"]

        from src.config import StorageConfig as _StorageConfig
        if "storage_config" in data and isinstance(data["storage_config"], dict):
            config.ingestion.storage_config = _StorageConfig(**data["storage_config"])

        # Persist to disk (user-config.json + system-config.json)
        config_loader.save_config(config)
        print(f"[INFO] Configuration saved — provider={provider}, schema={config.ingestion.schema_preference}, mode={config.ingestion.source_mode}")

        # Transition out of setup_required so redirect to / works after agent is ready
        if _init_state["status"] == "setup_required":
            _init_state["status"] = "initializing"
            _init_state["log"] = ["Configuration received. Initializing src..."]

        # Trigger background rebuild
        rebuild_agent()

        return jsonify({"status": "success", "message": "Configuration saved"})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/config/test', methods=['POST'])
def test_infra_connection():
    """Test connection to various infrastructure components before saving."""
    data = request.json
    target = data.get('target')
    payload = data.get('payload', {})

    try:
        print(f"[DEBUG] Processing connectivity test for target: {target}")
        if target == 'config_store':
            from src.connectors.db import SQLiteProvider, PostgresProvider
            store_type = payload.get('type')
            if store_type == 'sqlite':
                path = payload.get('sqlite', {}).get('path', 'data/connectors.db')
                provider = SQLiteProvider(path)
                return jsonify(provider.test_connection())
            elif store_type == 'postgres':
                pg = payload.get('postgres', {})
                provider = PostgresProvider(pg.get('host'), pg.get('port'), pg.get('database'), pg.get('user'), pg.get('password'))
                res = provider.test_connection()
                print(f"[DEBUG] Config Store ({store_type}) test result: {res}")
                return jsonify(res)
            
        elif target == 'graph_db':
            graph_type = payload.get('type', 'neo4j')
            if graph_type == 'mock':
                return jsonify({"success": True, "message": "In-Memory Graph Engine selected (No connection test required)"})

            # Neo4j check
            uri = payload.get('uri')
            user = payload.get('user')
            password = payload.get('password')
            
            if not uri:
                return jsonify({"success": False, "message": "Neo4j URI is required (e.g., neo4j://localhost:7687)"})
                
            try:
                from neo4j import GraphDatabase, basic_auth
                from neo4j.exceptions import ServiceUnavailable, AuthError
                
                # Use basic_auth explicitly to ensure credentials key is sent correctly
                auth = basic_auth(user or "", password or "")
                driver = GraphDatabase.driver(uri, auth=auth)
                
                # Set a tight timeout for the test using a real query
                with driver.session() as session:
                    session.run("RETURN 1").single()
                driver.close()
                print("[DEBUG] Neo4j connection successful")
                return jsonify({"success": True, "message": "Neo4j connection successful"})
            except (ServiceUnavailable, AuthError) as e:
                print(f"[DEBUG] Neo4j test failed (Expected): {e}")
                return jsonify({"success": False, "message": f"Neo4j Error: {str(e)}"})
            except ImportError:
                print("[DEBUG] Neo4j test failed: Missing driver")
                return jsonify({"success": False, "message": "Neo4j Python driver not found in environment."})
            except Exception as e:
                print(f"[DEBUG] Neo4j test failed (Unexpected): {e}")
                import traceback
                traceback.print_exc()
                return jsonify({"success": False, "message": f"Neo4j Status: {str(e)}"})

        elif target == 'vector_db':
            # Chroma check
            path = payload.get('path')
            if not path:
                return jsonify({"success": False, "message": "Vector DB path is required."})
                
            try:
                import chromadb
                from chromadb.config import Settings
                
                # Align settings with VectorStore (anonymized_telemetry=False)
                # to avoid "instance already exists with different settings" error
                client = chromadb.PersistentClient(
                    path=path,
                    settings=Settings(anonymized_telemetry=False)
                )
                client.heartbeat()
                return jsonify({"success": True, "message": f"Vector DB successfully reached at: {path}"})
            except ImportError:
                return jsonify({"success": False, "message": "ChromaDB library not found."})
            except Exception as e:
                return jsonify({"success": False, "message": f"Vector DB Error: {str(e)}"})

        elif target == 'llm':
            provider_type = payload.get('provider')
            api_key = payload.get('api_key')
            
            if provider_type == 'google':
                import google.generativeai as genai
                try:
                    genai.configure(api_key=api_key)
                    # Simple call to list models to verify key
                    genai.list_models()
                    return jsonify({"success": True, "message": "Google AI API key verified"})
                except Exception as e:
                    return jsonify({"success": False, "message": f"Google AI verification failed: {str(e)}"})
            elif provider_type == 'openai':
                import requests
                try:
                    # Simple direct check to avoid heavy dependency just for test
                    res = requests.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {api_key}"}, timeout=5)
                    if res.status_code == 200:
                        return jsonify({"success": True, "message": "OpenAI API key verified"})
                    else:
                        return jsonify({"success": False, "message": f"OpenAI verification failed (Status {res.status_code})"})
                except Exception as e:
                    return jsonify({"success": False, "message": f"OpenAI check failed: {str(e)}"})

        return jsonify({"status": "error", "message": "Unknown test target"}), 400

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"System error during test: {str(e)}"})

@app.route('/api/config/infra', methods=['GET', 'POST'])
def manage_infra_config():
    """Manage Triple-Store Architecture (PostgreSQL, Neo4j, Vector DB)."""
    try:
        # Always ensure we have latest from disk before editing
        config_loader.reload()
        config = config_loader.load_config()
        
        if request.method == 'GET':
            return jsonify({
                "config_store": config.config_store.model_dump(),
                "graph_db": config.graph_db.model_dump(),
                "vector_db": config.vector_db.model_dump(),
                "sqlite_absolute_path": os.path.join(os.path.dirname(config_loader.system_config_path), config.config_store.sqlite.path)
            })
            
        data = request.json
        
        # Update Config Store (SQLite/PostgreSQL)
        if "config_store" in data:
            cs = data["config_store"]
            config.config_store.type = cs.get("type", config.config_store.type)
            if "postgres" in cs:
                pg = cs["postgres"]
                config.config_store.postgres.host = pg.get("host", config.config_store.postgres.host)
                config.config_store.postgres.port = int(pg.get("port", config.config_store.postgres.port))
                config.config_store.postgres.database = pg.get("database", config.config_store.postgres.database)
                config.config_store.postgres.user = pg.get("user", config.config_store.postgres.user)
                if pg.get("password"):
                    config.config_store.postgres.password = pg["password"]
            if "sqlite" in cs:
                config.config_store.sqlite.path = cs["sqlite"].get("path", config.config_store.sqlite.path)

        # Update Graph DB
        if "graph_db" in data:
            gdb = data["graph_db"]
            config.graph_db.type = gdb.get("type", config.graph_db.type)
            config.graph_db.uri = gdb.get("uri", config.graph_db.uri)
            config.graph_db.database = gdb.get("database", config.graph_db.database)
            config.graph_db.user = gdb.get("user", config.graph_db.user)
            if gdb.get("password"):
                config.graph_db.password = gdb["password"]

        # Update Vector DB
        if "vector_db" in data:
            vdb = data["vector_db"]
            config.vector_db.path = vdb.get("path", config.vector_db.path)
            config.vector_db.collection_name = vdb.get("collection_name", config.vector_db.collection_name)
            config.vector_db.embedding_model = vdb.get("embedding_model", config.vector_db.embedding_model)

        # Save and Reload DB Provider
        config_loader.save_config(config)
        reload_db()
        
        # Trigger background agent rebuild to apply new infrastructure settings
        rebuild_agent()
        
        return jsonify({"status": "success", "message": "Infrastructure configuration saved and sub-systems rebuilding"})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/config/init-db', methods=['POST'])
def init_config_db():
    """Manually trigger schema initialization for the current backend."""
    try:
        # Reload DB provider just in case settings were just saved
        reload_db()
        initialize_schema()
        return jsonify({"status": "success", "message": "Database schema initialized successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/query', methods=['POST'])
def query_agent():
    """Primary chat query endpoint"""
    if not _init_state["ready"]:
        return jsonify({
            "answer": "Agent is still initializing. Please wait.",
            "ready": False
        }), 503
        
    data = request.json
    question = data.get("question")
    use_graph = data.get('use_graph', True)
    use_rag = data.get('use_rag', True)
    
    if not question:
        return jsonify({"error": "No question provided"}), 400
        
    try:
        response = agent.query(question, use_graph=use_graph, use_rag=use_rag)
        return jsonify(response)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/rebuild', methods=['POST'])
def rebuild_agent():
    """Trigger a full re-ingestion and rebuild of the intelligence layer"""
    global _init_state
    
    def background_rebuild():
        global _init_state
        try:
            _init_state["status"] = "rebuilding"
            _init_state["step"] = "Rebuilding"
            _init_state["details"] = "Clearing index and re-ingesting data..."
            _init_state["progress"] = 20
            _init_state["ready"] = False
            _init_state["log"] = ["Rebuilding intelligence layer..."]
            
            _do_rebuild()
            
            _init_state["status"] = "ready"
            _init_state["step"] = "Ready"
            _init_state["details"] = "Rebuild complete."
            _init_state["progress"] = 100
            _init_state["ready"] = True
            _init_state["log"].append("Rebuild complete.")
        except Exception as e:
            import traceback
            tb_lines = traceback.format_exc().splitlines()
            _init_state["status"]  = "error"
            _init_state["ready"]   = False
            _init_state["step"]    = "Failed"
            _init_state["details"] = str(e)
            # Append traceback into the log so setup page can render it
            _init_state["log"].append(f"ERROR: {e}")
            for line in tb_lines[-12:]:   # last 12 lines of traceback
                if line.strip():
                    _init_state["log"].append(line)
            print(f"[ERROR] Rebuild failed:\n{''.join(tb_lines)}")
            
    threading.Thread(target=background_rebuild, daemon=True).start()
    return jsonify({"status": "success", "message": "Rebuild started in background"})

@app.route('/api/stats')
def get_stats():
    """Get agent and source statistics"""
    if not _init_state["ready"]:
        return jsonify({"ready": False})
        
    stats = agent.get_stats()
    return jsonify({
        "ready": True,
        **stats,
        "sources": agent.get_source_metadata()
    })

@app.route('/api/notifications')
def get_notifications():
    """Get recent security notifications"""
    return jsonify([])

@app.route('/api/history')
def get_interaction_history():
    """Get audit history"""
    return jsonify({"history": audit_logger.load_history()})

@app.route('/api/logs')
def get_audit_logs():
    """Alias for history to support different frontend versions"""
    return jsonify({"history": audit_logger.load_history()})

# --- Security Agents API ---

def _inject_mcp_endpoints(agents):
    from src.mcp.manager import mcp_manager
    for agent in agents:
        agent["mcp_endpoint"] = mcp_manager.get_endpoint_for_agent(agent["id"])
    return agents

@app.route('/api/agents')
def get_security_agents():
    """Get all configured security agents"""
    agents = agent_manager.get_all_agents()
    return jsonify({"agents": _inject_mcp_endpoints(agents)})

@app.route('/api/agents/active')
def get_active_security_agents():
    """Get only active security agents"""
    all_agents = agent_manager.get_all_agents()
    active = [a for a in all_agents if a.get('is_active')]
    return jsonify({"agents": _inject_mcp_endpoints(active)})

@app.route('/api/agents/enable', methods=['POST'])
def enable_security_agent():
    """Enable a specific agent"""
    data = request.json
    aid = data.get("agent_id")
    config = data.get("config", {})
    if not aid:
        return jsonify({"status": "error", "message": "Missing agent_id"}), 400
    try:
        agent_manager.enable_agent(aid, config)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/agents/disable/<agent_id>', methods=['POST'])
def disable_security_agent(agent_id):
    """Disable a specific agent"""
    try:
        agent_manager.disable_agent(agent_id)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/agents/pause/<agent_id>', methods=['POST'])
def pause_security_agent(agent_id):
    """Pause a specific agent"""
    try:
        agent_manager.pause_agent(agent_id)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/agents/resume/<agent_id>', methods=['POST'])
def resume_security_agent(agent_id):
    """Resume a specific agent"""
    try:
        agent_manager.resume_agent(agent_id)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/agents/logs/<agent_id>')
def get_agent_logs(agent_id):
    """Get logs for a specific agent"""
    return jsonify({"logs": agent_manager.get_agent_logs(agent_id)})

@app.route('/api/agents/activity/<agent_id>')
def get_agent_activity(agent_id):
    """Get activity for a specific agent"""
    return jsonify({"activities": agent_manager.get_agent_activity(agent_id)})

@app.route('/api/agents/actions/<agent_id>')
def get_proposed_actions(agent_id):
    """Get proposed remediation actions for an agent"""
    try:
        actions = agent_manager.get_pending_actions(agent_id)
        return jsonify({"actions": actions})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/agents/actions/run/<int:action_id>', methods=['POST'])
def run_proposed_action(action_id):
    """Execute a proposed remediation action"""
    try:
        result = agent_manager.execute_action(action_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- Lab API ---

@app.route('/api/lab/status')
def get_lab_status():
    """Get current lab progress"""
    return jsonify(lab_manager.get_status())

@app.route('/api/lab/content')
def get_lab_content():
    """Get full lab content"""
    return jsonify(lab_manager.get_content())

@app.route('/api/lab/next', methods=['POST'])
def next_lab_step():
    """Advance to next lab step"""
    data = request.json
    return jsonify(lab_manager.next_step(data))

@app.route('/api/lab/submit', methods=['POST'])
def submit_lab_exercise():
    """Submit lab exercise for validation"""
    data = request.json
    sid = data.get("step_id")
    result = data.get("result")
    return jsonify(lab_manager.submit_exercise(sid, result))

@app.route('/api/lab/reset', methods=['POST'])
def reset_lab():
    """Reset lab progress"""
    return jsonify(lab_manager.reset_lab())


# Global scheduler initialization
from src.connectors.scheduler import scheduler
try:
    scheduler.start()
    print("[INFO] Connector scheduler started successfully.")
except Exception as e:
    print(f"[ERROR] Failed to start connector scheduler: {e}")


if __name__ == '__main__':
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)
