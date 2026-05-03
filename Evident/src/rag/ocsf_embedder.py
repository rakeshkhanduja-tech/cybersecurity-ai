"""Document embedder for OCSF records

Handles both native OCSFEntity objects and Evident SecurityEntity objects
that may be loaded from OCSF-formatted sample data.
"""

from typing import List, Dict, Any, Tuple
import json


class OCSFDocumentEmbedder:
    """Converts OCSF (or OCSF-compatible) entities into chunkable text for RAG indexing."""

    def __init__(self):
        self.doc_count = 0

    def embed_entities(self, entities: list) -> Tuple[List[str], List[Dict[str, Any]], List[str]]:
        documents = []
        metadatas = []
        ids = []

        for entity in entities:
            try:
                doc_text = self._entity_to_document(entity)
                metadata = self._entity_to_metadata(entity)
                doc_id = self._entity_id(entity)

                documents.append(doc_text)
                metadatas.append(metadata)
                ids.append(doc_id)
                self.doc_count += 1
            except Exception as e:
                print(f"[WARN] OCSFDocumentEmbedder: skipping entity {type(entity).__name__} — {e}")

        return documents, metadatas, ids

    # ------------------------------------------------------------------
    # Document text generation — handles both OCSFEntity and Evident entities
    # ------------------------------------------------------------------

    def _entity_to_document(self, entity) -> str:
        # Resolve class_uid safely — OCSF native vs Evident entity
        class_uid = getattr(entity, "class_uid", None)
        class_name = self._safe_str(getattr(entity, "class_name", type(entity).__name__))
        severity = self._safe_str(getattr(entity, "severity", getattr(entity, "severity_level", "Unknown")))

        # Determine title
        if class_uid == 2002:
            # Try via get_property first (OCSFEntity), then raw_data directly
            cve = self._get_property(entity, "vulnerabilities.0.cve.uid")
            if not cve:
                raw = getattr(entity, "raw_data", {}) or {}
                vulns = raw.get("vulnerabilities", [])
                if isinstance(vulns, list) and vulns:
                    cve = vulns[0].get("cve", {}).get("uid", "")
            if not cve:
                cve = getattr(entity, "cve_id", "")
            title = f"Vulnerability Finding: {cve}" if cve else "Vulnerability Finding"
        elif class_uid == 2004:
            title = f"Detection Finding: {self._get_property(entity, 'finding.title', 'Unknown')}"
        elif class_uid:
            title = f"OCSF Log [{class_name}] (class_uid={class_uid})"
        else:
            # Evident schema entity — build a readable title from whatever fields exist
            name = (getattr(entity, "title", None)
                    or getattr(entity, "name", None)
                    or getattr(entity, "cve_id", None)
                    or getattr(entity, "hostname", None)
                    or getattr(entity, "username", None)
                    or "")
            title = f"{class_name}: {name}" if name else class_name

        doc = [title]
        doc.append(f"Severity: {severity}")

        # Time
        ts = getattr(entity, "time", None) or getattr(entity, "timestamp", None)
        if ts:
            doc.append(f"Time: {ts}")

        # Device
        device = (self._get_property(entity, "device.hostname")
                  or getattr(entity, "hostname", None)
                  or getattr(entity, "ip_address", None))
        if device:
            doc.append(f"Device: {device}")

        # User
        user = (self._get_property(entity, "actor.user.name")
                or getattr(entity, "username", None)
                or getattr(entity, "user_id", None))
        if user:
            doc.append(f"User: {user}")

        # Raw payload — support both OCSFEntity.raw_data and plain dicts/Pydantic models
        raw = getattr(entity, "raw_data", None)
        if raw is None:
            try:
                raw = entity.model_dump()
            except Exception:
                try:
                    raw = vars(entity)
                except Exception:
                    raw = {}
        doc.append(f"Payload: {json.dumps(raw, default=str)[:2000]}")

        return "\n".join(doc)

    def _entity_to_metadata(self, entity) -> Dict[str, Any]:
        class_uid = getattr(entity, "class_uid", None)
        class_name = self._safe_str(
            getattr(entity, "class_name", type(entity).__name__)
        )
        meta = getattr(entity, "metadata", None) or {}
        entity_id = self._entity_id(entity)

        return {
            "entity_type": "ocsf_entity" if class_uid else type(entity).__name__.lower(),
            "entity_id": entity_id,
            "class_uid": class_uid,
            "class_name": class_name,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _entity_id(self, entity) -> str:
        """Extract a stable string ID from any entity type."""
        meta = getattr(entity, "metadata", {}) or {}
        if isinstance(meta, dict) and meta.get("id"):
            return str(meta["id"])
        for attr in ("id", "cve_id", "asset_id", "user_id", "log_id"):
            val = getattr(entity, attr, None)
            if val:
                return str(val)
        return f"{type(entity).__name__}_{self.doc_count}"

    def _safe_str(self, val) -> str:
        return str(val) if val is not None else "Unknown"

    def _get_property(self, entity, path: str, default=None):
        """Navigate dot-path on OCSFEntity or return None for Evident entities."""
        get_fn = getattr(entity, "get_property", None)
        if callable(get_fn):
            return get_fn(path, default)
        return default
