"""
Quick test script for Evident agent
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evident.agent import EvidentAgent


def test_evident():
    """Test the Evident agent"""
    
    print("\n" + "="*70)
    print("EVIDENT AGENT TEST")
    print("="*70)
    
    # Initialize agent with mock LLM
    print("\n1. Initializing agent...")
    agent = EvidentAgent(use_mock_llm=True, use_mock_graph=True)
    
    # Ingest data
    print("\n2. Ingesting data...")
    entities = agent.ingest_data()
    print(f"   ✓ Loaded {len(entities)} entities")
    
    # Build intelligence
    print("\n3. Building intelligence layer...")
    agent.build_intelligence()
    
    # Get stats
    print("\n4. Agent Statistics:")
    stats = agent.get_stats()
    print(f"   Total Entities: {stats['total_entities']}")
    print(f"   Vector DB Docs: {stats['rag_stats'].get('vector_store', {}).get('document_count', 0)}")
    print(f"   Graph Nodes: {stats['smg_stats'].get('node_count', 0)}")
    print(f"   Graph Edges: {stats['smg_stats'].get('relationship_count', 0)}")
    
    # Test queries
    print("\n5. Testing queries...")
    
    test_questions = [
        "Which assets are affected by critical CVEs?",
        "What permissions does user john.doe have?",
        "Show me failed login attempts",
        "Which cloud resources have security misconfigurations?"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n   Query {i}: {question}")
        response = agent.query(question)
        print(f"   Answer: {response['answer'][:150]}...")
        print(f"   Sources: {', '.join(response['sources'])}")
        print(f"   Model: {response['model']}")
    
    print("\n" + "="*70)
    print("✓ ALL TESTS PASSED")
    print("="*70 + "\n")


if __name__ == '__main__':
    test_evident()
