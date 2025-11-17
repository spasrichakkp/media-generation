"""
Vector Store Base Interface

This module defines the abstract interface for vector stores in the RAG system.
Different vector store implementations (Chroma, FAISS, etc.) should inherit from this.
"""

import logging
from typing import List, Dict, Optional, Any, Protocol
import numpy as np

logger = logging.getLogger(__name__)


class VectorStore(Protocol):
    """
    Abstract interface for vector stores.

    All vector store implementations should inherit from this protocol
    to ensure consistent behavior across different backends.
    """

    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: Optional[List[List[float]]] = None,
    ) -> List[str]:
        """
        Add documents to the vector store.

        Args:
            documents: List of documents with 'id', 'content', and 'metadata'
            embeddings: Optional pre-computed embeddings

        Returns:
            List of document IDs that were added
        """
        ...

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filters: Optional metadata filters

        Returns:
            List of results with content, metadata, and similarity scores
        """
        ...

    def delete_documents(self, ids: List[str]) -> bool:
        """
        Delete documents by ID.

        Args:
            ids: List of document IDs to delete

        Returns:
            True if deletion was successful
        """
        ...

    def get_document_count(self) -> int:
        """
        Get total number of documents in collection.

        Returns:
            Number of documents
        """
        ...

    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the collection.

        Returns:
            Dictionary with collection info
        """
        ...


# Import specific implementations
from .chroma_store import ChromaVectorStore

__all__ = ["VectorStore", "ChromaVectorStore"]