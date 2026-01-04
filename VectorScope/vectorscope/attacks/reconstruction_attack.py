"""Optimization-based vector reconstruction attack"""

import numpy as np
import time
from typing import List, Dict, Any, Optional
from .base_attack import BaseAttack, AttackResult


class ReconstructionAttack(BaseAttack):
    """
    Reverse engineer text from vectors using iterative optimization/beam search.
    
    Strategy:
    1. Start with known templates (e.g., "SSN: XXX-XX-XXXX")
    2. Iteratively refine digits to minimize distance between generated and target embeddings.
    3. Use beam search to keep track of multiple promising candidates.
    """
    
    def __init__(self, vector_db):
        super().__init__(vector_db)
    
    def execute(self, target_vector: np.ndarray, data_type: str = 'ssn', 
                beam_width: int = 5, **kwargs) -> AttackResult:
        """
        Execute reconstruction attack using beam search in digit space.
        
        Args:
            target_vector: Vector to reverse engineer
            data_type: 'ssn' or 'creditcard'
            beam_width: Number of top candidates to track during search
        """
        start_time = time.time()
        
        if data_type == 'ssn':
            extracted_text = self._reconstruct_ssn(target_vector, beam_width)
        elif data_type == 'creditcard':
            extracted_text = self._reconstruct_cc(target_vector, beam_width)
        else:
            raise ValueError(f"Unsupported data type for reconstruction: {data_type}")
            
        elapsed = time.time() - start_time
        
        # Verify result similarity
        final_vector = self.vector_db.embed_text(extracted_text)
        confidence = float(self.vector_db.compute_similarity(target_vector, final_vector))
        
        return AttackResult(
            success=confidence > 0.9,
            extracted_text=extracted_text,
            confidence=confidence,
            method="Reconstruction Attack (Beam Search)",
            num_queries=0, # Calculated internally if needed
            time_seconds=elapsed,
            metadata={'data_type': data_type, 'beam_width': beam_width}
        )

    def _reconstruct_ssn(self, target_vector: np.ndarray, beam_width: int) -> str:
        """Reconstruct SSN segment by segment"""
        # Template: "SSN: AAA-GG-SSSS"
        # We'll optimize area (AAA), then group (GG), then serial (SSSS)
        
        print("\nReconstructing SSN via iterative optimization...")
        
        # Initial candidates
        candidates = ["SSN: 000-00-0000"]
        
        # 1. Optimize Area (3 digits) - for demo we'll sample promising areas
        candidates = self._optimize_segment(target_vector, candidates, 5, 8, 100)
        
        # 2. Optimize Group (2 digits)
        candidates = self._optimize_segment(target_vector, candidates, 9, 11, 50)
        
        # 3. Optimize Serial (4 digits)
        candidates = self._optimize_segment(target_vector, candidates, 12, 16, 50)
        
        return candidates[0]

    def _reconstruct_cc(self, target_vector: np.ndarray, beam_width: int) -> str:
        """Reconstruct CC segment by segment"""
        # Simplified reconstruction for demo
        print("\nReconstructing Credit Card via iterative optimization...")
        
        candidates = ["Credit Card: 0000-0000-0000-0000"]
        
        # Optimize segments of 4 digits
        for start, end in [(13, 17), (18, 22), (23, 27), (28, 32)]:
             candidates = self._optimize_segment(target_vector, candidates, start, end, 50)
             
        return candidates[0]

    def _optimize_segment(self, target_vector: np.ndarray, current_candidates: List[str], 
                          start: int, end: int, num_samples: int) -> List[str]:
        """Try random digit replacements in segment and keep best ones"""
        scored_candidates = []
        
        for base in current_candidates:
            # Generate local variations for the segment
            local_vars = []
            for _ in range(num_samples):
                chars = list(base)
                for i in range(start, end):
                    if chars[i].isdigit():
                        chars[i] = str(np.random.randint(0, 10))
                local_vars.append("".join(chars))
            
            # Embed and score
            embeddings = self.vector_db.embed_batch(local_vars)
            for i, emb in enumerate(embeddings):
                sim = self.vector_db.compute_similarity(target_vector, emb)
                scored_candidates.append((sim, local_vars[i]))
        
        # Sort by similarity and keep top
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return [text for sim, text in scored_candidates[:5]] # Return top 5
