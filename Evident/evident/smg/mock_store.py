"""In-memory graph store (mock implementation)"""

from typing import Dict, Any, List, Optional


class MockGraphStore:
    """In-memory graph store for development/testing"""
    
    def __init__(self):
        self.nodes = []
        self.relationships = []
        self.node_index = {}  # Index nodes by ID for quick lookup
    
    def store_graph(self, nodes: List[Dict[str, Any]], relationships: List[Dict[str, Any]]):
        """
        Store nodes and relationships in memory
        
        Args:
            nodes: List of node dictionaries
            relationships: List of relationship dictionaries
        """
        # Store nodes
        for node in nodes:
            node_id = node['properties'].get('id', '')
            if node_id and node_id not in self.node_index:
                self.nodes.append(node)
                self.node_index[node_id] = node
        
        # Store relationships
        self.relationships.extend(relationships)
        
        print(f"✓ Stored {len(nodes)} nodes and {len(relationships)} relationships in memory")
    
    def query_nodes(self, label: Optional[str] = None, properties: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query nodes by label and/or properties
        
        Args:
            label: Node label to filter by
            properties: Property filters
        
        Returns:
            List of matching nodes
        """
        results = self.nodes
        
        if label:
            results = [n for n in results if n['label'] == label]
        
        if properties:
            for key, value in properties.items():
                results = [n for n in results if n['properties'].get(key) == value]
        
        return results
    
    def query_relationships(self, rel_type: Optional[str] = None, 
                          from_id: Optional[str] = None,
                          to_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Query relationships
        
        Args:
            rel_type: Relationship type to filter by
            from_id: Source node ID
            to_id: Target node ID
        
        Returns:
            List of matching relationships
        """
        results = self.relationships
        
        if rel_type:
            results = [r for r in results if r['type'] == rel_type]
        
        if from_id:
            results = [r for r in results if r['from_id'] == from_id]
        
        if to_id:
            results = [r for r in results if r['to_id'] == to_id]
        
        return results
    
    def find_path(self, from_id: str, to_id: str, max_depth: int = 3) -> List[List[Dict[str, Any]]]:
        """
        Find paths between two nodes (simplified BFS)
        
        Args:
            from_id: Starting node ID
            to_id: Target node ID
            max_depth: Maximum path length
        
        Returns:
            List of paths (each path is a list of relationships)
        """
        # Simplified path finding - just return direct relationships for now
        paths = []
        
        # Find direct relationship
        direct_rels = [r for r in self.relationships 
                      if r['from_id'] == from_id and r['to_id'] == to_id]
        
        for rel in direct_rels:
            paths.append([rel])
        
        return paths
    
    def get_neighbors(self, node_id: str, rel_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get neighboring nodes
        
        Args:
            node_id: Node ID to find neighbors for
            rel_type: Optional relationship type filter
        
        Returns:
            List of neighbor nodes
        """
        # Find outgoing relationships
        rels = self.query_relationships(rel_type=rel_type, from_id=node_id)
        
        neighbors = []
        for rel in rels:
            to_id = rel['to_id']
            if to_id in self.node_index:
                neighbors.append(self.node_index[to_id])
        
        return neighbors
    
    def clear(self):
        """Clear all data"""
        self.nodes = []
        self.relationships = []
        self.node_index = {}
        print("✓ Cleared graph store")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics"""
        return {
            "node_count": len(self.nodes),
            "relationship_count": len(self.relationships),
            "node_labels": list(set(n['label'] for n in self.nodes)),
            "relationship_types": list(set(r['type'] for r in self.relationships))
        }
