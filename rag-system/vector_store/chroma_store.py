"""
ChromaDB Vector Store Implementation

This module provides a ChromaDB-based vector store for the RAG system.
ChromaDB is chosen for its simplicity, local deployment capability, and good performance.
"""

import logging
from typing import List, Dict, Optional, Any
import chromadb
from chromadb.config import Settings
import numpy as np

logger = logging.getLogger(__name__)


class ChromaVectorStore:
    """
    ChromaDB-based vector store implementation.

    Features:
        - Persistent storage
        - Semantic search with similarity scores
        - Metadata filtering
        - Batch operations
        - Collection management

    Example:
        ```python
        # Initialize vector store
        vector_store = ChromaVectorStore(
            persist_directory="./data/chroma",
            collection_name="media_generation_code"
        )

        # Add documents
        vector_store.add_documents([
            {
                "id": "doc1",
                "content": "Python implementation for video processing",
                "metadata": {"file_path": "backend/video.py", "type": "python"}
            }
        ])

        # Search
        results = vector_store.search("video processing", top_k=5)
        ```
    """

    def __init__(
        self,
        persist_directory: str = "./data/chroma",
        collection_name: str = "media_generation_code",
        distance_metric: str = "cosine",
    ):
        """
        Initialize ChromaDB vector store.

        Args:
            persist_directory: Directory to persist vector database
            collection_name: Name of the collection
            distance_metric: Distance metric for similarity (cosine/l2/ip)
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.distance_metric = distance_metric

        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )

        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": distance_metric}
        )

        logger.info(f"ChromaVectorStore initialized: {collection_name}")
        logger.info(f"Persist directory: {persist_directory}")

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

        Example:
            ```python
            docs = [
                {
                    "id": "doc1",
                    "content": "Python video processing implementation",
                    "metadata": {"file_path": "backend/video.py", "type": "python"}
                }
            ]
            added_ids = vector_store.add_documents(docs)
            ```
        """
        ids = []
        contents = []
        metadatas = []

        for doc in documents:
            ids.append(doc["id"])
            contents.append(doc["content"])
            metadatas.append(doc.get("metadata", {}))

        # Add to ChromaDB
        if embeddings is not None:
            self.collection.add(
                documents=contents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings
            )
        else:
            self.collection.add(
                documents=contents,
                metadatas=metadatas,
                ids=ids
            )

        logger.info(f"Added {len(documents)} documents to collection")
        return ids

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

        Example:
            ```python
            query_emb = [0.1, 0.2, 0.3, ...]  # 384-dim for MiniLM
            results = vector_store.search(query_emb, top_k=5)
            # Results: [
            #     {
            #         "id": "doc1",
            #         "content": "content text...",
            #         "metadata": {"file_path": "backend/video.py"},
            #         "score": 0.85
            #     }
            # ]
            ```
        """
        # Prepare filters
        where_clause = filters if filters else None

        # Search in ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_clause
        )

        # Format results
        formatted_results = []
        if results["ids"] and results["documents"]:
            for i in range(len(results["ids"][0])):
                result = {
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "score": float(results["distances"][0][i]) if results["distances"] else 0.0
                }
                formatted_results.append(result)

        return formatted_results

    def search_texts(
        self,
        query_texts: List[str],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[List[Dict[str, Any]]]:
        """
        Search using text queries (ChromaDB will embed internally).

        Args:
            query_texts: List of query texts
            top_k: Number of results per query
            filters: Optional metadata filters

        Returns:
            List of result lists for each query
        """
        where_clause = filters if filters else None

        results = self.collection.query(
            query_texts=query_texts,
            n_results=top_k,
            where=where_clause
        )

        # Format results for each query
        all_formatted_results = []
        for q_idx in range(len(query_texts)):
            query_results = []
            for r_idx in range(len(results["ids"][q_idx])):
                result = {
                    "id": results["ids"][q_idx][r_idx],
                    "content": results["documents"][q_idx][r_idx],
                    "metadata": results["metadatas"][q_idx][r_idx] if results["metadatas"] else {},
                    "score": float(results["distances"][q_idx][r_idx]) if results["distances"] else 0.0
                }
                query_results.append(result)
            all_formatted_results.append(query_results)

        return all_formatted_results

    def delete_documents(self, ids: List[str]) -> bool:
        """
        Delete documents by ID.

        Args:
            ids: List of document IDs to delete

        Returns:
            True if deletion was successful
        """
        try:
            self.collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} documents from collection")
            return True
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            return False

    def get_document_count(self) -> int:
        """
        Get total number of documents in collection.

        Returns:
            Number of documents
        """
        return self.collection.count()

    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the collection.

        Returns:
            Dictionary with collection info
        """
        return {
            "name": self.collection_name,
            "count": self.collection.count(),
            "metadata": self.collection.metadata
        }

    def reset_collection(self):
        """
        Clear and reset the collection.
        WARNING: This will delete all stored vectors.
        """
        try:
            # Delete and recreate collection
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": self.distance_metric}
            )
            logger.info("Collection reset successfully")
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            raise

    def __repr__(self) -> str:
        """String representation."""
        info = self.get_collection_info()
        return f"ChromaVectorStore(collection={info['name']}, documents={info['count']})"