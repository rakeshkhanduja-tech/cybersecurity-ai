"""SMG Manager for security graph operations"""

from typing import Dict, Any, List, Optional
from evident.schema import SecurityEntity
from evident.smg.node_builder import SecurityNodeBuilder
from evident.smg.relationship_builder import SecurityRelationshipBuilder
from evident.smg.mock_store import MockGraphStore
from evident.config import config_loader


class SMGManager:
    """Manages the Security Memory Graph"""
    
    def __init__(self, use_mock: bool = None):
        # Determine whether to use mock store
        if use_mock is None:
            use_mock = config_loader.is_mock_mode("graph")
        
        # Initialize graph store
        if use_mock:
            self.graph_store = MockGraphStore()
            print("✓ Using mock graph store")
        else:
            # TODO: Initialize real Neo4j store
            print("⚠️  Neo4j not implemented yet, using mock store")
            self.graph_store = MockGraphStore()
        
        # Initialize builders
        self.node_builder = SecurityNodeBuilder()
        self.relationship_builder = SecurityRelationshipBuilder()
    
    def build_graph(self, entities: List[SecurityEntity]):
        """
        Build security graph from entities
        
        Args:
            entities: List of SecurityEntity objects
        """
        print(f"\nBuilding security graph from {len(entities)} entities...")
        
        # Build nodes
        nodes = self.node_builder.build_nodes(entities)
        print(f"✓ Built {len(nodes)} nodes")
        
        # Build relationships
        relationships = self.relationship_builder.build_relationships(entities)
        print(f"✓ Built {len(relationships)} relationships")
        
        # Store in graph
        self.graph_store.store_graph(nodes, relationships)
        
        print(f"✓ Security graph construction complete")
    
    def query_graph(self, query_type: str, **params) -> List[Dict[str, Any]]:
        """
        Query the security graph
        
        Args:
            query_type: Type of query (nodes, relationships, neighbors, path)
            **params: Query parameters
        
        Returns:
            Query results
        """
        if query_type == "nodes":
            return self.graph_store.query_nodes(
                label=params.get("label"),
                properties=params.get("properties")
            )
        
        elif query_type == "relationships":
            return self.graph_store.query_relationships(
                rel_type=params.get("rel_type"),
                from_id=params.get("from_id"),
                to_id=params.get("to_id")
            )
        
        elif query_type == "neighbors":
            return self.graph_store.get_neighbors(
                node_id=params.get("node_id"),
                rel_type=params.get("rel_type")
            )
        
        elif query_type == "path":
            return self.graph_store.find_path(
                from_id=params.get("from_id"),
                to_id=params.get("to_id"),
                max_depth=params.get("max_depth", 3)
            )
        
        return []
    
    def get_assets_affected_by_cve(self, cve_id: str) -> List[Dict[str, Any]]:
        """Get all assets affected by a specific CVE"""
        # Find vulnerability node
        vuln_nodes = self.graph_store.query_nodes(
            label="Vulnerability",
            properties={"cve_id": cve_id}
        )
        
        if not vuln_nodes:
            return []
        
        vuln_id = vuln_nodes[0]['properties']['id']
        
        # Find AFFECTS relationships
        affects_rels = self.graph_store.query_relationships(
            rel_type="AFFECTS",
            from_id=vuln_id
        )
        
        # Get affected assets
        assets = []
        for rel in affects_rels:
            asset_id = rel['to_id']
            if asset_id in self.graph_store.node_index:
                assets.append(self.graph_store.node_index[asset_id])
        
        return assets
    
    def get_user_permissions(self, username: str) -> List[Dict[str, Any]]:
        """Get all permissions for a user"""
        # Find user node
        user_nodes = self.graph_store.query_nodes(
            label="User",
            properties={"username": username}
        )
        
        if not user_nodes:
            return []
        
        user_id = user_nodes[0]['properties']['id']
        
        # Find user's roles
        role_rels = self.graph_store.query_relationships(
            rel_type="HAS_ROLE",
            from_id=user_id
        )
        
        # Get permissions for each role
        permissions = []
        for role_rel in role_rels:
            role_id = role_rel['to_id']
            perm_rels = self.graph_store.query_relationships(
                rel_type="HAS_PERMISSION",
                from_id=role_id
            )
            
            for perm_rel in perm_rels:
                perm_id = perm_rel['to_id']
                if perm_id in self.graph_store.node_index:
                    permissions.append(self.graph_store.node_index[perm_id])
        
        return permissions
    
    def get_user_assets(self, username: str) -> List[Dict[str, Any]]:
        """Get all assets owned by a user"""
        # Find user node
        user_nodes = self.graph_store.query_nodes(
            label="User",
            properties={"username": username}
        )
        
        if not user_nodes:
            return []
        
        user_id = user_nodes[0]['properties']['id']
        
        # Find OWNS relationships
        owns_rels = self.graph_store.query_relationships(
            rel_type="OWNS",
            from_id=user_id
        )
        
        # Get assets
        assets = []
        for rel in owns_rels:
            asset_id = rel['to_id']
            if asset_id in self.graph_store.node_index:
                assets.append(self.graph_store.node_index[asset_id])
        
        return assets
    
    def get_events_for_asset(self, asset_id: str) -> List[Dict[str, Any]]:
        """Get all events involving an asset"""
        events = []
        
        # Find INVOLVES relationships pointing to this asset
        involves_rels = self.graph_store.query_relationships(
            rel_type="INVOLVES",
            to_id=asset_id
        )
        
        for rel in involves_rels:
            event_id = rel['from_id']
            if event_id in self.graph_store.node_index:
                events.append(self.graph_store.node_index[event_id])
        
        return events
    
    def clear_graph(self):
        """Clear all graph data"""
        self.graph_store.clear()
        self.node_builder = SecurityNodeBuilder()
        self.relationship_builder = SecurityRelationshipBuilder()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics"""
        return self.graph_store.get_stats()
