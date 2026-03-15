"""Flask web application for Evident UI"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import threading
from evident.agent import EvidentAgent

# Initialize Flask app
app = Flask(__name__,
           static_folder='static',
           template_folder='templates')
CORS(app)

from evident.agent.audit_logger import audit_logger
from evident.config import config_loader, LLMConfig
from evident.securityagents.agent_manager import agent_manager

# Shared initialization state — written by background thread, read by /api/status
_init_state = {
    "ready": False,
    "step": "Starting...",
    "log": []          # chronological list of completed steps
}
agent = None


def _log_step(msg: str):
    """Append a step to the init log and update current step."""
    _init_state["step"] = msg
    _init_state["log"].append(msg)
    print(f"[INIT] {msg}")


def _do_rebuild():
    """Perform the actual rebuild logic, updating global _init_state."""
    global agent
    try:
        _init_state["ready"] = False
        _init_state["log"] = []
        
        _log_step("Reloading components and configuration...")
        import evident.config
        from evident.config import config_loader
        # Ensure config is reloaded from disk
        config_loader._config = None 
        config = config_loader.load_config()
        # Update global app_config to avoid stale references
        evident.config.app_config = config
        
        # Check if we should use mock LLM
        use_mock = os.getenv("USE_MOCK_LLM", "False").lower() == "true"
        
        if agent is None:
            _log_step("Initializing Evident Agent...")
            agent = EvidentAgent(use_mock_llm=use_mock, use_mock_graph=False)
            _log_step("Performing initial data ingestion...")
            agent.ingest_data()
            _log_step("Building initial intelligence layer...")
            agent.build_intelligence()
        else:
            _log_step(f"Re-initializing agent for source mode: {config.ingestion.source_mode}")
            # This will trigger SourceManager re-init and ingestion
            agent.rebuild_dataset()

        _log_step("Evident is ready ✓")
        _init_state["ready"] = True
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        _log_step(f"Error during rebuild: {e}")
        print(f"[REBUILD ERROR]\n{error_details}")
        _init_state["ready"] = True # Unblock UI on error

def _initialize_agent():
    """Initial startup rebuild"""
    _do_rebuild()

def _trigger_rebuild():
    """Start a background thread for a full rebuild"""
    thread = threading.Thread(target=_do_rebuild, daemon=True)
    thread.start()
    return thread


def get_agent():
    """Return agent (blocks until ready, for API endpoints called after init)."""
    global agent
    if agent is None:
        # Fallback – shouldn't normally happen since thread starts on import
        _initialize_agent()
    return agent


# Kick off background init immediately when the module is imported
_init_thread = threading.Thread(target=_initialize_agent, daemon=True)
_init_thread.start()


@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')


@app.route('/api/query', methods=['POST'])
def query():
    """Handle query requests"""
    data = request.json
    question = data.get('question', '')
    
    if not question:
        return jsonify({"error": "No question provided"}), 400
    
    # Get agent and query
    agent = get_agent()
    response = agent.query(question)
    
    return jsonify(response)


@app.route('/api/stats', methods=['GET'])
def stats():
    """Get agent statistics"""
    agent = get_agent()
    return jsonify(agent.get_stats())


@app.route('/chat')
def chat_page():
    """Render the standalone chat page."""
    return render_template('chat.html')


@app.route('/api/sources', methods=['GET'])
def sources():
    """Get data source metadata"""
    agent = get_agent()
    metadata = agent.get_source_metadata()
    
    # Format for frontend
    source_list = []
    for name, meta in metadata.items():
        source_list.append({
            "name": name,
            "display_name": name.replace("_", " ").title(),
            "record_count": meta.record_count,
            "status": meta.status,
            "last_loaded": meta.last_loaded
        })
    
    return jsonify({"sources": source_list})


@app.route('/api/source-data/<source_name>', methods=['GET'])
def source_data(source_name):
    """Get raw data for a source"""
    agent = get_agent()
    try:
        # We need to access the source manager directly
        # Since agent doesn't expose it publically in a friendly way for this, we use the internal reference
        if not agent.data_loaded:
             return jsonify({"error": "Data not loaded"}), 400
             
        # Re-load or fetch from cache if we had one. 
        # For now, we'll ask source manager to load it again (memory efficient, trade-off speed)
        # But wait, EvidentAgent calls load_all() and stores flattened list.
        # Let's verify if SourceManager caches. It doesn't seem to.
        
        entities = agent.source_manager.load_source(source_name)
        
        # Convert entities to dictionaries for JSON
        data = []
        for entity in entities:
             # Convert Pydantic model to dict
             entity_dict = entity.model_dump() if hasattr(entity, 'model_dump') else entity.dict()
             
             # Determine a display name based on entity type
             display_name = entity.id
             if "cve_id" in entity_dict:
                 display_name = entity_dict["cve_id"]
             elif "hostname" in entity_dict:
                 display_name = entity_dict["hostname"]
             elif "username" in entity_dict:
                 display_name = entity_dict["username"]
             elif "role_name" in entity_dict:
                 display_name = entity_dict["role_name"]
             elif "event_type" in entity_dict:
                 display_name = f"{entity_dict['event_type']} ({entity_dict.get('event_id', '')})"
                 
             # Basic serialization
             item = {
                 "id": entity.id,
                 "name": display_name,
                 "type": entity.entity_type,
                 **entity_dict
             }
             data.append(item)
             
        return jsonify({"data": data})
    except ValueError:
        return jsonify({"error": "Source not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "Evident Security Intelligence Agent"})


@app.route('/api/status', methods=['GET'])
def status():
    """Get agent initialization status (polled by frontend for loading screen)"""
    return jsonify({
        "ready": _init_state["ready"],
        "step": _init_state["step"],
        "log": _init_state["log"]
    })


@app.route('/api/models', methods=['POST'])
def list_models():
    """List available models for a provider"""
    data = request.json
    provider = data.get('provider')
    api_key = data.get('api_key')
    
    if not provider:
        return jsonify({"error": "Provider required"}), 400
        
    # If api_key is missing, a placeholder, or a masked version, try to load from config.json
    if not api_key or "your_" in api_key or "..." in api_key:
        llm_cfg = config_loader.get_llm_config(provider=provider)
        if llm_cfg and llm_cfg.api_key and "your_" not in llm_cfg.api_key:
            api_key = llm_cfg.api_key
            print(f"[DEBUG] list_models: Using stored API key for {provider}")
            
    if provider == 'gemini' and api_key and "your_" not in api_key:
        try:
            from google.genai import Client, types
            client = Client(
                api_key=api_key,
                http_options=types.HttpOptions(api_version='v1')
            )
            models = []
            for m in client.models.list():
                name = m.name.replace('models/', '')
                methods = getattr(m, 'supported_methods', [])
                
                # Include if it explicitly supports generation OR if metadata is missing/empty
                if not methods or 'generateContent' in methods or 'generate_content' in str(methods).lower():
                    models.append(name)
            
            print(f"[DEBUG] Discovered {len(models)} Gemini models: {models}")
            
            if not models:
                # Fallback to defaults including newer 2.x versions
                models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.0-pro", "gemini-1.5-pro"]
                
            return jsonify({"models": sorted(list(set(models)))})
        except Exception as e:
            print(f"[ERROR] Failed to list Gemini models: {e}")
            # Fallback to hardcoded list on error
            return jsonify({"models": ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]})

    # For now, return hardcoded lists based on provider
    if provider == 'openai':
        return jsonify({
            "models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
        })
    elif provider == 'claude':
        return jsonify({
            "models": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]
        })
    elif provider == 'gemini':
        # Default gemini list if key wasn't provided or discovery failed early
        return jsonify({
            "models": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"]
        })
    
    return jsonify({"models": []})


@app.route('/api/rebuild-graph', methods=['POST'])
def rebuild_graph():
    """Trigger a manual rebuild of the intelligence layer"""
    _trigger_rebuild()
    return jsonify({"status": "success", "message": "Rebuild triggered in background."})


@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    """Get or update agent configuration (LLM and Ingestion)"""
    if request.method == 'GET':
        config = config_loader.load_config()
        # Find active or first gemini config
        llm = config_loader.get_llm_config(provider="gemini")
        
        return jsonify({
            "provider": llm.provider if llm else "gemini",
            "model_id": llm.model_id if llm else "gemini-2.0-flash",
            "api_key": f"{llm.api_key[:6]}...{llm.api_key[-4:]}" if (llm and llm.api_key and len(llm.api_key) > 10) else "",
            "schema_preference": config.ingestion.schema_preference,
            "source_mode": config.ingestion.source_mode
        })
    
    data = request.json
    provider = data.get('provider')
    model_id = data.get('model_id')
    api_key = data.get('api_key')
    schema_preference = data.get('schema_preference', 'evident')
    source_mode = data.get('source_mode', 'sample')
    
    print(f"[API] Updating configuration: Provider={provider}, Model={model_id}, Key={api_key[:4]}...{api_key[-4:] if api_key else ''}, SourceMode={source_mode}")
    
    # 1. Update the app config object
    current_config = config_loader.load_config()
    
    # Update or add LLM config
    if provider and model_id:
        found = False
        for llm in current_config.llms:
            if llm.provider == provider:
                llm.model_id = model_id
                if api_key and "..." not in api_key: # Don't overwrite with masked key
                    llm.api_key = api_key
                found = True
                break
                
        if not found:
            current_config.llms.append(LLMConfig(
                name=f"{provider}-{model_id}",
                provider=provider,
                model_id=model_id,
                cost_per_token=0.0,
                capabilities=["general", "security"],
                api_key=api_key
            ))
    
    current_config.ingestion.schema_preference = schema_preference
    
    # Detect if source mode changed
    old_mode = current_config.ingestion.source_mode
    current_config.ingestion.source_mode = source_mode
    
    # 2. Persist to config.json
    config_loader.save_config(current_config)
    
    # 3. Reload global config effectively
    import evident.config
    evident.config.app_config = config_loader.load_config()
    
    # 4. Re-initialize agent components
    agent = get_agent()
    
    # Update LLM
    from evident.llm import LLMFactory
    agent.llm = LLMFactory.create_llm(config=None)
    
    # If source mode changed, trigger a rebuild in background
    if old_mode != source_mode:
        print(f"[API] Source mode changed from {old_mode} to {source_mode}. Triggering background rebuild...")
        _trigger_rebuild()
    
    return jsonify({"status": "success", "message": f"Updated configuration and persisted settings."})


@app.route('/api/history', methods=['GET'])
def get_history():
    """Get audit history"""
    history = audit_logger.load_history()
    return jsonify({"history": history})


@app.route('/api/graph', methods=['GET'])
def get_graph():
    """Get graph visualization data"""
    agent = get_agent()
    if not agent.graph_built:
        return jsonify({"nodes": [], "edges": []})
        
    # Get all nodes and edges from store (mock or real)
    # This assumes mock store for now which has these attributes
    if hasattr(agent.smg_manager.graph_store, 'nodes'):
         nodes = [
             {"data": {"id": n["properties"]["id"], "label": n["label"], **n["properties"]}} 
             for n in agent.smg_manager.graph_store.nodes
         ]
         edges = [
             {"data": {"source": e["from_id"], "target": e["to_id"], "label": e["type"], **e.get("properties", {})}}
             for e in agent.smg_manager.graph_store.relationships
         ]
         return jsonify({"nodes": nodes, "edges": edges})
         
    return jsonify({"nodes": [], "edges": []})


@app.route('/api/connectors', methods=['GET'])
def get_connectors():
    """Get available data plugs from filesystem."""
    import json
    # Use absolute path resolving up to connectors folder
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    plugs_file = os.path.join(base_dir, 'connectors', 'dataplugs', 'data_plugs.json')
    try:
         with open(plugs_file, "r", encoding="utf-8") as f:
             connectors = json.load(f)
         return jsonify({"connectors": connectors})
    except Exception as e:
         print(f"Error loading connectors: {e}")
         return jsonify({"connectors": []})





@app.route('/api/connectors/config', methods=['GET', 'POST'], strict_slashes=False)
def handle_connectors_config():
    """Get or save connector configurations."""
    import evident.connectors.db as db
    from evident.connectors.scheduler import scheduler
    
    if request.method == 'GET':
        configs = db.get_all_configs()
        return jsonify({"configs": configs})
        
    data = request.json
    connector_id = data.get('connector_id')
    config = data.get('config', {})
    is_active = data.get('is_active', False)
    interval = data.get('interval', 5)
    
    if not connector_id:
        return jsonify({"error": "Connector ID required"}), 400
        
    db.save_config(connector_id, config, is_active, interval=interval)
    
    # Refresh scheduler to pick up changes
    scheduler.refresh_from_db()
    
    return jsonify({"status": "success", "message": f"Saved config for {connector_id}"})


@app.route('/api/connectors/active', methods=['GET'], strict_slashes=False)
def get_active_connectors_stats():
    """Get stats for active connectors including scheduler status."""
    import evident.connectors.db as db
    active = db.get_all_configs()
    # Filter only active ones for the monitor
    active_list = []
    for cid, data in active.items():
        if data["is_active"]:
            active_list.append({
                "connector_id": cid,
                "last_run": data["last_run"],
                "records_generated": data["records_generated"],
                "scheduler_paused": data["scheduler_paused"],
                "interval_minutes": data["interval_minutes"]
            })
    return jsonify({"active": active_list})


@app.route('/api/connectors/pause/<connector_id>', methods=['POST'], strict_slashes=False)
def pause_connector(connector_id):
    from evident.connectors.scheduler import scheduler
    scheduler.pause_connector(connector_id)
    return jsonify({"status": "success", "message": f"Paused {connector_id}"})


@app.route('/api/connectors/resume/<connector_id>', methods=['POST'], strict_slashes=False)
def resume_connector(connector_id):
    from evident.connectors.scheduler import scheduler
    scheduler.resume_connector(connector_id)
    return jsonify({"status": "success", "message": f"Resumed {connector_id}"})


@app.route('/api/connectors/run/<connector_id>', methods=['POST'], strict_slashes=False)
def run_connector_now(connector_id):
    from evident.connectors.scheduler import scheduler
    scheduler.run_now(connector_id)
    return jsonify({"status": "success", "message": f"Triggered run for {connector_id}"})


@app.route('/api/connectors/test', methods=['POST'], strict_slashes=False)
def test_connector_connection():
    """Verify connector credentials without generating data."""
    import evident.connectors.db as db
    from evident.connectors.http_connector import HttpConnector
    from evident.connectors.aws_connector import AwsConnector
    from evident.connectors.sql_connector import SqlConnector
    
    data = request.json
    connector_id = data.get('connector_id')
    config = data.get('config', {})
    
    if not connector_id:
         return jsonify({"status": "error", "message": "Connector ID required"}), 400
         
    plug_def = db.get_plug_metadata(connector_id)
    if not plug_def:
         return jsonify({"status": "error", "message": f"Metadata not found for {connector_id}"}), 404
         
    try:
        if plug_def.get("base_url") == "boto3":
            conn = AwsConnector(plug_def, config)
        elif plug_def.get("plug_file") == "snowflake_plug.json":
            conn = SqlConnector(plug_def, config)
        else:
            conn = HttpConnector(plug_def, config)
            
        result = conn.test_connection()
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/api/connectors/logs/<connector_id>', methods=['GET'], strict_slashes=False)
def get_connector_logs(connector_id):
    """List log files for a specific connector."""
    # app.py is in c:\PRODDEV\personal\cybersecurity-ai\Evident\evident\ui\app.py
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    logs_dir = os.path.join(base_dir, 'Evident', 'evident', 'data', 'livedata', 'debug_logs')
    
    if not os.path.exists(logs_dir):
        return jsonify({"logs": []})
        
    logs = []
    for f in os.listdir(logs_dir):
        if f.endswith('.csv') and f"_{connector_id}.csv" in f:
            logs.append(f)
            
    # Sort by filename (timestamp-based) descending
    logs.sort(reverse=True)
    return jsonify({"logs": logs})


@app.route('/api/connectors/logs/view/<filename>', methods=['GET'], strict_slashes=False)
def view_connector_log(filename):
    """Read and return content of a log CSV file."""
    # app.py is in c:\PRODDEV\personal\cybersecurity-ai\Evident\evident\ui\app.py
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    log_path = os.path.join(base_dir, 'Evident', 'evident', 'data', 'livedata', 'debug_logs', filename)
    
    if not os.path.exists(log_path):
        return jsonify({"error": "Log file not found"}), 404
        
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Optional: Parse CSV to list of dicts for easier frontend handling
        import csv
        import io
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        return jsonify({"filename": filename, "data": rows})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/config', methods=['GET', 'POST'], strict_slashes=False)
def handle_app_config():
    import evident.connectors.db as db
    if request.method == 'GET':
        return jsonify(db.get_app_config())
    
    data = request.json
    for k, v in data.items():
        db.set_app_config(k, v)
    return jsonify({"status": "success"})


# Global scheduler initialization
from evident.connectors.scheduler import scheduler
try:
    scheduler.start()
    print("[INFO] Connector scheduler started successfully.")
except Exception as e:
    print(f"[ERROR] Failed to start connector scheduler: {e}")


@app.route('/api/agents', methods=['GET'])
def get_agents():
    """List all available security agents with status."""
    return jsonify({"agents": agent_manager.get_all_agents()})


@app.route('/api/agents/enable', methods=['POST'])
def enable_agent():
    """Enable or update a security agent."""
    data = request.json
    agent_id = data.get('agent_id')
    config = data.get('config', {})
    
    if not agent_id:
        return jsonify({"error": "No agent_id provided"}), 400
        
    try:
        agent_manager.enable_agent(agent_id, config)
        return jsonify({"status": "success", "message": f"Agent {agent_id} enabled"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/agents/disable/<agent_id>', methods=['POST'])
def disable_agent(agent_id):
    """Disable a security agent."""
    try:
        agent_manager.disable_agent(agent_id)
        return jsonify({"status": "success", "message": f"Agent {agent_id} disabled"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/agents/active', methods=['GET'])
def get_active_agents():
    """List only the enabled agents."""
    agents = agent_manager.get_all_agents()
    active = [a for a in agents if a.get('is_active')]
    return jsonify({"agents": active})


@app.route('/api/agents/pause/<agent_id>', methods=['POST'])
def pause_agent_route(agent_id):
    """Pause an active agent."""
    try:
        agent_manager.pause_agent(agent_id)
        return jsonify({"status": "success", "message": f"Agent {agent_id} paused"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/agents/resume/<agent_id>', methods=['POST'])
def resume_agent_route(agent_id):
    """Resume a paused agent."""
    try:
        agent_manager.resume_agent(agent_id)
        return jsonify({"status": "success", "message": f"Agent {agent_id} resumed"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/agents/logs/<agent_id>', methods=['GET'])
def get_agent_logs_route(agent_id):
    """Get recent logs for an agent."""
    limit = int(request.args.get('limit', 50))
    logs = agent_manager.get_agent_logs(agent_id, limit)
    return jsonify({"logs": logs})


@app.route('/api/agents/activity/<agent_id>', methods=['GET'])
def get_agent_activity_route(agent_id):
    """Get recent activity for an agent."""
    limit = int(request.args.get('limit', 50))
    activities = agent_manager.get_agent_activity(agent_id, limit)
    return jsonify({"activities": activities})


@app.route('/agent-view/<agent_id>')

def agent_view_page(agent_id):
    """Render the dedicated multi-tab agent view."""
    agent = agent_manager.get_agent_by_id(agent_id)
    if not agent:
        return "Agent not found", 404
    return render_template('agent_view.html', agent=agent)


if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(f"\n{'='*60}")
    print(f"Starting Evident Web Interface on http://localhost:{port}")
    print(f"{'='*60}\n")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
