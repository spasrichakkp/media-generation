"""
MCP RAG Server - Production Implementation

This module implements a production-ready MCP server for the RAG system,
designed for integration with Cline's Model Context Protocol.
"""

import asyncio
import json
import logging
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import signal

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from retriever.semantic_search import SemanticSearcher
from retriever.context_builder import ContextBuilder
from embeddings.embedding_model import EmbeddingModel

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create logs directory if it doesn't exist
logs_dir = Path("data/logs")
logs_dir.mkdir(parents=True, exist_ok=True)

# Set up file logging
file_handler = logging.FileHandler(logs_dir / "mcp_rag_server.log")
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


class RAGMCPTools:
    """
    MCP Tools for RAG System - Provides code search and context building capabilities.
    """
    
    def __init__(self):
        """Initialize RAG components for MCP tools."""
        self.searcher: Optional[SemanticSearcher] = None
        self.context_builder: Optional[ContextBuilder] = None
        self._initialized = False
        
        # Load configuration
        self._load_config()
        
        # Initialize components
        self._initialize_components()
    
    def _load_config(self):
        """Load configuration from config.yaml."""
        config_path = Path(__file__).parent / "config.yaml"
        self.config = {
            "embeddings": {
                "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                "normalize": True
            },
            "vector_store": {
                "chromadb": {
                    "persist_directory": "./data/chroma",
                    "collection_name": "media_generation_code"
                }
            },
            "search": {
                "similarity_threshold": 0.6,
                "default_top_k": 5
            },
            "context_builder": {
                "max_tokens": 8000
            }
        }
        
        if config_path.exists():
            import yaml
            try:
                with open(config_path, "r") as f:
                    yaml_config = yaml.safe_load(f)
                    # Merge with defaults
                    self.config.update(yaml_config)
            except Exception as e:
                logger.warning(f"Failed to load config.yaml, using defaults: {e}")
    
    def _initialize_components(self):
        """Initialize RAG system components."""
        try:
            # Initialize searcher
            embeddings_config = self.config["embeddings"]
            vector_store_config = self.config["vector_store"]["chromadb"]
            search_config = self.config["search"]
            
            self.searcher = SemanticSearcher(
                embedding_model_name=embeddings_config["model_name"],
                persist_directory=vector_store_config["persist_directory"],
                collection_name=vector_store_config["collection_name"],
                similarity_threshold=search_config["similarity_threshold"]
            )
            
            # Initialize context builder
            self.context_builder = ContextBuilder(
                max_tokens=self.config["context_builder"].get("max_context_tokens", 8000),
                format_type="llm",
                include_citations=True,
                include_metadata=True
            )
            
            self._initialized = True
            logger.info("RAG MCP tools initialized successfully")
            logger.info(f"Collection: {vector_store_config['collection_name']}")
            logger.info(f"Documents in index: {self.searcher.get_statistics()['document_count']}")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG components: {e}")
            raise
    
    async def search_codebase(
        self, 
        query: str, 
        top_k: Optional[int] = None, 
        filters: Optional[Dict[str, Any]] = None,
        min_similarity: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Search the codebase for relevant information.
        
        Args:
            query: Search query text
            top_k: Number of results to return (default from config)
            filters: Optional metadata filters (e.g., {"file_type": "py"})
            min_similarity: Minimum similarity threshold
            
        Returns:
            Dictionary with search results
        """
        if not self._initialized or not self.searcher:
            return self._error_result("RAG system not initialized properly")
        
        start_time = datetime.now()
        
        if not query or not query.strip():
            return self._error_result("Query cannot be empty")
        
        try:
            # Use default top_k if not provided
            effective_top_k = top_k or self.config["search"]["default_top_k"]
            
            results = self.searcher.search(
                query=query,
                top_k=effective_top_k,
                filters=filters,
                use_hybrid=True,
                min_similarity=min_similarity
            )
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000  # ms
            
            logger.info(f"Search completed: '{query[:50]}...' -> {len(results)} results in {execution_time:.2f}ms")
            
            return {
                "success": True,
                "query": query,
                "results": results,
                "results_count": len(results),
                "execution_time_ms": execution_time,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return self._error_result(f"Search failed: {str(e)}")
    
    async def build_context(
        self, 
        query: str, 
        search_results: List[Dict[str, Any]], 
        format_type: str = "llm",
        include_instructions: bool = True
    ) -> Dict[str, Any]:
        """
        Build contextual information from search results.
        
        Args:
            query: Original query
            search_results: Results from search operation
            format_type: Output format type (llm, markdown, json, chat)
            include_instructions: Whether to include LLM instructions
            
        Returns:
            Dictionary with formatted context
        """
        if not self._initialized or not self.context_builder:
            return self._error_result("RAG system not initialized properly")
        
        start_time = datetime.now()
        
        try:
            # Validate inputs
            if not query or not query.strip():
                return self._error_result("Query cannot be empty")
            
            if not search_results:
                return {
                    "success": True,
                    "query": query,
                    "context": f"No results provided for query: {query}",
                    "format_type": format_type,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Build context with specified format
            formatted_context = self.context_builder.build_context(
                query=query,
                results=search_results,
                top_k=len(search_results),
                include_query=True,
                include_instructions=include_instructions
            )
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000  # ms
            
            logger.info(f"Context built for query: '{query[:50]}...' in {execution_time:.2f}ms")
            
            return {
                "success": True,
                "query": query,
                "context": formatted_context,
                "format_type": format_type,
                "results_count": len(search_results),
                "execution_time_ms": execution_time,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Context building failed: {e}")
            return self._error_result(f"Context building failed: {str(e)}")
    
    async def get_codebase_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the indexed codebase.
        
        Returns:
            Dictionary with codebase statistics
        """
        if not self._initialized or not self.searcher:
            return self._error_result("RAG system not initialized properly")
        
        start_time = datetime.now()
        
        try:
            stats = self.searcher.get_statistics()
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000  # ms
            
            return {
                "success": True,
                "stats": stats,
                "execution_time_ms": execution_time,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return self._error_result(f"Failed to get stats: {str(e)}")
    
    async def index_directory(
        self,
        directory_path: str,
        force_reindex: bool = False
    ) -> Dict[str, Any]:
        """
        Index files in a directory (simplified version for MCP).
        
        Args:
            directory_path: Path to directory to index
            force_reindex: Whether to force reindexing
            
        Returns:
            Dictionary with indexing results
        """
        if not self._initialized or not self.searcher:
            return self._error_result("RAG system not initialized properly")
        
        start_time = datetime.now()
        
        try:
            # This would be a simplified indexing method
            # In a full implementation, you'd use the full indexer
            import os
            
            if not os.path.exists(directory_path):
                return self._error_result(f"Directory does not exist: {directory_path}")
            
            # For now, return a message indicating this would be implemented
            # with the full indexer in a production system
            return {
                "success": True,
                "message": f"Indexing would start for: {directory_path}",
                "warning": "Full indexing requires the full indexer module which should be run separately",
                "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Indexing failed: {e}")
            return self._error_result(f"Indexing failed: {str(e)}")
    
    def _error_result(self, message: str) -> Dict[str, Any]:
        """Create an error result dictionary."""
        return {
            "success": False,
            "error": message,
            "timestamp": datetime.now().isoformat()
        }


class RAGMCPHandler:
    """
    MCP Handler for RAG System - Processes MCP protocol requests.
    """
    
    def __init__(self):
        """Initialize the MCP handler."""
        self.tools = RAGMCPTools()
        self.server_info = {
            "name": "codebase-rag-mcp",
            "version": "1.0.0",
            "description": "Standalone RAG system for codebase search and context retrieval for Cline - runs independently of any project",
            "capabilities": [
                "codebase search",
                "context building",
                "document retrieval",
                "code statistics"
            ]
        }
        logger.info("RAG MCP Handler initialized")
    
    async def handle_request(self, request: Union[str, Dict[str, Any]]) -> str:
        """
        Handle incoming MCP request and return JSON response.
        
        Args:
            request: MCP request (string or dict)
            
        Returns:
            JSON response string
        """
        try:
            # Parse request if it's a string
            if isinstance(request, str):
                request_dict = json.loads(request)
            else:
                request_dict = request
            
            method = request_dict.get("method")
            params = request_dict.get("params", {})
            
            logger.debug(f"Processing MCP request: {method}")
            
            if method == "tools/list":
                response = await self._list_tools()
            elif method == "tools/call":
                response = await self._call_tool(params)
            elif method == "mcp/initialize":
                response = await self._initialize(params)
            elif method == "server/ping":
                response = await self._ping()
            elif method == "server/info":
                response = await self._server_info()
            else:
                response = self._error_response(f"Unknown method: {method}")
        
        except json.JSONDecodeError:
            response = self._error_response("Invalid JSON in request")
        except Exception as e:
            logger.error(f"Request handling failed: {e}")
            response = self._error_response(f"Request handling failed: {str(e)}")
        
        # Serialize response
        try:
            return json.dumps(response, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to serialize response: {e}")
            return json.dumps(self._error_response(f"Serialization failed: {str(e)}"))
    
    async def _list_tools(self) -> Dict[str, Any]:
        """List available tools."""
        tools = [
            {
                "name": "search_codebase",
                "description": "Search the entire codebase for relevant information using semantic search",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query text describing what you're looking for in the codebase"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of results to return (default: 5, max: 20)",
                            "default": 5,
                            "minimum": 1,
                            "maximum": 20
                        },
                        "filters": {
                            "type": "object",
                            "description": "Optional metadata filters (e.g., {'file_type': 'py', 'file_path': 'backend'})",
                            "properties": {
                                "file_type": {"type": "string", "description": "Filter by file extension (py, md, etc.)"},
                                "file_path": {"type": "string", "description": "Filter by path containing this text"}
                            }
                        },
                        "min_similarity": {
                            "type": "number",
                            "description": "Minimum similarity threshold (0.0 to 1.0)",
                            "minimum": 0.0,
                            "maximum": 1.0
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "build_context",
                "description": "Build optimized context from search results for LLM consumption",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Original query that generated the search results"
                        },
                        "search_results": {
                            "type": "array",
                            "description": "Results returned from search_codebase tool",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "content": {"type": "string"},
                                    "metadata": {"type": "object"},
                                    "score": {"type": "number"}
                                }
                            }
                        },
                        "format_type": {
                            "type": "string",
                            "description": "Output format for context",
                            "enum": ["llm", "markdown", "json", "chat"],
                            "default": "llm"
                        },
                        "include_instructions": {
                            "type": "boolean",
                            "description": "Whether to include LLM instructions in context",
                            "default": True
                        }
                    },
                    "required": ["query", "search_results"]
                }
            },
            {
                "name": "get_codebase_stats",
                "description": "Get statistics about the indexed codebase including document count and collection info",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "index_directory",
                "description": "Start indexing process for a directory (requires separate full indexer)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "directory_path": {
                            "type": "string",
                            "description": "Path to directory to index"
                        },
                        "force_reindex": {
                            "type": "boolean",
                            "description": "Whether to force reindexing all files",
                            "default": False
                        }
                    },
                    "required": ["directory_path"]
                }
            }
        ]
        
        return {
            "result": {
                "tools": tools
            }
        }
    
    async def _call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool."""
        try:
            tool_name = params.get("name")
            tool_params = params.get("arguments", {})
            
            logger.info(f"Calling tool: {tool_name}")
            
            if tool_name == "search_codebase":
                result = await self.tools.search_codebase(
                    query=tool_params.get("query"),
                    top_k=tool_params.get("top_k"),
                    filters=tool_params.get("filters"),
                    min_similarity=tool_params.get("min_similarity")
                )
            elif tool_name == "build_context":
                result = await self.tools.build_context(
                    query=tool_params.get("query"),
                    search_results=tool_params.get("search_results", []),
                    format_type=tool_params.get("format_type", "llm"),
                    include_instructions=tool_params.get("include_instructions", True)
                )
            elif tool_name == "get_codebase_stats":
                result = await self.tools.get_codebase_stats()
            elif tool_name == "index_directory":
                result = await self.tools.index_directory(
                    directory_path=tool_params.get("directory_path"),
                    force_reindex=tool_params.get("force_reindex", False)
                )
            else:
                return self._error_response(f"Unknown tool: {tool_name}")
            
            return {"result": result}
            
        except KeyError as e:
            return self._error_response(f"Missing required parameter: {e}")
        except Exception as e:
            logger.error(f"Tool call failed: {e}")
            return self._error_response(f"Tool call failed: {str(e)}")
    
    async def _initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialization."""
        return {
            "result": {
                "capabilities": {
                    "tools": True
                },
                "server_info": self.server_info
            }
        }
    
    async def _ping(self) -> Dict[str, Any]:
        """Handle ping request."""
        return {
            "result": {
                "status": "ok"
            }
        }
    
    async def _server_info(self) -> Dict[str, Any]:
        """Handle server info request."""
        return {
            "result": self.server_info
        }
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """Create error response."""
        return {
            "error": {
                "code": -32603,  # Internal error
                "message": message
            }
        }


# For Cline integration, you would typically have a main execution that reads from stdin
# and writes to stdout, following the MCP protocol

async def run_mcp_server():
    """
    Run the MCP server for Cline integration.
    This function reads requests from stdin and writes responses to stdout.
    """
    handler = RAGMCPHandler()
    logger.info("MCP RAG Server started - waiting for requests")
    
    # Signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        # In a real implementation, you might want to clean up resources
        exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Read from stdin in a loop
        while True:
            try:
                # Read a line (MCP protocol typically sends one request per line)
                line = sys.stdin.readline()
                
                if not line:
                    # EOF - stdin closed
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                # Process the request
                response = await handler.handle_request(line)
                
                # Write response to stdout (followed by newline for MCP protocol)
                print(response, flush=True)
                
            except (KeyboardInterrupt, EOFError):
                break
            except Exception as e:
                logger.error(f"Error processing request: {e}")
                error_response = json.dumps(handler._error_response(f"Request processing error: {str(e)}"))
                print(error_response, flush=True)
    
    except Exception as e:
        logger.error(f"Critical error in MCP server: {e}")
        # Write error response to stdout
        error_response = json.dumps({
            "error": {
                "code": -32603,
                "message": f"Critical server error: {str(e)}"
            }
        })
        print(error_response, flush=True)
    
    finally:
        logger.info("MCP RAG Server shutting down")


def main():
    """Main entry point for the MCP server."""
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Run in test mode
        asyncio.run(test_server())
    else:
        # Run as MCP server
        asyncio.run(run_mcp_server())


async def test_server():
    """Test the MCP server functionality."""
    print("Testing RAG MCP Server...")
    
    handler = RAGMCPHandler()
    
    # Test 1: List tools
    print("\n1. Testing tools/list...")
    request = {"method": "tools/list", "params": {}}
    response = await handler.handle_request(request)
    print(f"Response: {response}")
    
    # Test 2: Search (if there are documents indexed)
    print("\n2. Testing search_codebase...")
    search_request = {
        "method": "tools/call",
        "params": {
            "name": "search_codebase",
            "arguments": {
                "query": "test search",
                "top_k": 3
            }
        }
    }
    search_response = await handler.handle_request(search_request)
    print(f"Search response: {search_response}")
    
    # Test 3: Get stats
    print("\n3. Testing get_codebase_stats...")
    stats_request = {
        "method": "tools/call",
        "params": {
            "name": "get_codebase_stats",
            "arguments": {}
        }
    }
    stats_response = await handler.handle_request(stats_request)
    print(f"Stats response: {stats_response}")
    
    print("\nTesting completed!")


if __name__ == "__main__":
    main()