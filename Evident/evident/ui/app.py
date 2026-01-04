"""Flask web application for Evident UI"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
from evident.agent import EvidentAgent

# Initialize Flask app
app = Flask(__name__, 
           static_folder='static',
           template_folder='templates')
CORS(app)

# Initialize agent (will be done on first request)
agent = None


def get_agent():
    """Get or initialize the agent"""
    global agent
    if agent is None:
        # Initialize with mock LLM by default (can be changed via env var)
        use_mock = os.getenv("USE_MOCK_LLM", "True").lower() == "true"
        agent = EvidentAgent(use_mock_llm=use_mock, use_mock_graph=True)
        
        # Load data and build intelligence
        agent.ingest_data()
        agent.build_intelligence()
    
    return agent


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


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "Evident Security Intelligence Agent"})


if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(f"\n{'='*60}")
    print(f"Starting Evident Web Interface on http://localhost:{port}")
    print(f"{'='*60}\n")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
