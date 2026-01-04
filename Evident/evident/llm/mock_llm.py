"""Mock LLM for testing without API calls"""

import time
import random
from typing import Dict, Any, List
from evident.llm.base_llm import BaseLLM


class MockLLM(BaseLLM):
    """Mock LLM for testing and development"""
    
    def __init__(self, config: Any):
        super().__init__(config)
        self.response_templates = self._load_templates()
    
    def generate(self, prompt: str, context: str = "", **kwargs) -> Dict[str, Any]:
        """Generate mock security response"""
        
        # Simulate latency
        time.sleep(random.uniform(0.5, 1.5))
        
        # Analyze prompt to generate relevant response
        response_text = self._generate_response(prompt, context)
        
        # Estimate tokens
        tokens_used = (len(prompt) + len(context) + len(response_text)) // 4
        cost = tokens_used * self.config.cost_per_token
        
        self.total_tokens += tokens_used
        self.total_cost += cost
        
        return {
            "text": response_text,
            "model": self.config.model_id,
            "tokens_used": tokens_used,
            "cost": cost
        }
    
    def embed(self, text: str) -> List[float]:
        """Generate mock embeddings (random vector)"""
        # Return consistent random vector based on text hash
        random.seed(hash(text) % (2**32))
        return [random.random() for _ in range(384)]
    
    def _generate_response(self, prompt: str, context: str) -> str:
        """Generate contextual mock response"""
        prompt_lower = prompt.lower()
        
        # Vulnerability queries
        if any(word in prompt_lower for word in ["cve", "vulnerability", "vulnerabilities", "affected"]):
            return self._vulnerability_response(prompt, context)
        
        # Asset queries
        elif any(word in prompt_lower for word in ["asset", "server", "device", "infrastructure"]):
            return self._asset_response(prompt, context)
        
        # Access/Permission queries
        elif any(word in prompt_lower for word in ["permission", "access", "role", "privilege"]):
            return self._access_response(prompt, context)
        
        # Event/Log queries
        elif any(word in prompt_lower for word in ["event", "log", "failed", "login", "attempt"]):
            return self._event_response(prompt, context)
        
        # Cloud security queries
        elif any(word in prompt_lower for word in ["cloud", "aws", "azure", "gcp", "misconfiguration"]):
            return self._cloud_response(prompt, context)
        
        # General security query
        else:
            return self._general_response(prompt, context)
    
    def _vulnerability_response(self, prompt: str, context: str) -> str:
        if context:
            return f"""Based on the security data analysis:

**Vulnerability Assessment:**
{context[:500]}...

**Key Findings:**
- Multiple critical vulnerabilities detected requiring immediate attention
- Affected assets have been identified and prioritized by criticality
- Remediation steps are available for most vulnerabilities

**Recommendations:**
1. Prioritize patching critical vulnerabilities (CVSS > 9.0)
2. Verify affected assets are properly isolated
3. Monitor for exploitation attempts in security logs
4. Schedule maintenance windows for patch deployment

**Next Steps:**
Review the detailed vulnerability data above and coordinate with asset owners for remediation."""
        
        return "I found several vulnerabilities in the system. Please provide more specific criteria to narrow down the search."
    
    def _asset_response(self, prompt: str, context: str) -> str:
        if context:
            return f"""**Asset Analysis:**

{context[:400]}...

**Summary:**
- Assets have been categorized by type and criticality
- Ownership and department information is available
- Last scan dates indicate current security posture

**Security Observations:**
- Critical assets require enhanced monitoring
- Ensure all high-criticality assets have current security patches
- Review asset access controls regularly

**Recommendations:**
Maintain up-to-date asset inventory and ensure regular security scans."""
        
        return "Asset information is available. Please specify which assets you'd like to investigate."
    
    def _access_response(self, prompt: str, context: str) -> str:
        if context:
            return f"""**Access Control Analysis:**

{context[:400]}...

**Findings:**
- User role assignments and permissions have been mapped
- Risk levels vary from low to critical based on permission scope
- Some roles have elevated privileges requiring review

**Security Concerns:**
- Monitor accounts with critical permissions closely
- Ensure principle of least privilege is enforced
- Review temporary access grants regularly

**Recommendations:**
1. Audit high-risk permissions quarterly
2. Implement just-in-time access for critical operations
3. Enable MFA for all privileged accounts"""
        
        return "Access control data is available. Please specify the user or role you want to investigate."
    
    def _event_response(self, prompt: str, context: str) -> str:
        if context:
            return f"""**Security Event Analysis:**

{context[:400]}...

**Event Summary:**
- Multiple security events detected across different severity levels
- Failed login attempts and suspicious activities identified
- Correlation with user and asset data provides context

**Threat Indicators:**
- Unusual access patterns detected
- Geographic anomalies in sign-in logs
- Potential brute force attempts identified

**Recommended Actions:**
1. Investigate high-severity events immediately
2. Correlate events with user behavior baselines
3. Block suspicious IP addresses
4. Enable enhanced logging for affected assets"""
        
        return "Security events are being monitored. Please specify the time range or event type you're interested in."
    
    def _cloud_response(self, prompt: str, context: str) -> str:
        if context:
            return f"""**Cloud Security Assessment:**

{context[:400]}...

**Configuration Issues:**
- Several misconfigurations detected across cloud providers
- Risk levels range from low to critical
- Compliance violations identified

**Critical Findings:**
- Public access enabled on sensitive resources
- Encryption disabled on some data stores
- Overly permissive firewall rules

**Remediation Steps:**
1. Disable public access on all production resources
2. Enable encryption at rest and in transit
3. Implement least-privilege IAM policies
4. Enable cloud security monitoring and alerting"""
        
        return "Cloud configuration data is available. Please specify which cloud provider or resource type to analyze."
    
    def _general_response(self, prompt: str, context: str) -> str:
        if context:
            return f"""**Security Intelligence Summary:**

Based on the available security data:

{context[:300]}...

**Analysis:**
The security posture shows a mix of strengths and areas requiring attention. Multiple data sources have been correlated to provide comprehensive insights.

**Key Recommendations:**
1. Address critical vulnerabilities and misconfigurations first
2. Monitor user access patterns for anomalies
3. Maintain current asset inventory
4. Review and update security policies regularly

Please ask more specific questions about vulnerabilities, assets, access controls, events, or cloud security for detailed analysis."""
        
        return """I'm Evident, your security intelligence assistant. I can help you investigate:

- **Vulnerabilities**: CVEs, affected assets, remediation status
- **Assets**: Inventory, criticality, ownership
- **Access Control**: User permissions, roles, privilege analysis
- **Security Events**: Logs, failed logins, suspicious activities
- **Cloud Security**: Misconfigurations, compliance issues

What would you like to investigate?"""
    
    def _load_templates(self) -> Dict[str, str]:
        """Load response templates"""
        return {
            "greeting": "Hello! I'm Evident, your security intelligence assistant.",
            "error": "I encountered an issue processing your request. Please try rephrasing your question.",
        }
