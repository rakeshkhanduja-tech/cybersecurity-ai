"""Build graph nodes and edges strictly from OCSF entities."""

from typing import Dict, Any, List
from src.schema.ocsf_schema import OCSFEntity

class OCSFNodeBuilder:
    """Builds Neo4j Graph nodes from OCSF formatted objects.
    Extracts nested objects to link elements like Users, Devices, or Vulnerabilities.
    """
    
    def __init__(self):
        self.nodes = {}
    
    def build_nodes(self, entities: List[OCSFEntity]) -> List[Dict[str, Any]]:
        nodes = []
        for entity in entities:
            # We treat the main Finding/Event as a node
            node = {
                "label": entity.class_name.replace(" ", "_") if entity.class_name else "OCSF_Event",
                "properties": {
                    "id": str(entity.id),
                    "class_name": entity.class_name,
                    "class_uid": entity.class_uid,
                    "time": str(entity.time) if entity.time else "",
                    "severity": entity.severity
                }
            }
            # Capture specific fields based on class
            if entity.class_uid == 2004: # Detection Finding
                finding = entity.get_property("finding", {})
                node["properties"]["title"] = finding.get("title", "")
                node["properties"]["finding_uid"] = finding.get("uid", "")
                
            elif entity.class_uid == 2002: # Vulnerability Finding
                vuln_list = entity.get_property("vulnerabilities") or [entity.get_property("vulnerability")] or [{}]
                vuln = vuln_list[0] if isinstance(vuln_list, list) and vuln_list else vuln_list
                node["properties"]["cve"] = vuln.get("cve", {}).get("uid", "") or vuln.get("uid", "")
                node["properties"]["cvss"] = vuln.get("cvss", {}).get("base_score", 0.0) or vuln.get("cvss_score", 0.0)

            elif entity.class_uid == 3002: # Authentication
                node["properties"]["user"] = entity.get_property("actor.user.name")
                node["properties"]["src_ip"] = entity.get_property("src_endpoint.ip")
                node["properties"]["status"] = entity.get_property("status")

            elif entity.class_uid == 9002: # Security Finding
                finding = entity.get_property("finding", {})
                node["properties"]["title"] = finding.get("title", "")
                node["properties"]["finding_id"] = finding.get("uid", "")

            elif entity.class_uid == 5001: # Device Inventory
                device = entity.get_property("device", {})
                node["properties"]["hostname"] = device.get("hostname", "")
                node["properties"]["ip"] = device.get("ip", "")

            elif entity.class_uid == 6003: # Compliance Finding
                finding = entity.get_property("finding", {})
                node["properties"]["title"] = finding.get("title", "")
                node["properties"]["resource"] = entity.get_property("resource.name")

            # Avoid duplicates on the top layer nodes
            node_key = f"{node['label']}:{node['properties']['id']}"
            if node_key not in self.nodes:
                self.nodes[node_key] = node
                nodes.append(node)
                
            # Extract nested assets (Device) to build asset nodes
            device = entity.get_property("device")
            if device:
                dev_node = {
                    "label": "Asset",
                    "properties": {
                        "id": str(device.get("uid") or device.get("hostname") or "unknown_device"),
                        "hostname": device.get("hostname", ""),
                        "os": device.get("os", {}).get("name", "") if isinstance(device.get("os"), dict) else str(device.get("os", "")),
                        "ip": device.get("ip", "")
                    }
                }
                dev_key = f"Asset:{dev_node['properties']['id']}"
                if dev_key not in self.nodes:
                    self.nodes[dev_key] = dev_node
                    nodes.append(dev_node)
                    
            # Extract nested users (User)
            user = entity.get_property("actor.user") or entity.get_property("user")
            if user and isinstance(user, dict):
                user_node = {
                    "label": "User",
                    "properties": {
                        "id": str(user.get("uid") or user.get("email_addr") or user.get("name") or "unknown_user"),
                        "name": user.get("name", ""),
                        "email": user.get("email_addr", "")
                    }
                }
                usr_key = f"User:{user_node['properties']['id']}"
                if usr_key not in self.nodes:
                    self.nodes[usr_key] = user_node
                    nodes.append(user_node)

        return nodes

    def get_node_count(self) -> int:
        return len(self.nodes)
