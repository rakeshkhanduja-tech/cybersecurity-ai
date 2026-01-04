"""Base attack interface"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import numpy as np
from dataclasses import dataclass


@dataclass
class AttackResult:
    """Result of an attack"""
    success: bool
    extracted_text: Optional[str]
    confidence: float
    method: str
    num_queries: int
    time_seconds: float
    metadata: Dict[str, Any]
    
    def __str__(self):
        return f"""
Attack Result:
  Method: {self.method}
  Success: {self.success}
  Extracted: {self.extracted_text}
  Confidence: {self.confidence:.2%}
  Queries: {self.num_queries}
  Time: {self.time_seconds:.2f}s
"""


class BaseAttack(ABC):
    """Abstract base class for vector reverse engineering attacks"""
    
    def __init__(self, vector_db):
        """
        Initialize attack
        
        Args:
            vector_db: VectorDatabase instance
        """
        self.vector_db = vector_db
        self.name = self.__class__.__name__
    
    @abstractmethod
    def execute(self, target_vector: np.ndarray, **kwargs) -> AttackResult:
        """
        Execute the attack
        
        Args:
            target_vector: Vector to reverse engineer
            **kwargs: Attack-specific parameters
        
        Returns:
            AttackResult with extracted information
        """
        pass
    
    def evaluate(self, extracted: str, ground_truth: str) -> Dict[str, Any]:
        """
        Evaluate attack success
        
        Args:
            extracted: Extracted text
            ground_truth: Original text
        
        Returns:
            Evaluation metrics
        """
        exact_match = extracted == ground_truth
        
        # Partial match (for structured data)
        extracted_clean = ''.join(c for c in extracted if c.isalnum())
        truth_clean = ''.join(c for c in ground_truth if c.isalnum())
        
        char_matches = sum(1 for a, b in zip(extracted_clean, truth_clean) if a == b)
        partial_accuracy = char_matches / max(len(truth_clean), 1)
        
        return {
            'exact_match': exact_match,
            'partial_accuracy': partial_accuracy,
            'extracted': extracted,
            'ground_truth': ground_truth
        }
