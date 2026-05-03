"""Vector store using ChromaDB for semantic search"""

import os
import sys
from typing import List, Dict, Any, Optional

class VectorStore:
    """ChromaDB-based vector store for security documents"""
    
    def __init__(self, persist_directory: str = "./chroma_db", collection_name: str = "evident_security"):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self.embedding_model = None
        
        # Lazy load chromadb to avoid startup hangs
        try:
            import chromadb
            from chromadb.config import Settings
            
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(name=collection_name)
                print(f"[OK] Loaded existing collection: {collection_name}")
            except:
                self.collection = self.client.create_collection(
                    name=collection_name,
                    metadata={"description": "Evident security intelligence documents"}
                )
                print(f"[OK] Created new collection: {collection_name}")
                
            # Initialize embedding model
            self._load_embedder()
            
        except ImportError:
            print("[WARN] chromadb not found. Vector store functionality will be limited.")
        except Exception as e:
            print(f"[ERROR] Failed to initialize ChromaDB: {e}")

    def _load_embedder(self):
        """Lazy load sentence-transformers and torch"""
        try:
            from sentence_transformers import SentenceTransformer
            # Explicitly use 'cpu' device to avoid PyTorch meta-tensor errors or hangs on CUDA
            try:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
            except Exception:
                # Fallback for older versions or more complex errors
                import torch
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                self.embedding_model = self.embedding_model.cpu()
            print("[OK] Loaded embedding model: all-MiniLM-L6-v2")
        except Exception as e:
            print(f"[WARN] Could not load embedding model: {e}. Semantic search will be unavailable.")

    def add_documents(self, documents: List[str], metadatas: List[Dict[str, Any]], ids: List[str]):
        """Add documents to the vector store"""
        if not self.collection or not self.embedding_model:
            print("[ERROR] VectorStore not fully initialized. Cannot add documents.")
            return
            
        if not documents:
            return
        
        # Generate embeddings
        embeddings = self.embedding_model.encode(documents).tolist()
        
        # Add to collection
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"[OK] Added {len(documents)} documents to vector store")
    
    def search(self, query: str, top_k: int = 5, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        if not self.collection or not self.embedding_model:
            print("[ERROR] VectorStore not initialized. Cannot search.")
            return []
            
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query])[0].tolist()
        
        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_metadata
        )
        
        # Format results
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                formatted_results.append({
                    'document': doc,
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'distance': results['distances'][0][i] if results['distances'] else 0.0,
                    'id': results['ids'][0][i] if results['ids'] else ''
                })
        
        return formatted_results
    
    def clear(self):
        """Clear all documents from the collection"""
        if not self.client: return
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"description": "Evident security intelligence documents"}
        )
        print(f"[OK] Cleared collection: {self.collection_name}")
    
    def get_count(self) -> int:
        """Get number of documents in the collection"""
        if not self.collection: return 0
        return self.collection.count()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        return {
            "collection_name": self.collection_name,
            "document_count": self.get_count(),
            "persist_directory": self.persist_directory,
            "ready": self.collection is not None and self.embedding_model is not None
        }
