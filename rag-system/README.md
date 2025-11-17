# Codebase RAG MCP Server

Standalone RAG (Retrieval Augmented Generation) system for any codebase. This system provides semantic search capabilities across the entire codebase, allowing AI assistants to access grounded context from your code via the Model Context Protocol (MCP). Designed for integration with Cline and other MCP-compatible tools.

## Features

- **Semantic Search**: Search codebase using embeddings and vector similarity
- **Multi-format Output**: Context building in LLM, markdown, JSON, and chat formats
- **Metadata Filtering**: Filter results by file type, path, and other metadata
- **Citation Support**: Automatic citation generation with file:line references
- **MCP Integration**: Model Context Protocol support for integration with Cline

## Components

- **Embeddings**: Sentence-transformers for semantic understanding
- **Vector Store**: ChromaDB for efficient similarity search
- **Search Engine**: Semantic + keyword hybrid search
- **Context Builder**: Optimized context formatting for LLMs
- **MCP Server**: Model Context Protocol interface

## Usage

The RAG system can be used in three ways:

1. **CLI Tool**: `uv run rag-search "your query"`
2. **API**: FastAPI server at /search endpoints
3. **MCP**: Model Context Protocol for Cline integration

## MCP Tools Available

- `search_codebase`: Search entire codebase semantically
- `build_context`: Build LLM-optimized context from search results  
- `get_codebase_stats`: Get indexing statistics
- `index_directory`: Start indexing process

## Configuration

See `config.yaml` for all configuration options including:
- Embedding model selection
- Vector store settings
- Search parameters
- API configuration
- Performance tuning