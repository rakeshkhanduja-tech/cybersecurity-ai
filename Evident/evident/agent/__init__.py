"""Evident AI Agent - Main agent class"""

from typing import Dict, Any, List, Optional
from evident.ingestion import SourceManager
from evident.rag import RAGEngine
from evident.smg import SMGManager
from evident.llm import LLMFactory, PromptTemplates
from evident.config import app_config


class EvidentAgent:
    """Main Evident security intelligence agent"""
    
    def __init__(self, use_mock_llm: bool = False, use_mock_graph: bool = True):
        print("\n" + "="*60)
        print("Initializing Evident Security Intelligence Agent")
        print("="*60)
        
        # Initialize components
        self.source_manager = SourceManager(data_path=app_config.ingestion.data_path)
        self.rag_engine = RAGEngine()
        self.smg_manager = SMGManager(use_mock=use_mock_graph)
        self.llm = LLMFactory.create_llm(force_mock=use_mock_llm)
        
        # State
        self.data_loaded = False
        self.graph_built = False
        
        print(f"✓ Agent initialized with {self.llm.config.name}")
        print("="*60 + "\n")
    
    def ingest_data(self):
        """Ingest security data from all sources"""
        print("\n" + "="*60)
        print("STEP 1: Data Ingestion")
        print("="*60)
        
        # Load all data sources
        all_entities = self.source_manager.load_all()
        
        # Flatten entities
        self.entities = []
        for source_name, entities in all_entities.items():
            self.entities.extend(entities)
        
        print(f"\n✓ Total entities loaded: {len(self.entities)}")
        self.data_loaded = True
        
        return self.entities
    
    def build_intelligence(self):
        """Build RAG index and SMG"""
        if not self.data_loaded:
            print("⚠️  No data loaded. Run ingest_data() first.")
            return
        
        print("\n" + "="*60)
        print("STEP 2: Building Intelligence Layer")
        print("="*60)
        
        # Build RAG index
        print("\n[RAG] Indexing entities into vector database...")
        self.rag_engine.index_entities(self.entities)
        
        # Build SMG
        print("\n[SMG] Building security memory graph...")
        self.smg_manager.build_graph(self.entities)
        
        self.graph_built = True
        
        print("\n" + "="*60)
        print("✓ Intelligence layer ready")
        print("="*60)
    
    def query(self, question: str, use_graph: bool = True, use_rag: bool = True) -> Dict[str, Any]:
        """
        Query the agent
        
        Args:
            question: Security investigator's question
            use_graph: Whether to use SMG for context
            use_rag: Whether to use RAG for context
        
        Returns:
            Response dictionary with answer and metadata
        """
        if not self.data_loaded or not self.graph_built:
            return {
                "answer": "Agent not ready. Please run ingest_data() and build_intelligence() first.",
                "sources": [],
                "error": "Agent not initialized"
            }
        
        print(f"\n{'='*60}")
        print(f"Query: {question}")
        print(f"{'='*60}")
        
        # Retrieve context
        context_parts = []
        sources = []
        
        if use_rag:
            print("\n[RAG] Retrieving relevant documents...")
            rag_context = self.rag_engine.retrieve_context(question)
            context_parts.append(f"=== Vector Database Results ===\n{rag_context}")
            sources.append("Vector Database")
        
        if use_graph:
            print("[SMG] Querying security graph...")
            graph_context = self._query_graph_for_context(question)
            if graph_context:
                context_parts.append(f"\n=== Security Graph Results ===\n{graph_context}")
                sources.append("Security Memory Graph")
        
        # Combine context
        full_context = "\n\n".join(context_parts) if context_parts else "No relevant context found."
        
        # Build prompt
        prompt = PromptTemplates.build_prompt(question, full_context, "investigation")
        
        # Generate response
        print("[LLM] Generating response...")
        llm_response = self.llm.generate(prompt)
        
        print(f"\n{'='*60}")
        print("Response generated")
        print(f"{'='*60}\n")
        
        return {
            "answer": llm_response["text"],
            "sources": sources,
            "context": full_context[:500] + "..." if len(full_context) > 500 else full_context,
            "model": llm_response["model"],
            "tokens": llm_response.get("tokens_used", 0),
            "cost": llm_response.get("cost", 0.0)
        }
    
    def _query_graph_for_context(self, question: str) -> str:
        """Query SMG for relevant context"""
        question_lower = question.lower()
        context_parts = []
        
        # CVE/Vulnerability queries
        if "cve" in question_lower:
            # Extract CVE ID if present
            import re
            cve_match = re.search(r'CVE-\d{4}-\d{4,}', question, re.IGNORECASE)
            if cve_match:
                cve_id = cve_match.group(0).upper()
                assets = self.smg_manager.get_assets_affected_by_cve(cve_id)
                if assets:
                    asset_list = [f"- {a['properties']['hostname']} ({a['properties']['criticality']} criticality)" 
                                 for a in assets[:5]]
                    context_parts.append(f"Assets affected by {cve_id}:\n" + "\n".join(asset_list))
        
        # User permission queries
        if any(word in question_lower for word in ["permission", "access", "role"]):
            # Try to extract username
            import re
            # Simple username extraction (e.g., "user john.doe")
            user_match = re.search(r'user\s+(\S+)', question, re.IGNORECASE)
            if user_match:
                username = user_match.group(1)
                permissions = self.smg_manager.get_user_permissions(username)
                if permissions:
                    perm_list = [f"- {p['properties']['action']} on {p['properties']['resource_type']} (scope: {p['properties']['scope']})" 
                                for p in permissions[:5]]
                    context_parts.append(f"Permissions for {username}:\n" + "\n".join(perm_list))
        
        # Asset queries
        if "asset" in question_lower:
            stats = self.smg_manager.get_stats()
            context_parts.append(f"Total assets in graph: {stats.get('node_count', 0)}")
        
        return "\n\n".join(context_parts) if context_parts else ""
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics"""
        return {
            "data_loaded": self.data_loaded,
            "graph_built": self.graph_built,
            "total_entities": len(self.entities) if self.data_loaded else 0,
            "source_status": self.source_manager.get_source_status(),
            "rag_stats": self.rag_engine.get_stats() if self.graph_built else {},
            "smg_stats": self.smg_manager.get_stats() if self.graph_built else {},
            "llm_stats": self.llm.get_stats()
        }
    
    def get_source_metadata(self) -> Dict[str, Any]:
        """Get metadata about loaded data sources"""
        return self.source_manager.get_metadata()
