"""Evident AI Agent - Main agent class"""

from typing import Dict, Any, List, Optional
from evident.ingestion import SourceManager
from evident.rag import RAGEngine
from evident.smg import SMGManager
from evident.llm import LLMFactory, PromptTemplates
from datetime import datetime
from evident.config import app_config
from evident.agent.audit_logger import audit_logger


class EvidentAgent:
    """Main Evident security intelligence agent"""
    
    def __init__(self, use_mock_llm: bool = False, use_mock_graph: bool = False):
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
        
        print(f"[OK] Agent initialized with {self.llm.config.name}")
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
        
        print(f"\n[OK] Total entities loaded: {len(self.entities)}")
        self.data_loaded = True
        
        return self.entities
    
    def build_intelligence(self):
        """Build RAG index and SMG"""
        if not self.data_loaded:
            print("[WARN] No data loaded. Run ingest_data() first.")
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
        print("[OK] Intelligence layer ready")
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
        execution_steps = []
        execution_steps.append({
            "step": "Start Investigation",
            "description": f"Received query: {question}",
            "timestamp": datetime.now().isoformat()
        })

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
            execution_steps.append({
                "step": "RAG Retrieval",
                "description": "Querying vector database for similar documents...",
                "timestamp": datetime.now().isoformat()
            })
            rag_context = self.rag_engine.retrieve_context(question)
            context_parts.append(f"=== Vector Database Results ===\n{rag_context}")
            sources.append("Vector Database")
            execution_steps.append({
                "step": "RAG Retrieval Complete",
                "description": f"Found relevant documents from vector store.",
                "timestamp": datetime.now().isoformat()
            })
        
        if use_graph:
            print("[SMG] Querying security graph...")
            execution_steps.append({
                "step": "Graph Query",
                "description": "Traversing security memory graph for connected entities...",
                "timestamp": datetime.now().isoformat()
            })
            graph_context = self._query_graph_for_context(question)
            if graph_context:
                context_parts.append(f"\n=== Security Graph Results ===\n{graph_context}")
                sources.append("Security Memory Graph")
                execution_steps.append({
                    "step": "Graph Query Complete",
                    "description": "Found connected entities in security graph.",
                    "timestamp": datetime.now().isoformat()
                })
        
        # Combine context
        full_context = "\n\n".join(context_parts) if context_parts else "No relevant context found."
        
        # Build prompt
        prompt = PromptTemplates.build_prompt(question, full_context, "investigation")
        
        # Generate response
        # Prepare LLM Trace description
        llm_name = self.llm.config.name
        is_fallback = getattr(self.llm, 'fallback_reason', None) is not None
        trace_desc = f"Generating response using {llm_name}..."
        if is_fallback:
            trace_desc = f"⚠️ Fallback Active: Generating response using {llm_name}..."

        print(f"[LLM] {trace_desc}")
        execution_steps.append({
            "step": "LLM Inference",
            "description": trace_desc,
            "timestamp": datetime.now().isoformat()
        })
        llm_response = self.llm.generate(prompt, context=full_context)
        
        print(f"\n{'='*60}")
        print("Response generated")
        print(f"{'='*60}\n")
        
        execution_steps.append({
            "step": "Complete",
            "description": "Response generated and formatted.",
            "timestamp": datetime.now().isoformat()
        })

        # Log interaction for audit history
        from evident.agent.audit_logger import audit_logger
        interaction_id = audit_logger.log_interaction(
            query=question,
            response=llm_response["text"],
            model=llm_response["model"],
            tokens=llm_response.get("tokens_used", 0),
            cost=llm_response.get("cost", 0.0),
            execution_steps=execution_steps,
            context_summary=full_context[:200] + "..." if len(full_context) > 200 else full_context
        )

        return {
            "answer": llm_response["text"],
            "sources": sources,
            "context": full_context[:500] + "..." if len(full_context) > 500 else full_context,
            "model": llm_response["model"],
            "tokens": llm_response.get("tokens_used", 0),
            "cost": llm_response.get("cost", 0.0),
            "interaction_id": interaction_id
        }
    
    def _query_graph_for_context(self, question: str) -> str:
        """Query SMG for relevant context using entities extracted from question"""
        question_lower = question.lower()
        context_parts = []
        
        # 1. Extract potential entities from the question
        import re
        
        # CVE IDs
        cve_pattern = r'CVE-\d{4}-\d{4,}'
        cves = re.findall(cve_pattern, question, re.IGNORECASE)
        
        # IP Addresses
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        ips = re.findall(ip_pattern, question)
        
        # Usernames (common formats)
        user_match = re.search(r'(?:user|account|member)\s+([a-zA-Z0-9\._-]+)', question, re.IGNORECASE)
        usernames = [user_match.group(1)] if user_match else []
        
        # Hostnames/Assets (e.g. "asset server-01")
        asset_match = re.search(r'(?:asset|host|server|vm)\s+([a-zA-Z0-9\._-]+)', question, re.IGNORECASE)
        hostnames = [asset_match.group(1)] if asset_match else []
        
        # 2. Query SMG for each extracted entity
        
        # CVE Context
        for cve_id in cves:
            cve_id = cve_id.upper()
            assets = self.smg_manager.get_assets_affected_by_cve(cve_id)
            if assets:
                asset_list = [f"- {a['properties'].get('hostname', a['properties'].get('id'))} ({a['properties'].get('criticality', 'medium')} criticality)" 
                             for a in assets[:10]]
                context_parts.append(f"Assets known to be affected by {cve_id}:\n" + "\n".join(asset_list))
        
        # User/Identity Context
        for username in usernames:
            permissions = self.smg_manager.get_user_permissions(username)
            if permissions:
                perm_list = [f"- Action: {p['properties'].get('action')} on {p['properties'].get('resource_type')} (Scope: {p['properties'].get('scope')})" 
                            for p in permissions[:10]]
                context_parts.append(f"Identified permissions for user '{username}':\n" + "\n".join(perm_list))
            
            # Look for recent logins or activity if we have those relationships
            # (Self-note: expansion logic in SMGManager would be needed for deeper traversal)
        
        # Asset context
        for hostname in hostnames:
            # Check if this hostname exists as a node
            asset_nodes = [e for e in self.entities if e.entity_type == "asset" and e.hostname == hostname]
            if asset_nodes:
                entity = asset_nodes[0]
                # we could query the graph for everything connected to this host
                # For now, let's just add basic info and mention we're looking at its connections
                context_parts.append(f"Security focus on asset: {hostname} (Type: {entity.asset_type}, Criticality: {entity.criticality})")
        
        # 3. Add global graph stats if no specific entities found
        if not context_parts:
            stats = self.smg_manager.get_stats()
            context_parts.append(f"Security Graph Overview: {stats.get('node_count', 0)} entities and {stats.get('relationship_count', 0)} connections are available for cross-source correlation.")
            
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
