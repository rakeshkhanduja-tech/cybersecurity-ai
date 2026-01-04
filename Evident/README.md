# Evident - Security Intelligence Agent

Evident is a RAG-based cybersecurity AI agent that ingests security signals from multiple sources, builds a structured memory graph, and provides intelligent security investigation capabilities through natural language queries.

## Features

- **Multi-Source Data Ingestion**: Ingests security data from 7 sources:
  - CVEs (Common Vulnerabilities and Exposures)
  - Assets Inventory
  - Security Log Events
  - Cloud Configurations
  - Sign-In Logs
  - User Roles
  - Role Permissions

- **Structured Memory Graph (SMG)**: Builds a comprehensive security knowledge graph using Neo4j, representing entities and their relationships

- **RAG Framework**: Combines vector database (ChromaDB) semantic search with graph traversal for intelligent context retrieval

- **Configurable LLM**: Supports multiple LLM providers with Gemini as default

- **Web Interface**: Interactive chat interface with signal source dashboard and graph visualization

## Architecture

```
User Query → Query Processor → Context Builder (RAG + SMG) → LLM → Response
                                      ↓
                            Vector DB + Graph DB
                                      ↑
                            Data Ingestion Pipeline
                                      ↑
                            Security Signal Sources
```

## Quick Start

### Prerequisites

- Python 3.9+
- Neo4j (optional - mock store available)
- Google Gemini API key (optional - mock LLM available)

### Installation

```bash
# Clone the repository
cd cybersecurity-ai/Evident

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys and database credentials
```

### Usage

1. **Ingest Sample Data**
```bash
python main.py --ingest
```

2. **Start Web Interface**
```bash
python main.py --serve
```

3. **Open browser to** `http://localhost:5000`

4. **Ask security questions**:
   - "Which assets are affected by critical CVEs?"
   - "What permissions does user john.doe have?"
   - "Show me failed login attempts in the last 24 hours"
   - "Which cloud resources have security misconfigurations?"

## Project Structure

```
Evident/
├── evident/                    # Main package
│   ├── config/                # Configuration management
│   ├── ingestion/             # Data ingestion module
│   ├── schema/                # Normalization schemas
│   ├── smg/                   # Structured Memory Graph
│   ├── rag/                   # RAG & Vector DB
│   ├── llm/                   # LLM integration
│   ├── agent/                 # Agent core logic
│   └── ui/                    # User interface
├── data/                      # Sample datasets
├── tests/                     # Test suite
├── requirements.txt
├── config.json               # LLM and system config
└── main.py                   # Entry point
```

## Extending to Real Data Sources

The ingestion module uses an interface-based design. To connect to real data sources:

1. Implement the `BaseSource` interface in `evident/ingestion/base_source.py`
2. Create your connector class (e.g., `SplunkConnector`, `CrowdStrikeConnector`)
3. Register it in `source_manager.py`

Example:
```python
from evident.ingestion.base_source import BaseSource

class SplunkConnector(BaseSource):
    def load(self):
        # Connect to Splunk API
        # Fetch security events
        # Return normalized data
        pass
```

## Development

```bash
# Run tests
pytest tests/ -v

# Run with mock LLM (no API key needed)
python main.py --serve --mock-llm

# Run with mock graph store (no Neo4j needed)
python main.py --serve --mock-graph
```

## License

MIT License
