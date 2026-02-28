"""LLM factory and prompt templates"""

from typing import Optional
from evident.config import LLMConfig, config_loader
from evident.llm.base_llm import BaseLLM
from evident.llm.gemini_llm import GeminiLLM, GEMINI_AVAILABLE
from evident.llm.mock_llm import MockLLM


class LLMFactory:
    """Factory for creating LLM instances"""
    
    @staticmethod
    def create_llm(config: Optional[LLMConfig] = None, force_mock: bool = False) -> BaseLLM:
        """
        Create an LLM instance
        
        Args:
            config: LLM configuration (uses default if None)
            force_mock: Force use of mock LLM
        
        Returns:
            BaseLLM instance
        """
        print(f"\n[DEBUG] LLMFactory.create_llm START (force_mock={force_mock})")
        if config is None:
            print("[DEBUG] No config provided, loading from config.json...")
            
            # Smart discovery: Try to find a real provider with a key FIRST
            gemini_cfg = config_loader.get_llm_config(provider="gemini")
            is_mock_env = config_loader.is_mock_mode("llm")
            print(f"[DEBUG] is_mock_mode (env): {is_mock_env}")
            
            # If we have a Gemini key, we should ALWAYS use it (priority 1)
            has_gemini_key = gemini_cfg and gemini_cfg.api_key and "your_gemini_api_key" not in gemini_cfg.api_key
            
            if has_gemini_key:
                print("[DEBUG] Found valid Gemini configuration. Using as authoritative source.")
                config = gemini_cfg
            elif force_mock:
                print("[DEBUG] Forced Mock mode active (No real keys found)")
                config = config_loader.get_llm_config(provider="mock")
            elif is_mock_env:
                print("[DEBUG] Environment requested Mock mode, no real keys found. Using Mock.")
                config = config_loader.get_llm_config(provider="mock")
            else:
                print("[DEBUG] Defaulting to Gemini search")
                config = gemini_cfg or config_loader.get_llm_config()
        
        print(f"[DEBUG] Resolved Config - Name: {config.name}, Provider: {config.provider}, Model: {config.model_id}")
        
        if force_mock or config.provider == "mock":
            print("[DEBUG] Creating MockLLM instance")
            return MockLLM(config)
        
        if config.provider == "gemini":
            print("[DEBUG] Attempting GeminiLLM initialization...")
            if not GEMINI_AVAILABLE:
                print("[DEBUG] GEMINI_AVAILABLE is False (import error)")
                mock_config = config_loader.get_llm_config(provider="mock")
                mock = MockLLM(mock_config)
                mock.fallback_reason = "google-genai package not installed or import failed."
                return mock
            try:
                llm = GeminiLLM(config)
                print("[DEBUG] GeminiLLM initialized successfully")
                return llm
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                print(f"❌ [DEBUG] GeminiLLM INIT FAILED: {e}")
                print(f"[DEBUG] Traceback: {error_detail}")
                
                mock_config = config_loader.get_llm_config(provider="mock")
                mock = MockLLM(mock_config)
                mock.fallback_reason = f"Gemini initialization failed: {str(e)}"
                return mock

        # Generic handling for other providers
        try:
            if config.provider == "openai":
                from evident.llm.openai_llm import OpenAILLM
                return OpenAILLM(config)
            elif config.provider == "claude":
                from evident.llm.claude_llm import ClaudeLLM
                return ClaudeLLM(config)
        except Exception as e:
            print(f"⚠️ Failed to initialize {config.provider}: {e}")
            mock_config = config_loader.get_llm_config(provider="mock")
            mock = MockLLM(mock_config)
            mock.fallback_reason = f"{config.provider.title()} initialization failed: {str(e)}"
            return mock
        
        raise ValueError(f"Unsupported LLM provider: {config.provider}")


class PromptTemplates:
    """Security-specific prompt templates"""
    
    SYSTEM_PROMPT = """You are Evident, an expert cybersecurity AI assistant specialized in security intelligence and threat analysis.

Your role is to help security investigators by:
- Analyzing security data from multiple sources (CVEs, assets, logs, cloud configs, access controls)
- Identifying security risks and threats
- Providing actionable remediation recommendations
- Correlating events and entities to uncover security issues

Always provide:
1. Clear, concise answers based on available data
2. Specific evidence and sources
3. Risk assessment when relevant
4. Actionable next steps

Be direct and professional. If you don't have enough information, say so clearly."""
    
    INVESTIGATION_PROMPT = """You are Evident, a cybersecurity AI specialized in threat intelligence.
Use the following context from our Security Intelligence Graph and Vector Database to answer the investigator's question.

### SECURITY CONTEXT
{context}

### INVESTIGATOR QUESTION
{query}

### INSTRUCTIONS
1. Provide a direct and reasoned answer.
2. Cite specific evidence from the context above (e.g., mention specific CVEs, assets, or permissions).
3. Perform a risk assessment based on the criticality of the assets and vulnerabilities involved.
4. Recommend clear, actionable next steps for remediation or further investigation.

Response:"""
    
    THREAT_ANALYSIS_PROMPT = """Analyze the following security data for potential threats:

{context}

Question: {query}

Provide:
1. Threat assessment
2. Indicators of compromise (if any)
3. Affected assets/users
4. Remediation steps

Assessment:"""
    
    COMPLIANCE_PROMPT = """Review the following security configurations and access controls:

{context}

Question: {query}

Assess:
1. Compliance status
2. Policy violations (if any)
3. Risk level
4. Remediation steps

Assessment:"""
    
    @staticmethod
    def build_prompt(query: str, context: str, prompt_type: str = "investigation") -> str:
        """
        Build a prompt from template
        
        Args:
            query: User's question
            context: Retrieved context
            prompt_type: Type of prompt (investigation, threat, compliance)
        
        Returns:
            Formatted prompt
        """
        templates = {
            "investigation": PromptTemplates.INVESTIGATION_PROMPT,
            "threat": PromptTemplates.THREAT_ANALYSIS_PROMPT,
            "compliance": PromptTemplates.COMPLIANCE_PROMPT,
        }
        
        template = templates.get(prompt_type, PromptTemplates.INVESTIGATION_PROMPT)
        return template.format(context=context, query=query)
