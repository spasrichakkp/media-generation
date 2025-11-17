"""
MCP RAG Server - Model Context Protocol Implementation

This module implements an MCP server that provides RAG capabilities to Cline.
It allows Cline to query the codebase and get contextual information through
a standardized protocol.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from retriever.semantic_search import SemanticSearcher
from retriever.context_builder import ContextBuilder
from embeddings.embedding_model import EmbeddingModel

logger = logging.getLogger(__name__)


class MCPTools:
    """
    MCP Tools implementation for RAG system integration.
    
    This class provides the tools that can be called via MCP protocol.
    """
    
    def __init__(self):
        """Initialize RAG components for MCP tools."""
        self.searcher: Optional[SemanticSearcher] = None
        self.context_builder: Optional[ContextBuilder] = None
        self._initialized = False
        
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize RAG system components."""
        try:
            # Initialize searcher with default configuration
            self.searcher = SemanticSearcher(
                embedding_model_name="sentence-transformers/all-MiniLM-L6-v2",
                persist_directory="./data/chroma",
                collection_name="media_generation_code",
                similarity_threshold=0.6
            )
            
            # Initialize context builder
            self.context_builder = ContextBuilder(
                max_tokens=8000,
                format_type="llm",
                include_citations=True,
                include_metadata=True
            )
            
            self._initialized = True
            logger.info("MCP RAG tools initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP RAG tools: {e}")
            raise
    
    async def search_codebase(self, query: str, top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Search the codebase for relevant information.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            filters: Optional metadata filters
            
        Returns:
            Dictionary with search results
        """
        if not self._initialized or not self.searcher:
            raise RuntimeError("RAG system not initialized")
        
        if not query or not query.strip():
            return {
                "query": query,
                "results": [],
                "error": "Query cannot be empty"
            }
        
        try:
            results = self.searcher.search(
                query=query,
                top_k=top_k,
                filters=filters,
                use_hybrid=True
            )
            
            return {
                "query": query,
                "results": results,
                "results_count": len(results),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {
                "query": query,
                "results": [],
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def build_context(self, query: str, search_results: List[Dict[str, Any]], format_type: str = "llm") -> Dict[str, str]:
        """
        Build contextual information from search results.
        
        Args:
            query: Original query
            search_results: Results from search operation
            format_type: Output format type (llm, markdown, json, chat)
            
        Returns:
            Dictionary with formatted context
        """
        if not self._initialized or not self.context_builder:
            raise RuntimeError("RAG system not initialized")
        
        try:
            # Create a temporary context builder with the specified format
            temp_builder = ContextBuilder(
                max_tokens=8000,
                format_type=format_type,
                include_citations=True,
                include_metadata=True
            )
            
            formatted_context = temp_builder.build_context(
                query=query,
                results=search_results,
                top_k=len(search_results),
                include_instructions=(format_type == "llm")
            )
            
            return {
                "query": query,
                "context": formatted_context,
                "format_type": format_type,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Context building failed: {e}")
            return {
                "query": query,
                "context": f"Error building context: {e}",
                "format_type": format_type,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_codebase_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the indexed codebase.
        
        Returns:
            Dictionary with codebase statistics
        """
        if not self._initialized or not self.searcher:
            raise RuntimeError("RAG system not initialized")
        
        try:
            stats = self.searcher.get_statistics()
            return {
                "stats": stats,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


class MCPRAGServer:
    """
    MCP Server for RAG system integration with Cline.
    
    This server implements the Model Context Protocol to provide
    RAG capabilities through standardized tool calls.
    """
    
    def __init__(self):
        """Initialize the MCP RAG server."""
        self.tools = MCPTools()
        self.server_info = {
            "name": "rag-system-mcp",
            "version": "1.0.0",
            "description": "RAG system for codebase search and context retrieval"
        }
        logger.info("MCP RAG Server initialized")
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming MCP request.
        
        Args:
            request: MCP request dictionary
            
        Returns:
            MCP response dictionary
        """
        try:
            request_type = request.get("method")
            params = request.get("params", {})
            
            if request_type == "tools/list":
                return await self._list_tools()
            elif request_type == "tools/call":
                tool_name = params.get("name")
                tool_params = params.get("arguments", {})
                return await self._call_tool(tool_name, tool_params)
            elif request_type == "ping":
                return await self._ping()
            else:
                return self._error_response(f"Unknown request type: {request_type}")
                
        except Exception as e:
            logger.error(f"Request handling failed: {e}")
            return self._error_response(str(e))
    
    async def _list_tools(self) -> Dict[str, Any]:
        """List available tools."""
        tools = [
            {
                "name": "search_codebase",
                "description": "Search the codebase for relevant information",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query text"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of results to return (default: 5)",
                            "default": 5
                        },
                        "filters": {
                            "type": "object",
                            "description": "Optional metadata filters"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "build_context",
                "description": "Build contextual information from search results for LLM consumption",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Original query"
                        },
                        "search_results": {
                            "type": "array",
                            "description": "Results from search_codebase tool"
                        },
                        "format_type": {
                            "type": "string",
                            "description": "Output format (llm, markdown, json, chat)",
                            "enum": ["llm", "markdown", "json", "chat"],
                            "default": "llm"
                        }
                    },
                    "required": ["query", "search_results"]
                }
            },
            {
                "name": "get_codebase_stats",
                "description": "Get statistics about the indexed codebase",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
        
        return {
            "result": {
                "tools": tools
            }
        }
    
    async def _call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool."""
        try:
            if tool_name == "search_codebase":
                query = params["query"]
                top_k = params.get("top_k", 5)
                filters = params.get("filters", None)
                
                result = await self.tools.search_codebase(query, top_k, filters)
                return {"result": result}
                
            elif tool_name == "build_context":
                query = params["query"]
                search_results = params["search_results"]
                format_type = params.get("format_type", "llm")
                
                result = await self.tools.build_context(query, search_results, format_type)
                return {"result": result}
                
            elif tool_name == "get_codebase_stats":
                result = await self.tools.get_codebase_stats()
                return {"result": result}
                
            else:
                return self._error_response(f"Unknown tool: {tool_name}")
                
        except KeyError as e:
            return self._error_response(f"Missing required parameter: {e}")
        except Exception as e:
            return self._error_response(f"Tool call failed: {e}")
    
    async def _ping(self) -> Dict[str, Any]:
        """Handle ping request."""
        return {
            "result": {
                "status": "ok",
                "server_info": self.server_info
            }
        }
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """Create error response."""
        return {
            "error": {
                "code": -32603,
                "message": message
            }
        }


# Global server instance
mcp_server: Optional[MCPRAGServer] = None


async def main():
    """Main entry point for MCP server."""
    global mcp_server
    
    # Initialize server
    mcp_server = MCPRAGServer()
    
    # For now, this would be integrated with actual MCP protocol
    # In a real implementation, you'd connect this to the MCP transport layer
    print("MCP RAG Server started")
    print("Available tools:")
    print("- search_codebase: Search codebase for information")
    print("- build_context: Build LLM context from search results") 
    print("- get_codebase_stats: Get codebase statistics")
    
    # Wait for requests (in real implementation, this would be the MCP loop)
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down MCP RAG Server...")


if __name__ == "__main__":
    asyncio.run(main())