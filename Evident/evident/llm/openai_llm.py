from typing import Dict, Any, List
from evident.llm.base_llm import BaseLLM
from evident.config import LLMConfig
import os

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class OpenAILLM(BaseLLM):
    """OpenAI LLM Wrapper"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        if not OPENAI_AVAILABLE:
             raise ImportError("openai package is not installed.")
        
        api_key = config.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
             raise ValueError("OpenAI API Key not provided")
             
        self.client = OpenAI(api_key=api_key)
        
    def generate(self, prompt: str) -> Dict[str, Any]:
        """Generate response from OpenAI"""
        try:
            response = self.client.chat.completions.create(
                model=self.config.model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens
            
            cost = (total_tokens * self.config.cost_per_token) / 1000 # Rough estimate if strictly linear
            
            return {
                "text": content,
                "model": self.config.model_id,
                "tokens_used": total_tokens,
                "cost": cost,
                "raw": response
            }
            
        except Exception as e:
            return {
                "text": f"Error generating response: {str(e)}",
                "model": self.config.model_id,
                "tokens_used": 0,
                "cost": 0.0,
                "error": str(e)
            }
            
    def get_stats(self) -> Dict[str, Any]:
        return {
            "provider": "openai",
            "model": self.config.model_id
        }
