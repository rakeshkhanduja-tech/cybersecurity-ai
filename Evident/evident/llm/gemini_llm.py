"""Google Gemini LLM implementation (uses google-genai SDK)"""

import os
from typing import Dict, Any, List

try:
    import google.genai as genai
    from google.genai import types as genai_types
    GEMINI_AVAILABLE = True
except ImportError:
    try:
        # Fallback to deprecated sdk if new one isn't installed yet
        import google.generativeai as _old_genai  # noqa: F401
        GEMINI_AVAILABLE = False
        _LEGACY = True
    except ImportError:
        GEMINI_AVAILABLE = False
        _LEGACY = False

from evident.llm.base_llm import BaseLLM


class GeminiLLM(BaseLLM):
    """Google Gemini LLM implementation"""

    def __init__(self, config: Any):
        super().__init__(config)
        print(f"[DEBUG] GeminiLLM.__init__ START")
        if not GEMINI_AVAILABLE:
            print("[DEBUG] Gemini SDK not available, raising ImportError")
            raise ImportError(
                "google-genai package not installed. "
                "Install with: pip install google-genai"
            )

        source = "config"
        api_key = config.api_key
        if not api_key:
            api_key = os.getenv("GEMINI_API_KEY")
            source = "environment"
            
        if not api_key or api_key == "your_gemini_api_key_here":
            print(f"[DEBUG] Gemini API key invalid or missing (Source: {source})")
            raise ValueError(
                f"Gemini API key not found or placeholder used (Source: {source}). "
                "Set GEMINI_API_KEY environment variable or provide in config."
            )

        masked_key = f"{api_key[:6]}...{api_key[-4:]}" if len(api_key) > 10 else "***"
        print(f"[DEBUG] Using API Key from {source}: {masked_key}")

        # Initialize Client with stable v1 API version
        print("[DEBUG] Initializing google.genai Client (API Version: v1)...")
        from google.genai import types as genai_types
        self.client = genai.Client(
            api_key=api_key,
            http_options=genai_types.HttpOptions(api_version='v1')
        )

        # Use base model name (SDK often adds models/ itself or fails if double-prefixed)
        self.model_id = config.model_id
        if self.model_id.startswith("models/"):
            print(f"[DEBUG] Sanitizing model_id: {self.model_id}")
            self.model_id = self.model_id.replace("models/", "")
        
        print(f"✅ [DEBUG] GeminiLLM instance created. Model: {self.model_id}")

    def generate(self, prompt: str, context: str = "", **kwargs) -> Dict[str, Any]:
        """Generate response using Gemini"""
        full_prompt = self._build_prompt(prompt, context)

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=full_prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=kwargs.get("temperature", 0.7),
                    max_output_tokens=kwargs.get("max_tokens", 2048),
                ),
            )

            response_text = response.text

            tokens_used = self._estimate_tokens(full_prompt, response_text)
            cost = tokens_used * self.config.cost_per_token

            self.total_tokens += tokens_used
            self.total_cost += cost

            return {
                "text": response_text,
                "model": self.model_id,
                "tokens_used": tokens_used,
                "cost": cost,
            }

        except Exception as e:
            error_str = str(e).lower()
            print(f"[DEBUG] Gemini Generation Error: {e}")
            
            # Automatic fallback if 404 or unsupported model occurs
            if "not found" in error_str or "404" in error_str or "not_found" in error_str or "not supported" in error_str:
                print(f"⚠️ Model {self.model_id} hit 404 or is unsupported. Attempting dynamic discovery...")
                
                try:
                    # 1. Discover actual available models for this key
                    available_models = []
                    print("[DEBUG] Querying all available models from API...")
                    for m in self.client.models.list():
                        methods = getattr(m, 'supported_methods', [])
                        print(f"[DEBUG] Model found: {m.name} | Methods: {methods}")
                        
                        # Be lenient: Include if metadata is empty or explicitly supports generation
                        name = m.name.replace('models/', '')
                        if not methods or 'generateContent' in methods or 'generate_content' in str(methods).lower():
                            available_models.append(name)
                    
                    if not available_models:
                        # Final desperation: take anything found
                        available_models = [m.name.replace('models/', '') for m in self.client.models.list()]
                        if not available_models:
                            raise ValueError("No models at all found for this API key.")
                    
                    # 2. Pick a stable-looking model from the real list (Prioritize 2.0/2.5 Flash)
                    new_model = available_models[0]
                    priority_targets = [
                        "gemini-2.0-flash", "gemini-2.5-flash", 
                        "gemini-1.5-flash", "gemini-2.0-flash-lite",
                        "gemini-2.0-pro", "gemini-1.5-pro"
                    ]
                    for target in priority_targets:
                        if target in available_models:
                            new_model = target
                            break
                    
                    print(f"🔄 Switching to discovered model: {new_model}")
                    self.model_id = new_model
                    
                    # 3. Retry with discovery model
                    response = self.client.models.generate_content(
                        model=self.model_id,
                        contents=full_prompt,
                        config=genai_types.GenerateContentConfig(
                            temperature=kwargs.get("temperature", 0.7),
                            max_output_tokens=kwargs.get("max_tokens", 2048),
                        ),
                    )
                    
                    response_text = response.text
                    tokens_used = self._estimate_tokens(full_prompt, response_text)
                    cost = tokens_used * self.config.cost_per_token
                    
                    return {
                        "text": response_text,
                        "model": f"{self.model_id} (auto-switched)",
                        "tokens_used": tokens_used,
                        "cost": cost,
                    }

                except Exception as discovery_err:
                    print(f"❌ Dynamic discovery failed: {discovery_err}")
                    return {
                        "text": f"Critical Error: Model {self.model_id} failed and no suitable fallback found. {str(discovery_err)}",
                        "model": self.model_id,
                        "tokens_used": 0,
                        "cost": 0.0,
                        "error": str(discovery_err),
                    }

            return {
                "text": f"Error generating response: {str(e)}",
                "model": self.model_id,
                "tokens_used": 0,
                "cost": 0.0,
                "error": str(e),
            }

    def embed(self, text: str) -> List[float]:
        """Generate embeddings using Gemini"""
        try:
            response = self.client.models.embed_content(
                model="models/text-embedding-004",
                contents=text,
            )
            return response.embeddings[0].values
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return [0.0] * 768

    def _build_prompt(self, prompt: str, context: str) -> str:
        """The agent now builds the full prompt using PromptTemplates.
        We just pass it through or append additional context if provided separately."""
        if not context:
            return prompt
        return f"{prompt}\n\n[Additional Retrieved Context]\n{context}"

    def _estimate_tokens(self, prompt: str, response: str) -> int:
        """Estimate token count (rough approximation: ~4 chars per token)"""
        return (len(prompt) + len(response)) // 4
