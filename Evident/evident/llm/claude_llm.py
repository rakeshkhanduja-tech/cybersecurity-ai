from typing import Dict, Any
from evident.llm.base_llm import BaseLLM
from evident.config import LLMConfig
import os

try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False

class ClaudeLLM(BaseLLM):
    """Anthropic Claude LLM Wrapper"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        if not CLAUDE_AVAILABLE:
            raise ImportError("anthropic package is not installed")
            
        api_key = config.api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Anthropic API Key not provided")
            
        self.client = anthropic.Anthropic(api_key=api_key)
        
    def generate(self, prompt: str) -> Dict[str, Any]:
        """Generate response from Claude"""
        try:
            message = self.client.messages.create(
                model=self.config.model_id,
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = message.content[0].text
            input_tokens = message.usage.input_tokens
            output_tokens = message.usage.output_tokens
            total_tokens = input_tokens + output_tokens
            
            cost = (total_tokens * self.config.cost_per_token) / 1000 
            
            return {
                "text": content,
                "model": self.config.model_id,
                "tokens_used": total_tokens,
                "cost": cost,
                "raw": message
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
            "provider": "claude",
            "model": self.config.model_id
        }
