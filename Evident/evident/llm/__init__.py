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
        if config is None:
            # Get default LLM from config
            if force_mock or config_loader.is_mock_mode("llm"):
                config = config_loader.get_llm_config(provider="mock")
            else:
                config = config_loader.get_llm_config(provider="gemini")
                if not config:
                    config = config_loader.get_llm_config()  # Get first available
        
        if force_mock or config.provider == "mock":
            return MockLLM(config)
        
        if config.provider == "gemini":
            if not GEMINI_AVAILABLE:
                print("⚠️  Gemini not available, falling back to mock LLM")
                mock_config = config_loader.get_llm_config(provider="mock")
                return MockLLM(mock_config)
            try:
                return GeminiLLM(config)
            except Exception as e:
                print(f"⚠️  Failed to initialize Gemini: {e}")
                print("Falling back to mock LLM")
                mock_config = config_loader.get_llm_config(provider="mock")
                return MockLLM(mock_config)
        
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
    
    INVESTIGATION_PROMPT = """Context from Security Intelligence Graph:
{context}

Security Investigator Question: {query}

Provide a comprehensive security analysis addressing the question. Include:
1. Direct answer to the question
2. Supporting evidence from the context
3. Risk assessment (if applicable)
4. Recommended actions

Response:"""
    
    THREAT_ANALYSIS_PROMPT = """Analyze the following security data for potential threats:

{context}

Question: {query}

Provide:
1. Threat assessment
2. Indicators of compromise (if any)
3. Affected assets/users
4. Recommended mitigation steps

Analysis:"""
    
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
