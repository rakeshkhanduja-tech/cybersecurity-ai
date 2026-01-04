"""Google Gemini LLM implementation"""

import os
from typing import Dict, Any, List
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from evident.llm.base_llm import BaseLLM


class GeminiLLM(BaseLLM):
    """Google Gemini LLM implementation"""
    
    def __init__(self, config: Any):
        super().__init__(config)
        
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai package not installed. Install with: pip install google-generativeai")
        
        # Configure Gemini
        api_key = config.api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key not found. Set GEMINI_API_KEY environment variable or provide in config.")
        
        genai.configure(api_key=api_key)
        
        # Initialize model
        self.model = genai.GenerativeModel(config.model_id)
        
        # For embeddings
        self.embedding_model = "models/embedding-001"
    
    def generate(self, prompt: str, context: str = "", **kwargs) -> Dict[str, Any]:
        """Generate response using Gemini"""
        
        # Build full prompt with context
        full_prompt = self._build_prompt(prompt, context)
        
        try:
            # Generate response
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=kwargs.get("temperature", 0.7),
                    max_output_tokens=kwargs.get("max_tokens", 2048),
                )
            )
            
            response_text = response.text
            
            # Estimate tokens (Gemini doesn't always provide exact counts)
            tokens_used = self._estimate_tokens(full_prompt, response_text)
            cost = tokens_used * self.config.cost_per_token
            
            self.total_tokens += tokens_used
            self.total_cost += cost
            
            return {
                "text": response_text,
                "model": self.config.model_id,
                "tokens_used": tokens_used,
                "cost": cost
            }
            
        except Exception as e:
            return {
                "text": f"Error generating response: {str(e)}",
                "model": self.config.model_id,
                "tokens_used": 0,
                "cost": 0.0,
                "error": str(e)
            }
    
    def embed(self, text: str) -> List[float]:
        """Generate embeddings using Gemini"""
        try:
            result = genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            print(f"Error generating embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * 768
    
    def _build_prompt(self, prompt: str, context: str) -> str:
        """Build full prompt with context"""
        if not context:
            return prompt
        
        return f"""You are Evident, a cybersecurity AI assistant. Use the following context to answer the security investigator's question.

Context:
{context}

Question: {prompt}

Provide a detailed, accurate answer based on the context. If the context doesn't contain enough information, say so clearly."""
    
    def _estimate_tokens(self, prompt: str, response: str) -> int:
        """Estimate token count (rough approximation)"""
        # Rough estimate: ~4 characters per token
        return (len(prompt) + len(response)) // 4
