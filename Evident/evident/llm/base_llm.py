"""Base LLM interface"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseLLM(ABC):
    """Abstract base class for all LLM providers"""
    
    def __init__(self, config: Any):
        self.config = config
        self.total_tokens = 0
        self.total_cost = 0.0
    
    @abstractmethod
    def generate(self, prompt: str, context: str = "", **kwargs) -> Dict[str, Any]:
        """
        Generate a response from the LLM
        
        Args:
            prompt: The user's query/prompt
            context: Additional context to include
            **kwargs: Additional provider-specific parameters
        
        Returns:
            Dictionary containing:
                - text: Generated response text
                - model: Model name used
                - tokens_used: Number of tokens consumed
                - cost: Cost of the request
        """
        pass
    
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """
        Generate embeddings for text
        
        Args:
            text: Text to embed
        
        Returns:
            List of embedding values
        """
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "model": self.config.model_id
        }
