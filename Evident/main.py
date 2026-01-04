"""
Evident - Security Intelligence Agent
Main entry point
"""

import argparse
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evident.agent import EvidentAgent


def run_cli():
    """Run CLI mode"""
    print("\n" + "="*60)
    print("Evident - Security Intelligence Agent (CLI Mode)")
    print("="*60 + "\n")
    
    # Initialize agent
    agent = EvidentAgent(use_mock_llm=True, use_mock_graph=True)
    
    # Ingest data
    agent.ingest_data()
    
    # Build intelligence
    agent.build_intelligence()
    
    # Interactive query loop
    print("\n" + "="*60)
    print("Ready for queries! Type 'exit' to quit, 'stats' for statistics")
    print("="*60 + "\n")
    
    while True:
        try:
            question = input("\n🔍 Your question: ").strip()
            
            if not question:
                continue
            
            if question.lower() in ['exit', 'quit', 'q']:
                print("\nGoodbye!")
                break
            
            if question.lower() == 'stats':
                stats = agent.get_stats()
                print("\n📊 Agent Statistics:")
                print(f"  Total Entities: {stats['total_entities']}")
                print(f"  Vector DB Docs: {stats['rag_stats'].get('vector_store', {}).get('document_count', 0)}")
                print(f"  Graph Nodes: {stats['smg_stats'].get('node_count', 0)}")
                print(f"  Graph Edges: {stats['smg_stats'].get('relationship_count', 0)}")
                continue
            
            # Query agent
            response = agent.query(question)
            
            print(f"\n🤖 Evident: {response['answer']}")
            print(f"\n📌 Sources: {', '.join(response['sources'])}")
            print(f"💡 Model: {response['model']} | Tokens: {response['tokens']} | Cost: ${response['cost']:.4f}")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


def run_web():
    """Run web UI mode"""
    from evident.ui.app import app
    
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(f"\n{'='*60}")
    print(f"Starting Evident Web Interface on http://localhost:{port}")
    print(f"{'='*60}\n")
    
    app.run(host='0.0.0.0', port=port, debug=debug)


def run_ingest_only():
    """Run data ingestion only"""
    print("\n" + "="*60)
    print("Evident - Data Ingestion Mode")
    print("="*60 + "\n")
    
    agent = EvidentAgent(use_mock_llm=True, use_mock_graph=True)
    agent.ingest_data()
    agent.build_intelligence()
    
    stats = agent.get_stats()
    print("\n" + "="*60)
    print("Ingestion Complete!")
    print("="*60)
    print(f"Total Entities: {stats['total_entities']}")
    print(f"Vector DB Docs: {stats['rag_stats'].get('vector_store', {}).get('document_count', 0)}")
    print(f"Graph Nodes: {stats['smg_stats'].get('node_count', 0)}")
    print(f"Graph Edges: {stats['smg_stats'].get('relationship_count', 0)}")
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(description='Evident - Security Intelligence Agent')
    parser.add_argument('--mode', choices=['cli', 'web', 'ingest'], default='web',
                       help='Run mode: cli (interactive), web (web UI), ingest (data ingestion only)')
    parser.add_argument('--mock-llm', action='store_true',
                       help='Use mock LLM instead of Gemini')
    parser.add_argument('--port', type=int, default=5000,
                       help='Port for web server (default: 5000)')
    
    args = parser.parse_args()
    
    # Set environment variables
    if args.mock_llm:
        os.environ['USE_MOCK_LLM'] = 'True'
    
    if args.port:
        os.environ['FLASK_PORT'] = str(args.port)
    
    # Run appropriate mode
    if args.mode == 'cli':
        run_cli()
    elif args.mode == 'web':
        run_web()
    elif args.mode == 'ingest':
        run_ingest_only()


if __name__ == '__main__':
    main()
