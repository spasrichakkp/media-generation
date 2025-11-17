"""
RAG API - FastAPI Implementation

This module provides a REST API for the RAG system with search capabilities.
"""

import logging
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from pathlib import Path
import yaml

# Add parent directory to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import RAG components
from retriever.semantic_search import SemanticSearcher
from retriever.context_builder import ContextBuilder
from embeddings.embedding_model import EmbeddingModel

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="RAG System API",
    description="Retrieval Augmented Generation API for code search and context retrieval",
    version="0.1.0"
)

# Global searcher instance
searcher: Optional[SemanticSearcher] = None
context_builder: Optional[ContextBuilder] = None


class SearchRequest(BaseModel):
    """Request model for search endpoint."""
    query: str
    top_k: int = Query(5, ge=1, le=50, description="Number of results to return")
    filters: Optional[Dict[str, Any]] = None
    use_hybrid: bool = True
    min_similarity: Optional[float] = None


class SearchResponse(BaseModel):
    """Response model for search endpoint."""
    query: str
    results: List[Dict[str, Any]]
    results_count: int
    execution_time_ms: float


class AddDocumentsRequest(BaseModel):
    """Request model for adding documents."""
    documents: List[Dict[str, Any]]
    batch_size: int = 32


class AddDocumentsResponse(BaseModel):
    """Response model for adding documents."""
    added_count: int
    document_ids: List[str]


def initialize_searcher():
    """Initialize the semantic searcher with configuration."""
    global searcher, context_builder
    
    # Load configuration
    config_path = Path(__file__).parent.parent / "config.yaml"
    if config_path.exists():
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    else:
        # Use defaults
        config = {
            "embeddings": {"model_name": "sentence-transformers/all-MiniLM-L6-v2"},
            "vector_store": {
                "chromadb": {
                    "persist_directory": "./data/chroma",
                    "collection_name": "media_generation_code"
                }
            },
            "search": {"similarity_threshold": 0.6}
        }

    # Initialize searcher
    searcher = SemanticSearcher(
        embedding_model_name=config["embeddings"]["model_name"],
        persist_directory=config["vector_store"]["chromadb"]["persist_directory"],
        collection_name=config["vector_store"]["chromadb"]["collection_name"],
        similarity_threshold=config["search"]["similarity_threshold"]
    )

    # Initialize context builder
    context_builder = ContextBuilder(
        max_tokens=config.get("context_builder", {}).get("max_context_tokens", 8000)
    )

    logger.info("RAG searcher initialized")


@app.on_event("startup")
async def startup_event():
    """Initialize searcher on startup."""
    try:
        initialize_searcher()
        logger.info("RAG API started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize searcher: {e}")
        raise


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    if searcher is None:
        raise HTTPException(status_code=500, detail="Searcher not initialized")
    
    stats = searcher.get_statistics()
    return {
        "status": "healthy",
        "searcher_ready": True,
        "document_count": stats["document_count"],
        "collection_name": stats["collection_name"]
    }


@app.get("/search/{query:path}")
async def quick_search(query: str, top_k: int = 5) -> SearchResponse:
    """Quick search endpoint with path parameter."""
    if searcher is None:
        raise HTTPException(status_code=500, detail="Searcher not initialized")
    
    import time
    start_time = time.time()

    try:
        results = searcher.search(query, top_k=top_k)
        execution_time_ms = (time.time() - start_time) * 1000

        return SearchResponse(
            query=query,
            results=results,
            results_count=len(results),
            execution_time_ms=execution_time_ms
        )
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search")
async def search(request: SearchRequest) -> SearchResponse:
    """Search endpoint with JSON request."""
    if searcher is None:
        raise HTTPException(status_code=500, detail="Searcher not initialized")
    
    import time
    start_time = time.time()

    try:
        results = searcher.search(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
            use_hybrid=request.use_hybrid,
            min_similarity=request.min_similarity
        )
        execution_time_ms = (time.time() - start_time) * 1000

        return SearchResponse(
            query=request.query,
            results=results,
            results_count=len(results),
            execution_time_ms=execution_time_ms
        )
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/add")
async def add_documents(request: AddDocumentsRequest) -> AddDocumentsResponse:
    """Add documents to the vector store."""
    if searcher is None:
        raise HTTPException(status_code=500, detail="Searcher not initialized")
    
    try:
        added_ids = searcher.add_documents(request.documents, request.batch_size)
        
        return AddDocumentsResponse(
            added_count=len(added_ids),
            document_ids=added_ids
        )
    except Exception as e:
        logger.error(f"Failed to add documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_statistics() -> Dict[str, Any]:
    """Get statistics about the RAG system."""
    if searcher is None:
        raise HTTPException(status_code=500, detail="Searcher not initialized")
    
    return searcher.get_statistics()


@app.post("/context/build")
async def build_context(
    query: str = Query(..., description="Query for context building"),
    results_json: str = Query(..., description="JSON string of search results"),
    format_type: str = Query("llm", description="Output format: llm, chat, markdown, json")
) -> Dict[str, str]:
    """Build context from search results."""
    import json
    
    if context_builder is None or searcher is None:
        raise HTTPException(status_code=500, detail="Context builder not initialized")
    
    try:
        results = json.loads(results_json)
        context = context_builder.build_context(
            query=query,
            results=results,
            top_k=5,
            include_instructions=True
        )
        
        return {"context": context}
    except Exception as e:
        logger.error(f"Context building failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Add more endpoints as needed
# - Index management
# - Collection operations
# - Configuration endpoints
# - Batch operations

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)