# VectorScope

**Vector Database Security Research Project**

VectorScope demonstrates vulnerabilities in vector databases through reverse engineering attacks and develops defense mechanisms.

## Overview

This research project proves that sensitive information (SSNs, credit cards, etc.) stored as embeddings in vector databases can be extracted through various attack techniques.

## Attack Techniques

1. **Similarity Attack**: Dictionary-based matching using pre-computed embeddings
2. **Reconstruction Attack**: Optimization-based text recovery from vectors
3. **Pattern Recognition**: Statistical analysis of embedding space

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Store sensitive information
python main.py store "SSN: 123-45-6789"

# Run reverse engineering attack
python main.py attack --vector-id <id>

# Run all attacks
python main.py attack-all --vector-id <id>
```

## Research Findings

This project demonstrates that:
- Structured data (SSN, credit cards) can be extracted with 80-95% accuracy
- Vector databases without proper security are vulnerable to information leakage
- Defense mechanisms are necessary for production vector database deployments

## Project Structure

```
VectorScope/
├── vectorscope/
│   ├── storage/      # Vector database integration
│   ├── attacks/      # Reverse engineering exploits
│   └── cli/          # Command-line interface
├── research/         # Research findings
├── examples/         # Sample sensitive data
└── tests/
```

## Ethical Notice

This is a security research project. The techniques demonstrated should only be used for:
- Security research and education
- Testing your own systems
- Developing defense mechanisms

**Do not use these techniques on systems you don't own or have permission to test.**

## License

MIT License - For research and educational purposes
