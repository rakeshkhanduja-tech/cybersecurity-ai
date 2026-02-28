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


def _initialize_agent():
    """Run in a background thread: create agent and warm it up."""
    global agent
    try:
        print(f"[INIT] CWD: {os.getcwd()}")
        # Check if we should use mock LLM (default to False)
        use_mock_env = os.getenv("USE_MOCK_LLM", "False")
        use_mock = use_mock_env.lower() == "true"
        print(f"[INIT] USE_MOCK_LLM (env): {use_mock_env} -> Resolved: {use_mock}")
        
        # If not explicitly forced to mock, check if we have any reasoning keys
        if not use_mock:
             gemini_key = os.getenv("GEMINI_API_KEY", "")
             has_real_key = gemini_key and "your_gemini_api_key" not in gemini_key
             print(f"[INIT] Gemini API Key present: {bool(gemini_key)} | Is real key: {has_real_key}")
             if not has_real_key:
                 print("⚠️ No real LLM API keys found in environment. Relying on config.json.")

        _log_step("Loading configuration...")
        _log_step("Initializing LLM and components...")
        agent = EvidentAgent(use_mock_llm=use_mock, use_mock_graph=False)

        _log_step("Populating signal sources from CSV files...")
        agent.ingest_data()

        _log_step("Building vector database index...")
        # RAG indexing already happens inside build_intelligence
        _log_step("Constructing security knowledge graph...")
        agent.build_intelligence()

        _log_step("Evident is ready ✓")
        _init_state["ready"] = True

    except Exception as e:
        _log_step(f"Error during initialization: {e}")
        # Allow the server to stay up so user can see the error
        _init_state["ready"] = True  # unblock UI so it doesn't spin forever


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


@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    """Get or update agent configuration"""
    if request.method == 'GET':
        config = config_loader.load_config()
        # Find active or first gemini config
        llm = config_loader.get_llm_config(provider="gemini")
        
        return jsonify({
            "provider": llm.provider if llm else "gemini",
            "model_id": llm.model_id if llm else "gemini-2.0-flash",
            "api_key": f"{llm.api_key[:6]}...{llm.api_key[-4:]}" if (llm and llm.api_key and len(llm.api_key) > 10) else ""
        })
    
    # POST logic follows...
    data = request.json
    provider = data.get('provider')
    model_id = data.get('model_id')
    api_key = data.get('api_key')
    
    print(f"[API] Updating configuration: Provider={provider}, Model={model_id}, Key={api_key[:4]}...{api_key[-4:] if api_key else ''}")
    
    # 1. Update the app config object
    current_config = config_loader.load_config()
    
    # Update or add LLM config
    found = False
    for llm in current_config.llms:
        if llm.provider == provider:
            llm.model_id = model_id
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
    
    # 2. Persist to config.json
    config_loader.save_config(current_config)
    
    # 3. Reload global config effectively
    import evident.config
    evident.config.app_config = config_loader.load_config()
    
    # 4. Re-initialize agent LLM
    agent = get_agent()
    from evident.llm import LLMFactory
    print(f"[API] Re-initializing agent LLM via Factory")
    agent.llm = LLMFactory.create_llm(config=None) # Passing None forces it to reload from config_loader
    print(f"[API] Agent LLM updated to: {agent.llm.config.name} (type: {type(agent.llm).__name__})")
    
    return jsonify({"status": "success", "message": f"Updated to {model_id} and persisted config."})


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



if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(f"\n{'='*60}")
    print(f"Starting Evident Web Interface on http://localhost:{port}")
    print(f"{'='*60}\n")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
