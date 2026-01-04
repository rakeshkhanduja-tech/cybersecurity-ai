"""Similarity-based reverse engineering attack"""

import numpy as np
from typing import List, Dict, Any
import time
from tqdm import tqdm
from .base_attack import BaseAttack, AttackResult


class SimilarityAttack(BaseAttack):
    """
    Extract sensitive information using similarity matching
    
    Strategy:
    1. Generate candidate texts matching known patterns (SSN, credit cards)
    2. Embed all candidates
    3. Find candidate with highest similarity to target vector
    4. Return as extracted information
    """
    
    def __init__(self, vector_db):
        super().__init__(vector_db)
        self.candidates_cache = {}
    
    def generate_ssn_candidates(self, sample_size: int = 1000) -> List[str]:
        """
        Generate SSN candidates
        
        Args:
            sample_size: Number of candidates to generate
        
        Returns:
            List of SSN candidates in format "SSN: XXX-XX-XXXX"
        """
        if 'ssn' in self.candidates_cache:
            return self.candidates_cache['ssn'][:sample_size]
        
        print(f"Generating {sample_size} SSN candidates...")
        candidates = []
        
        # Generate random SSNs
        np.random.seed(42)  # For reproducibility
        for _ in range(sample_size):
            area = np.random.randint(1, 900)  # 001-899 (avoiding 000, 900-999)
            group = np.random.randint(1, 100)  # 01-99
            serial = np.random.randint(1, 10000)  # 0001-9999
            
            ssn = f"SSN: {area:03d}-{group:02d}-{serial:04d}"
            candidates.append(ssn)
        
        self.candidates_cache['ssn'] = candidates
        return candidates
    
    def generate_creditcard_candidates(self, sample_size: int = 1000) -> List[str]:
        """
        Generate credit card candidates
        
        Args:
            sample_size: Number of candidates to generate
        
        Returns:
            List of credit card candidates
        """
        if 'cc' in self.candidates_cache:
            return self.candidates_cache['cc'][:sample_size]
        
        print(f"Generating {sample_size} credit card candidates...")
        candidates = []
        
        # Common card prefixes
        prefixes = [
            '4',      # Visa
            '51', '52', '53', '54', '55',  # Mastercard
            '34', '37',  # American Express
            '6011',  # Discover
        ]
        
        np.random.seed(42)
        for _ in range(sample_size):
            prefix = np.random.choice(prefixes)
            
            # Generate remaining digits
            if prefix in ['34', '37']:  # Amex (15 digits)
                remaining = 15 - len(prefix)
            else:  # Others (16 digits)
                remaining = 16 - len(prefix)
            
            number = prefix + ''.join([str(np.random.randint(0, 10)) for _ in range(remaining)])
            
            # Format with hyphens
            if len(number) == 15:
                formatted = f"{number[:4]}-{number[4:10]}-{number[10:]}"
            else:
                formatted = f"{number[:4]}-{number[4:8]}-{number[8:12]}-{number[12:]}"
            
            candidates.append(f"Credit Card: {formatted}")
        
        self.candidates_cache['cc'] = candidates
        return candidates
    
    def generate_candidates_for_type(self, data_type: str, sample_size: int = 1000) -> List[str]:
        """
        Generate candidates for a specific data type
        
        Args:
            data_type: 'ssn' or 'creditcard'
            sample_size: Number of candidates
        
        Returns:
            List of candidate strings
        """
        if data_type == 'ssn':
            return self.generate_ssn_candidates(sample_size)
        elif data_type == 'creditcard':
            return self.generate_creditcard_candidates(sample_size)
        else:
            raise ValueError(f"Unknown data type: {data_type}")
    
    def execute(self, target_vector: np.ndarray, data_type: str = 'ssn', 
                sample_size: int = 1000, **kwargs) -> AttackResult:
        """
        Execute similarity attack
        
        Args:
            target_vector: Vector to reverse engineer
            data_type: Type of sensitive data ('ssn' or 'creditcard')
            sample_size: Number of candidates to test
        
        Returns:
            AttackResult with extracted information
        """
        start_time = time.time()
        
        # Generate candidates
        candidates = self.generate_candidates_for_type(data_type, sample_size)
        
        print(f"\nRunning similarity attack with {len(candidates)} candidates...")
        
        # Embed all candidates
        print("Embedding candidates...")
        candidate_embeddings = self.vector_db.embed_batch(candidates)
        
        # Compute similarities
        print("Computing similarities...")
        similarities = []
        for embedding in tqdm(candidate_embeddings, desc="Similarity search"):
            sim = self.vector_db.compute_similarity(target_vector, embedding)
            similarities.append(sim)
        
        # Find best match
        best_idx = np.argmax(similarities)
        best_similarity = similarities[best_idx]
        extracted_text = candidates[best_idx]
        
        elapsed = time.time() - start_time
        
        # Determine success (high similarity indicates likely match)
        success = best_similarity > 0.9  # Threshold for success
        
        return AttackResult(
            success=success,
            extracted_text=extracted_text,
            confidence=float(best_similarity),
            method="Similarity Attack",
            num_queries=len(candidates),
            time_seconds=elapsed,
            metadata={
                'data_type': data_type,
                'sample_size': sample_size,
                'top_5_similarities': sorted(similarities, reverse=True)[:5]
            }
        )
    
    def incremental_search(self, target_vector: np.ndarray, data_type: str = 'ssn',
                          max_iterations: int = 5) -> AttackResult:
        """
        Incremental search with increasing sample sizes
        
        Args:
            target_vector: Vector to reverse engineer
            data_type: Type of sensitive data
            max_iterations: Maximum number of iterations
        
        Returns:
            AttackResult
        """
        start_time = time.time()
        sample_sizes = [100, 500, 1000, 5000, 10000]
        
        best_result = None
        total_queries = 0
        
        for i, sample_size in enumerate(sample_sizes[:max_iterations]):
            print(f"\nIteration {i+1}: Testing {sample_size} candidates")
            
            result = self.execute(target_vector, data_type, sample_size)
            total_queries += result.num_queries
            
            if best_result is None or result.confidence > best_result.confidence:
                best_result = result
            
            # Early stopping if high confidence
            if result.confidence > 0.95:
                print(f"High confidence achieved ({result.confidence:.2%}), stopping early")
                break
        
        # Update result with total metrics
        best_result.time_seconds = time.time() - start_time
        best_result.num_queries = total_queries
        best_result.method = "Similarity Attack (Incremental)"
        
        return best_result
