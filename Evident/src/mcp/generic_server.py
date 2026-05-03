"""Generic MCP Server for Evident Security Agents"""

import os
import sys
import argparse
import asyncio
import json
import logging
from typing import List, Dict, Any, Optional

# Add project root to path so we can import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from mcp.server.fastmcp import FastMCP
from src.rag import RAGEngine
from src.smg import SMGManager
from src.ingestion import SourceManager
from src.securityagents.agent_manager import agent_manager
from src.config import config_loader

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("evident-mcp")

def parse_args():
    parser = argparse.ArgumentParser(description="Evident Security Agent MCP Server")
    parser.add_argument("--agent-id", required=True, help="ID of the security agent")
    parser.add_argument("--port", type=int, default=6101, help="Port to run the MCP server on")
    return parser.parse_args()

def main():
    args = parse_args()
    agent_id = args.agent_id
    port = args.port

    # 1. Load Agent Profile
    agent_profile = agent_manager.get_agent_by_id(agent_id)
    if not agent_profile:
        print(f"Error: Agent {agent_id} not found", file=sys.stderr)
        sys.exit(1)

    # 2. Initialize MCP Server
    mcp = FastMCP(f"Evident: {agent_profile['name']}", port=port)
    
    # 3. Initialize Security Components
    logger.info(f"Initializing MCP Server for agent: {agent_id} on port {port}")
    rag = RAGEngine()
    smg = SMGManager()
    
    # Get config for data path
    config = config_loader.load_config()
    source_manager = SourceManager(data_path=config.ingestion.data_path)
    
    supported_signals = agent_profile.get("supported_signals", [])

    # --- Resources ---
    
    @mcp.resource("agent://profile")
    def get_agent_profile() -> str:
        """Get the full profile and system prompt of this security agent"""
        return json.dumps(agent_profile, indent=2)

    @mcp.resource("agent://signals")
    def get_supported_signals() -> str:
        """Get the list of security signals this agent is specialized to analyze"""
        return json.dumps(supported_signals, indent=2)

    # --- Tools ---

    @mcp.tool()
    def search_knowledge_base(query: str, top_k: int = 5) -> str:
        """
        Search the security vector database for relevant documents, signals, or logs.
        The search is automatically scoped to the signals supported by this agent.
        """
        logger.info(f"[{agent_id}] Searching knowledge base for: {query}")
        
        # Filter RAG search by supported signals if possible
        # Currently RAGEngine.retrieve_context takes filter_by metadata
        filter_by = None
        if supported_signals:
            # We assume the metadata contains 'source' which corresponds to the signal name
            # This is a heuristic based on how SourceManager indexes data
            filter_by = {"source": {"$in": supported_signals}}
            
        context = rag.retrieve_context(query, top_k=top_k, filter_by=filter_by)
        return context

    @mcp.tool()
    def query_security_graph(query_type: str, **params) -> str:
        """
        Query the security memory graph (SMG) for connected entities, relationships, or neighbors.
        Common query types: 'nodes' (with label/properties), 'neighbors' (with node_id), 'path' (with from_id/to_id).
        """
        logger.info(f"[{agent_id}] Querying security graph: {query_type}")
        results = smg.query_graph(query_type, **params)
        return json.dumps(results, indent=2)

    @mcp.tool()
    def fetch_raw_signals(source_name: str, limit: int = 10) -> str:
        """
        Retrieve raw security entities directly from the storage source.
        Only sources supported by this agent are accessible.
        """
        if source_name not in supported_signals:
            return f"Error: Source '{source_name}' is not supported by this agent. Supported: {supported_signals}"
            
        logger.info(f"[{agent_id}] Fetching raw signals from: {source_name}")
        try:
            entities = source_manager.load_source(source_name)
            # Limit results
            entities = entities[:limit]
            normalized = [e.model_dump() for e in entities]
            return json.dumps(normalized, indent=2)
        except Exception as e:
            return f"Error fetching source: {str(e)}"

    @mcp.tool()
    def analyze_risk_summary() -> str:
        """
        Get a high-level summary of risks and anomalies identified by this agent across its domain.
        Combines RAG context and Graph paths.
        """
        logger.info(f"[{agent_id}] Generating risk summary")
        # 1. Get graph signals of interest
        signals = smg.get_signals_of_interest(limit=3)
        
        # 2. Get some relevant RAG context for a general "risk" query
        rag_context = rag.retrieve_context(f"risks related to {', '.join(supported_signals)}", top_k=2)
        
        summary = {
            "agent": agent_profile["name"],
            "graph_signals": signals,
            "vector_context_snippet": rag_context[:500] + "..." if len(rag_context) > 500 else rag_context
        }
        
        return json.dumps(summary, indent=2)

    # 4. Start Server
    logger.info(f"Starting MCP server '{agent_profile['name']}' on port {port}")
    mcp.run()

if __name__ == "__main__":
    main()
