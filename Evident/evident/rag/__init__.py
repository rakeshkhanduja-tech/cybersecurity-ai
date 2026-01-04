"""RAG engine for context retrieval and augmentation"""

from typing import List, Dict, Any, Optional
from evident.rag.vector_store import VectorStore
from evident.rag.embedder import SecurityDocumentEmbedder
from evident.schema import SecurityEntity
from evident.config import app_config


class RAGEngine:
    """Retrieval-Augmented Generation engine"""
    
    def __init__(self, vector_store: Optional[VectorStore] = None):
        # Initialize vector store
        if vector_store is None:
            self.vector_store = VectorStore(
                persist_directory=app_config.vector_db.path,
                collection_name=app_config.vector_db.collection_name
            )
        else:
            self.vector_store = vector_store
        
        # Initialize embedder
        self.embedder = SecurityDocumentEmbedder()
        
        # Configuration
        self.top_k = app_config.agent.retrieval_top_k
        self.max_context_length = app_config.agent.max_context_length
    
    def index_entities(self, entities: List[SecurityEntity]):
        """
        Index security entities into vector store
        
        Args:
            entities: List of SecurityEntity objects to index
        """
        if not entities:
            print("⚠️  No entities to index")
            return
        
        print(f"Indexing {len(entities)} entities...")
        
        # Convert entities to documents
        documents, metadatas, ids = self.embedder.embed_entities(entities)
        
        # Add to vector store
        self.vector_store.add_documents(documents, metadatas, ids)
        
        print(f"✓ Indexed {len(entities)} entities")
    
    def retrieve_context(self, query: str, top_k: Optional[int] = None, 
                        filter_by: Optional[Dict[str, Any]] = None) -> str:
        """
        Retrieve relevant context for a query
        
        Args:
            query: User's query
            top_k: Number of documents to retrieve (uses config default if None)
            filter_by: Optional metadata filter
        
        Returns:
            Formatted context string
        """
        if top_k is None:
            top_k = self.top_k
        
        # Search vector store
        results = self.vector_store.search(query, top_k=top_k, filter_metadata=filter_by)
        
        if not results:
            return "No relevant security data found."
        
        # Format context
        context = self._format_context(results)
        
        # Truncate if too long
        if len(context) > self.max_context_length:
            context = context[:self.max_context_length] + "\n\n[Context truncated...]"
        
        return context
    
    def retrieve_with_metadata(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve context with full metadata
        
        Args:
            query: User's query
            top_k: Number of documents to retrieve
        
        Returns:
            List of result dictionaries with documents and metadata
        """
        if top_k is None:
            top_k = self.top_k
        
        return self.vector_store.search(query, top_k=top_k)
    
    def _format_context(self, results: List[Dict[str, Any]]) -> str:
        """Format search results into context string"""
        context_parts = []
        
        for i, result in enumerate(results, 1):
            doc = result['document']
            metadata = result['metadata']
            distance = result.get('distance', 0.0)
            
            # Add source information
            source = metadata.get('source', 'unknown')
            entity_type = metadata.get('entity_type', 'unknown')
            
            context_parts.append(f"[Source {i}: {entity_type} from {source}]")
            context_parts.append(doc)
            context_parts.append("")  # Empty line for separation
        
        return "\n".join(context_parts)
    
    def clear_index(self):
        """Clear all indexed documents"""
        self.vector_store.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get RAG engine statistics"""
        return {
            "vector_store": self.vector_store.get_stats(),
            "top_k": self.top_k,
            "max_context_length": self.max_context_length
        }
