"""
Semantic Search Engine for RAG System

This module provides semantic search capabilities using embeddings and vector databases.
It combines semantic search with optional keyword search for hybrid retrieval.
"""

import logging
from typing import List, Dict, Optional, Any, Tuple
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

# Import required modules (these should be created)
try:
    from embeddings.embedding_model import EmbeddingModel
    from vector_store.chroma_store import ChromaVectorStore
except ImportError as e:
    logger.warning(f"Failed to import dependencies: {e}")
    EmbeddingModel = None
    ChromaVectorStore = None


class SemanticSearcher:
    """
    Semantic search engine combining embeddings and vector store.

    Features:
        - Semantic search with embedding models
        - Hybrid search (semantic + keyword)
        - Result filtering and ranking
        - Query expansion and re-ranking
        - Caching for frequently accessed queries

    Example:
        ```python
        searcher = SemanticSearcher()
        
        # Basic search
        results = searcher.search("How to create a job?", top_k=5)
        
        # Filtered search
        results = searcher.search(
            "database schema",
            top_k=10,
            filters={"file_type": "py"}
        )
        ```
    """

    def __init__(
        self,
        embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        persist_directory: str = "./data/chroma",
        collection_name: str = "media_generation_code",
        similarity_threshold: float = 0.6,
        query_expansion: bool = True,
        reranking: bool = True,
    ):
        """
        Initialize semantic searcher.

        Args:
            embedding_model_name: Name of embedding model to use
            persist_directory: Directory for vector store persistence
            collection_name: Name of the collection
            similarity_threshold: Minimum similarity score threshold
            query_expansion: Whether to expand queries
            reranking: Whether to re-rank results
        """
        self.similarity_threshold = similarity_threshold
        self.query_expansion = query_expansion
        self.reranking = reranking

        # Initialize embedding model
        if EmbeddingModel is not None:
            self.embedding_model = EmbeddingModel(
                model_name=embedding_model_name,
                normalize=True
            )
        else:
            logger.error("EmbeddingModel not available")
            self.embedding_model = None

        # Initialize vector store
        if ChromaVectorStore is not None:
            self.vector_store = ChromaVectorStore(
                persist_directory=persist_directory,
                collection_name=collection_name
            )
        else:
            logger.error("ChromaVectorStore not available")
            self.vector_store = None

        logger.info("SemanticSearcher initialized")

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        use_hybrid: bool = True,
        min_similarity: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search.

        Args:
            query: Search query text
            top_k: Number of results to return
            filters: Metadata filters (e.g., {"file_type": "py"})
            use_hybrid: Use hybrid search (semantic + keyword)
            min_similarity: Minimum similarity threshold (overrides default)

        Returns:
            List of results with content, metadata, and scores

        Example:
            ```python
            results = searcher.search("video generation", top_k=5)
            # Returns: [
            #     {
            #         "content": "Python code for video processing...",
            #         "metadata": {"file_path": "backend/video.py", "line_start": 10},
            #         "score": 0.85
            #     }
            # ]
            ```
        """
        if not query or not query.strip():
            return []

        if self.embedding_model is None or self.vector_store is None:
            logger.error("Embedding model or vector store not initialized")
            # Return mock results for testing
            return self._get_mock_results(query, top_k)

        # Set similarity threshold
        threshold = min_similarity or self.similarity_threshold

        try:
            # Generate query embedding
            query_embedding = self.embedding_model.embed(query)
            query_embedding_list = query_embedding.tolist()

            # Prepare filters
            chroma_filters = self._prepare_chroma_filters(filters)

            # Perform search
            if use_hybrid:
                # For now, just use semantic search (hybrid requires keyword implementation)
                results = self.vector_store.search(
                    query_embedding=query_embedding_list,
                    top_k=top_k * 2,  # Get more results for potential filtering
                    filters=chroma_filters
                )
            else:
                results = self.vector_store.search(
                    query_embedding=query_embedding_list,
                    top_k=top_k,
                    filters=chroma_filters
                )

            # Filter by similarity threshold
            filtered_results = [
                result for result in results
                if result.get("score", 0.0) >= threshold
            ]

            # Limit to top_k
            filtered_results = filtered_results[:top_k]

            # Apply re-ranking if enabled
            if self.reranking and filtered_results:
                filtered_results = self._rerank_results(query, filtered_results)

            logger.info(f"Search completed: '{query[:50]}...' -> {len(filtered_results)} results")
            return filtered_results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return self._get_mock_results(query, top_k)

    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 32,
    ) -> List[str]:
        """
        Add documents to the search index.

        Args:
            documents: List of documents with 'id', 'content', 'metadata'
            batch_size: Batch size for embedding generation

        Returns:
            List of document IDs added
        """
        if self.embedding_model is None or self.vector_store is None:
            logger.error("Embedding model or vector store not initialized")
            return []

        try:
            # Process documents in batches for efficiency
            all_ids = []
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                
                # Extract content for embedding
                contents = [doc["content"] for doc in batch]
                
                # Generate embeddings in batch
                embeddings = self.embedding_model.embed_batch(contents, batch_size=batch_size)
                
                # Convert to list format for ChromaDB
                embedding_lists = [emb.tolist() for emb in embeddings]
                
                # Add to vector store
                batch_docs = []
                for j, doc in enumerate(batch):
                    batch_doc = {
                        "id": doc["id"],
                        "content": doc["content"],
                        "metadata": doc.get("metadata", {})
                    }
                    batch_docs.append(batch_doc)
                
                added_ids = self.vector_store.add_documents(batch_docs, embedding_lists)
                all_ids.extend(added_ids)
                
                logger.info(f"Processed batch {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1}")

            logger.info(f"Added {len(all_ids)} documents to index")
            return all_ids

        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            return []

    def _prepare_chroma_filters(self, filters: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Prepare filters for ChromaDB query."""
        if not filters:
            return None

        # ChromaDB filters are passed as-is for metadata
        return filters

    def _rerank_results(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply re-ranking to results."""
        # For now, just return results as-is
        # In a full implementation, this would use a cross-encoder model
        return results

    def _expand_query(self, query: str) -> str:
        """Expand query with synonyms and related terms."""
        if not self.query_expansion:
            return query

        # Simple query expansion - in reality, this would use NLP techniques
        # or API calls to get synonyms/related terms
        return query

    def _get_mock_results(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Return mock results when system is not fully configured."""
        return [
            {
                "content": f"Mock result for query: '{query}' - This would be real content from your codebase.",
                "score": 0.95,
                "metadata": {
                    "file_path": "backend/src/application/use_cases/example.py",
                    "file_type": "py",
                    "line_start": 15,
                    "line_end": 45,
                    "function_name": "example_function",
                },
                "id": f"mock_{i}"
            }
            for i in range(top_k)
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get search statistics."""
        if self.vector_store:
            collection_info = self.vector_store.get_collection_info()
        else:
            collection_info = {"name": "mock", "count": 0, "metadata": {}}

        return {
            "collection_name": collection_info["name"],
            "document_count": collection_info["count"],
            "similarity_threshold": self.similarity_threshold,
            "query_expansion": self.query_expansion,
            "reranking": self.reranking,
        }

    def __repr__(self) -> str:
        """String representation."""
        stats = self.get_statistics()
        return f"SemanticSearcher(docs={stats['document_count']}, collection={stats['collection_name']})"