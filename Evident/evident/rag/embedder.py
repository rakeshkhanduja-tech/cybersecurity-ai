"""Document embedder for security data"""

from typing import List, Dict, Any
from evident.schema import SecurityEntity, EntityType


class SecurityDocumentEmbedder:
    """Converts security entities into embeddable documents"""
    
    def __init__(self):
        self.doc_count = 0
    
    def embed_entities(self, entities: List[SecurityEntity]) -> tuple[List[str], List[Dict[str, Any]], List[str]]:
        """
        Convert security entities into documents for embedding
        
        Args:
            entities: List of SecurityEntity objects
        
        Returns:
            Tuple of (documents, metadatas, ids)
        """
        documents = []
        metadatas = []
        ids = []
        
        for entity in entities:
            doc_text = self._entity_to_document(entity)
            metadata = self._entity_to_metadata(entity)
            doc_id = self._generate_id(entity)
            
            documents.append(doc_text)
            metadatas.append(metadata)
            ids.append(doc_id)
        
        return documents, metadatas, ids
    
    def _entity_to_document(self, entity: SecurityEntity) -> str:
        """Convert entity to searchable document text"""
        
        if entity.entity_type == EntityType.VULNERABILITY:
            return self._vulnerability_to_doc(entity)
        elif entity.entity_type == EntityType.ASSET:
            return self._asset_to_doc(entity)
        elif entity.entity_type == EntityType.EVENT:
            return self._event_to_doc(entity)
        elif entity.entity_type == EntityType.CLOUD_RESOURCE:
            return self._cloud_to_doc(entity)
        elif entity.entity_type == EntityType.USER:
            return self._user_to_doc(entity)
        elif entity.entity_type == EntityType.ROLE:
            return self._role_to_doc(entity)
        elif entity.entity_type == EntityType.PERMISSION:
            return self._permission_to_doc(entity)
        else:
            return f"{entity.entity_type}: {entity.id}"
    
    def _vulnerability_to_doc(self, vuln) -> str:
        """Convert vulnerability to document"""
        affected = ", ".join(vuln.affected_products) if vuln.affected_products else "unknown products"
        return f"""Vulnerability {vuln.cve_id}: {vuln.description}
Severity: {vuln.severity.value} (CVSS: {vuln.cvss_score})
Affected Products: {affected}
Remediation Status: {vuln.remediation_status}
Published: {vuln.published_date}"""
    
    def _asset_to_doc(self, asset) -> str:
        """Convert asset to document"""
        return f"""Asset {asset.asset_id}: {asset.hostname}
Type: {asset.asset_type}
IP Address: {asset.ip_address or 'N/A'}
Operating System: {asset.os or 'N/A'}
Owner: {asset.owner or 'N/A'}
Department: {asset.department or 'N/A'}
Criticality: {asset.criticality}
Last Scan: {asset.last_scan_date}"""
    
    def _event_to_doc(self, event) -> str:
        """Convert security event to document"""
        # Check if it's a SignInLog or SecurityEvent
        if hasattr(event, 'log_id'):
            # SignInLog
            mfa_status = "MFA enabled" if event.mfa_used else "No MFA"
            return f"""Sign-In Event {event.log_id}: {event.username}
User ID: {event.user_id}
Source IP: {event.source_ip}
Location: {event.location or 'N/A'}
Device: {event.device or 'N/A'}
Status: {event.status}
{mfa_status}
Risk Score: {event.risk_score}
Timestamp: {event.timestamp}"""
        else:
            # SecurityEvent
            return f"""Security Event {event.event_id}: {event.description}
Type: {event.event_type}
Severity: {event.severity.value}
Source: {event.source}
User: {event.user_id or 'N/A'}
Asset: {event.asset_id or 'N/A'}
Timestamp: {event.timestamp}
Raw Log: {event.raw_log or 'N/A'}"""
    
    def _cloud_to_doc(self, cloud) -> str:
        """Convert cloud resource to document"""
        compliance = "Compliant" if cloud.compliant else "Non-Compliant"
        return f"""Cloud Resource {cloud.resource_id}
Provider: {cloud.cloud_provider}
Type: {cloud.resource_type}
Setting: {cloud.setting_name} = {cloud.setting_value}
Compliance: {compliance}
Risk Level: {cloud.risk_level}
Recommendation: {cloud.recommendation or 'N/A'}"""
    
    def _user_to_doc(self, user) -> str:
        """Convert user to document"""
        status = "Active" if user.is_active else "Inactive"
        return f"""User {user.username} (ID: {user.user_id})
Email: {user.email or 'N/A'}
Department: {user.department or 'N/A'}
Status: {status}
Risk Score: {user.risk_score}"""
    
    def _role_to_doc(self, role) -> str:
        """Convert role to document"""
        return f"""Role {role.role_name} (ID: {role.role_id})
Description: {role.description or 'N/A'}
Risk Level: {role.risk_level}"""
    
    def _permission_to_doc(self, perm) -> str:
        """Convert permission to document"""
        return f"""Permission {perm.permission_id}
Role: {perm.role_id}
Resource: {perm.resource_type}
Action: {perm.action}
Scope: {perm.scope}
Risk Level: {perm.risk_level}"""
    
    def _entity_to_metadata(self, entity: SecurityEntity) -> Dict[str, Any]:
        """Extract metadata from entity"""
        metadata = {
            "entity_type": entity.entity_type.value,
            "entity_id": entity.id,
            "source": entity.metadata.get("source", "unknown")
        }
        
        # Add type-specific metadata
        if entity.entity_type == EntityType.VULNERABILITY:
            metadata["severity"] = entity.severity.value
            metadata["cvss_score"] = entity.cvss_score
            metadata["cve_id"] = entity.cve_id
        elif entity.entity_type == EntityType.ASSET:
            metadata["criticality"] = entity.criticality
            metadata["asset_type"] = entity.asset_type
        elif entity.entity_type == EntityType.EVENT:
            # Check if it's a SignInLog or SecurityEvent
            if hasattr(entity, 'log_id'):
                # SignInLog
                metadata["event_type"] = "signin"
                metadata["status"] = entity.status
                metadata["risk_score"] = entity.risk_score
            else:
                # SecurityEvent
                metadata["severity"] = entity.severity.value
                metadata["event_type"] = entity.event_type
        elif entity.entity_type == EntityType.CLOUD_RESOURCE:
            metadata["cloud_provider"] = entity.cloud_provider
            metadata["compliant"] = str(entity.compliant)
            metadata["risk_level"] = entity.risk_level
        
        return metadata
    
    def _generate_id(self, entity: SecurityEntity) -> str:
        """Generate unique ID for document"""
        self.doc_count += 1
        return f"{entity.entity_type.value}_{entity.id}_{self.doc_count}"
