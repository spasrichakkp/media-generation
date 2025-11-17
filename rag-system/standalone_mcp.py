#!/usr/bin/env python3
"""
Standalone RAG MCP Server Entry Point

This module provides the main entry point for running the RAG system
as a standalone MCP server using uvx. It can be run directly or via uvx.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the current directory to path to import local modules
sys.path.insert(0, str(Path(__file__).parent))

# Import the MCP server
from mcp_rag_server import run_mcp_server


def main():
    """
    Main entry point for the standalone RAG MCP server.
    
    This function can be called:
    - Directly: python -m standalone_rag_mcp
    - Via uvx: uvx path/to/this/directory
    - As installed package: uv run rag-mcp
    """
    print("🚀 Starting Standalone RAG MCP Server", file=sys.stderr)
    print("📋 Available tools: search_codebase, build_context, get_codebase_stats, index_directory", file=sys.stderr)
    print("💡 Use with Cline MCP integration for codebase search capabilities", file=sys.stderr)
    print("❌ Press Ctrl+C to stop", file=sys.stderr)
    
    try:
        # Run the MCP server
        asyncio.run(run_mcp_server())
    except KeyboardInterrupt:
        print("\n🛑 RAG MCP Server stopped by user", file=sys.stderr)
    except Exception as e:
        print(f"💥 Error running RAG MCP Server: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()