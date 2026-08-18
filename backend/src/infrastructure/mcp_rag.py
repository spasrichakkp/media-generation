"""RAG MCP Tools provider for application use cases.

Provides access to the standalone RAG MCP system for codebase semantic search
and context building, integrated into the video generation pipeline.
"""

from ...config import get_settings
import logging

logger = logging.getLogger(__name__)

# Module-level RAG tools instance (lazily initialized)
_rag_tools: Optional[object] = None
_initialized: bool = False


def get_rag_tools() -> Optional[object]:
    """
    Get initialized RAG MCP tools instance.
    
    Returns the RAGMCPTools instance if initialized and ENABLE_RAG_CONTEXT is True,
    None otherwise. The RAG system is loaded from the standalone rag-system module.
    
    Returns:
        RAGMCPTools instance or None
    """
    global _rag_tools, _initialized
    
    if _initialized:
        return _rag_tools
    
    # Check if RAG context is enabled in settings
    try:
        settings = get_settings()
        if not getattr(settings, 'ENABLE_RAG_CONTEXT', False):
            _initialized = True  # Mark as checked, return None cached
            return None
    except Exception:
        # If settings not available, disable RAG
        _initialized = True
        return None
    
    # Attempt to initialize RAG tools from rag-system
    try:
        import sys
        import os
        
        # Add rag-system to path if not already there
        rag_system_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'rag-system')
        if rag_system_dir not in sys.path:
            sys.path.insert(0, rag_system_dir)
        
        # Import the RAG MCP server components
        from mcp_rag_server import RAGMCPTools
        from indexer.index_all import get_statistics as get_index_stats
        
        # Check if indexing has been done
        stats = get_index_stats()
        if stats.get('chunks_created', 0) == 0:
            logger.warning("RAG system not indexed - no codebase context available")
            _initialized = True
            return None
        
        # Initialize RAG tools
        _rag_tools = RAGMCPTools()
        _initialized = True
        logger.info("RAG MCP tools initialized successfully")
        return _rag_tools
        
    except ImportError as e:
        logger.warning(f"RAG system import failed: {e}. RAG context disabled.")
        _initialized = True
        return None
    except Exception as e:
        logger.error(f"Failed to initialize RAG tools: {e}")
        _initialized = True
        return None