# Standalone RAG MCP Server Integration Guide

This document explains how to integrate the standalone RAG system with Cline using the Model Context Protocol (MCP).

## Overview

The standalone RAG (Retrieval Augmented Generation) system provides semantic search capabilities for your entire codebase, allowing AI assistants to access grounded context from your actual code. The system is accessible via MCP (Model Context Protocol) for seamless integration with Cline and runs independently of any specific project. This package can be run with `uvx` for easy deployment.

## Available MCP Tools

### 1. `search_codebase`
Search the entire codebase for relevant information using semantic search.

**Parameters:**
- `query`: (required) Search query text describing what you're looking for in the codebase
- `top_k`: (optional) Number of results to return (default: 5, max: 20)
- `filters`: (optional) Metadata filters (e.g., {"file_type": "py", "file_path": "backend"})
- `min_similarity`: (optional) Minimum similarity threshold (0.0 to 1.0)

**Example:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "search_codebase",
    "arguments": {
      "query": "How to create a video generation job?",
      "top_k": 5,
      "filters": {"file_type": "py"}
    }
  }
}
```

### 2. `build_context`
Build optimized context from search results for LLM consumption.

**Parameters:**
- `query`: (required) Original query that generated the search results
- `search_results`: (required) Results returned from search_codebase tool
- `format_type`: (optional) Output format ("llm", "markdown", "json", "chat") - default: "llm"
- `include_instructions`: (optional) Whether to include LLM instructions - default: true

**Example:**
```json
{
  "method": "tools/call", 
  "params": {
    "name": "build_context",
    "arguments": {
      "query": "How to create a video generation job?",
      "search_results": [...], // results from search_codebase
      "format_type": "llm"
    }
  }
}
```

### 3. `get_codebase_stats`
Get statistics about the indexed codebase including document count and collection info.

**Example:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "get_codebase_stats",
    "arguments": {}
  }
}
```

### 4. `index_directory`
Start indexing process for a directory (requires separate full indexer).

**Parameters:**
- `directory_path`: (required) Path to directory to index
- `force_reindex`: (optional) Whether to force reindexing all files - default: false

## Integration with Cline

### Method 1: Using uvx (Recommended)
Run the MCP server using uvx without installation:

```bash
# Run directly from the repository
uvx codebase-rag-mcp

# Or if installed in a different location
cd rag-system
uvx .
```

### Method 2: Direct MCP Server
Run the MCP server directly:

```bash
cd rag-system
source .venv/bin/activate
python mcp_rag_server.py
```

### Method 3: Using the CLI Command
If properly installed as a package:

```bash
uv run rag-mcp
```

### Method 4: Using uv with the script
```bash
uv run python mcp_rag_server.py
```

## Configuration

The RAG system is configured via `config.yaml` which controls:

- Embedding model selection
- Vector store settings  
- Search parameters
- API configuration
- Performance tuning

## Usage Examples

### Basic Search
```bash
# Start the MCP server
python mcp_rag_server.py

# Then Cline can call the search tool with query
```

### Index Your Codebase
Before searching, you need to index your codebase:

```bash
# Index the entire project
uv run rag-index --full

# Or index specific directory
uv run rag-index --path ../backend

# Incremental updates
uv run rag-index --incremental
```

## Architecture

```
Cline (MCP Client) 
    ↓
MCP Protocol 
    ↓  
RAG MCP Server (mcp_rag_server.py)
    ↓
├── Semantic Search Engine
├── Vector Store (ChromaDB)  
├── Embedding Model
└── Context Builder
    ↓
Codebase Index (./data/chroma/)
```

## Development & Testing

### Test the MCP Server
```bash
python mcp_rag_server.py test
```

### Run API Server (Alternative Interface)
```bash
uv run rag-serve
# Available at http://localhost:8001
```

### Run CLI Tool (Direct Interface)  
```bash
uv run rag-search "your query here"
```

## Troubleshooting

### Common Issues:
1. **No results found**: Make sure to index your codebase first with `rag-index --full`
2. **Slow performance**: Check that embedding models are downloaded and cached
3. **Connection issues**: Ensure the MCP server is running and accessible

### Performance Tips:
- Use appropriate embedding models based on your needs (accuracy vs speed)
- Configure batch sizes for optimal performance
- Monitor vector store performance with the monitoring endpoints

## Security Considerations

- The MCP server runs locally and only accesses the indexed codebase
- No external connections are made during search operations
- All data is stored locally in the configured vector store
- Configure authentication if exposing the API externally