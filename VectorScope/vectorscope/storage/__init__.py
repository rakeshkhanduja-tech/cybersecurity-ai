"""Vector database storage and embedding generation"""

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Any, Optional
import uuid


class VectorDatabase:
    """Manages vector storage and retrieval"""
    
    def __init__(self, persist_directory: str = "./vector_db", 
                 embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize vector database
        
        Args:
            persist_directory: Directory to persist vectors
            embedding_model: Sentence transformer model name
        """
        self.persist_directory = persist_directory
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(name="sensitive_data")
            print(f"[OK] Loaded existing collection")
        except:
            self.collection = self.client.create_collection(
                name="sensitive_data",
                metadata={"description": "Sensitive information vectors for research"}
            )
            print(f"[OK] Created new collection")
        
        # Initialize embedding model
        print(f"Loading embedding model: {embedding_model}...")
        self.embedder = SentenceTransformer(embedding_model)
        self.embedding_dim = self.embedder.get_sentence_embedding_dimension()
        print(f"[OK] Model loaded (dimension: {self.embedding_dim})")
    
    def store_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Store text as vector embedding
        
        Args:
            text: Sensitive text to store
            metadata: Optional metadata
        
        Returns:
            Vector ID
        """
        # Generate unique ID
        vector_id = str(uuid.uuid4())
        
        # Generate embedding
        embedding = self.embedder.encode([text])[0].tolist()
        
        # Prepare metadata
        if metadata is None:
            metadata = {}
        metadata["original_text"] = text  # Store for ground truth comparison
        metadata["text_length"] = len(text)
        
        # Store in ChromaDB
        self.collection.add(
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
            ids=[vector_id]
        )
        
        return vector_id
    
    def get_vector(self, vector_id: str) -> Optional[np.ndarray]:
        """
        Retrieve vector by ID
        
        Args:
            vector_id: Vector identifier
        
        Returns:
            Vector as numpy array or None if not found
        """
        try:
            result = self.collection.get(
                ids=[vector_id],
                include=["embeddings"]
            )
            if result['embeddings']:
                return np.array(result['embeddings'][0])
            return None
        except:
            return None
    
    def get_metadata(self, vector_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a vector"""
        try:
            result = self.collection.get(
                ids=[vector_id],
                include=["metadatas"]
            )
            if result['metadatas']:
                return result['metadatas'][0]
            return None
        except:
            return None
    
    def get_all_vectors(self) -> List[Dict[str, Any]]:
        """Get all stored vectors with metadata"""
        result = self.collection.get(include=["embeddings", "metadatas"])
        
        vectors = []
        for i, vector_id in enumerate(result['ids']):
            vectors.append({
                'id': vector_id,
                'embedding': np.array(result['embeddings'][i]),
                'metadata': result['metadatas'][i]
            })
        
        return vectors
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for text without storing
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector
        """
        return self.embedder.encode([text])[0]
    
    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
        
        Returns:
            Array of embeddings
        """
        return self.embedder.encode(texts, show_progress_bar=True)
    
    def compute_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Compute cosine similarity between two vectors
        
        Args:
            vec1: First vector
            vec2: Second vector
        
        Returns:
            Cosine similarity score
        """
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    def find_similar(self, query_vector: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Find most similar vectors
        
        Args:
            query_vector: Query vector
            top_k: Number of results
        
        Returns:
            List of similar vectors with metadata
        """
        result = self.collection.query(
            query_embeddings=[query_vector.tolist()],
            n_results=top_k,
            include=["embeddings", "metadatas", "distances"]
        )
        
        similar = []
        for i in range(len(result['ids'][0])):
            similar.append({
                'id': result['ids'][0][i],
                'embedding': np.array(result['embeddings'][0][i]),
                'metadata': result['metadatas'][0][i],
                'distance': result['distances'][0][i]
            })
        
        return similar
    
    def count(self) -> int:
        """Get number of stored vectors"""
        return self.collection.count()
    
    def clear(self):
        """Clear all vectors"""
        self.client.delete_collection(name="sensitive_data")
        self.collection = self.client.create_collection(
            name="sensitive_data",
            metadata={"description": "Sensitive information vectors for research"}
        )
        print("[OK] Cleared all vectors")
