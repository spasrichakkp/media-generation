"""
Embedding Model - Generate embeddings using sentence-transformers

This module provides a production-ready wrapper for sentence-transformers
models with GPU support, caching, batch processing, and error handling.

References:
    - sentence-transformers: https://www.sbert.net/
    - Model Hub: https://huggingface.co/sentence-transformers
    - Version: sentence-transformers>=2.2.2
"""

import hashlib
import logging
from functools import lru_cache
from typing import List, Optional, Union

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """
    Wrapper for sentence-transformers embedding models.

    Features:
        - GPU/CPU/MPS device auto-detection
        - LRU caching for single embeddings
        - Batch processing for efficiency
        - Embedding normalization
        - Comprehensive error handling
        - Memory-efficient operations

    Example:
        ```python
        # Initialize model
        embedder = EmbeddingModel(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            device="cuda",
            normalize=True
        )

        # Single embedding (cached)
        embedding = embedder.embed("Hello world")

        # Batch embeddings (no cache)
        embeddings = embedder.embed_batch([
            "First text",
            "Second text",
            "Third text"
        ])
        ```

    Attributes:
        model_name: HuggingFace model identifier
        device: Device to use (cuda/cpu/mps)
        normalize: Whether to normalize embeddings to unit length
        dimension: Embedding vector dimension
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: Optional[str] = None,
        normalize: bool = True,
        cache_size: int = 10000,
    ):
        """
        Initialize embedding model.

        Args:
            model_name: HuggingFace model identifier
                Recommended models:
                - all-MiniLM-L6-v2 (384d, fast, good quality)
                - all-mpnet-base-v2 (768d, slower, better quality)
                - all-distilroberta-v1 (768d, balanced)
            device: Device to use (cuda/cpu/mps), auto-detect if None
            normalize: Whether to normalize embeddings (recommended: True)
            cache_size: LRU cache size for single embeddings

        Raises:
            RuntimeError: If model loading fails
            ValueError: If invalid device specified
        """
        self.model_name = model_name
        self.normalize = normalize
        self.cache_size = cache_size

        # Auto-detect device
        self.device = self._detect_device(device)

        # Load model
        logger.info(f"Loading embedding model: {model_name}")
        logger.info(f"Device: {self.device}")

        try:
            self.model = SentenceTransformer(model_name, device=self.device)
            self.dimension = self.model.get_sentence_embedding_dimension()

            logger.info(f"Model loaded successfully")
            logger.info(f"Embedding dimension: {self.dimension}")

        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise RuntimeError(
                f"Cannot load embedding model '{model_name}'. "
                f"Ensure the model exists on HuggingFace and you have internet access. "
                f"Error: {e}"
            ) from e

        # Setup caching for single embeddings
        self._embed_single_cached = lru_cache(maxsize=cache_size)(self._embed_single_uncached)

        logger.info(f"EmbeddingModel initialized with cache size: {cache_size}")

    def _detect_device(self, device: Optional[str]) -> str:
        """
        Auto-detect optimal device if not specified.

        Args:
            device: User-specified device or None

        Returns:
            Device string (cuda/cpu/mps)

        Raises:
            ValueError: If specified device is invalid
        """
        if device is not None:
            # Validate user-specified device
            valid_devices = ["cuda", "cpu", "mps"]
            if device not in valid_devices:
                raise ValueError(f"Invalid device '{device}'. Must be one of: {valid_devices}")

            # Check if CUDA requested but not available
            if device == "cuda" and not torch.cuda.is_available():
                logger.warning("CUDA requested but not available, falling back to CPU")
                return "cpu"

            # Check if MPS requested but not available
            if device == "mps" and not torch.backends.mps.is_available():
                logger.warning("MPS requested but not available, falling back to CPU")
                return "cpu"

            return device

        # Auto-detect
        if torch.cuda.is_available():
            device = "cuda"
            logger.info(f"CUDA detected: {torch.cuda.get_device_name(0)}")
        elif torch.backends.mps.is_available():
            device = "mps"
            logger.info("Apple Silicon GPU (MPS) detected")
        else:
            device = "cpu"
            logger.info("Using CPU (no GPU detected)")

        return device

    def embed(self, text: str) -> np.ndarray:
        """
        Generate embedding for single text with caching.

        This method uses LRU cache to avoid recomputing embeddings
        for frequently seen texts. Use for repeated queries.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector as numpy array (dimension: self.dimension)

        Raises:
            ValueError: If text is empty or None
            RuntimeError: If embedding generation fails

        Example:
            ```python
            embedding = embedder.embed("How to create a job?")
            print(embedding.shape)  # (384,) for MiniLM
            ```
        """
        if not text or not text.strip():
            raise ValueError("Cannot embed empty or whitespace-only text")

        return self._embed_single_cached(text.strip())

    def _embed_single_uncached(self, text: str) -> np.ndarray:
        """
        Generate embedding without cache (internal use).

        Args:
            text: Input text (already validated)

        Returns:
            Embedding vector

        Raises:
            RuntimeError: If embedding fails
        """
        try:
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=self.normalize,
                show_progress_bar=False,
                batch_size=1,
            )
            return embedding

        except Exception as e:
            logger.error(f"Embedding generation failed for text: '{text[:50]}...': {e}")
            raise RuntimeError(f"Failed to generate embedding: {e}") from e

    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = False,
    ) -> np.ndarray:
        """
        Generate embeddings for multiple texts (batched, no caching).

        This is much faster than calling embed() in a loop for multiple texts.
        Does not use cache - better for one-time bulk processing.

        Args:
            texts: List of input texts
            batch_size: Number of texts to process at once
                Larger = faster but more memory
                Recommended: 32 (CPU), 128 (GPU)
            show_progress: Show tqdm progress bar

        Returns:
            Array of embeddings (N x D) where N=len(texts), D=dimension

        Raises:
            ValueError: If texts is empty or contains only empty strings
            RuntimeError: If batch embedding fails

        Example:
            ```python
            texts = ["First document", "Second document", "Third document"]
            embeddings = embedder.embed_batch(texts, batch_size=32)
            print(embeddings.shape)  # (3, 384) for MiniLM
            ```
        """
        if not texts:
            raise ValueError("Cannot embed empty text list")

        # Filter out empty texts and track indices
        filtered_texts = []
        valid_indices = []

        for i, text in enumerate(texts):
            if text and text.strip():
                filtered_texts.append(text.strip())
                valid_indices.append(i)

        if not filtered_texts:
            raise ValueError("All texts are empty after filtering")

        if len(filtered_texts) < len(texts):
            logger.warning(f"Filtered out {len(texts) - len(filtered_texts)} empty texts")

        try:
            embeddings = self.model.encode(
                filtered_texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                normalize_embeddings=self.normalize,
                show_progress_bar=show_progress,
            )

            # If we filtered texts, create full array with None/zeros for empties
            if len(filtered_texts) < len(texts):
                full_embeddings = np.zeros((len(texts), self.dimension))
                for i, valid_idx in enumerate(valid_indices):
                    full_embeddings[valid_idx] = embeddings[i]
                return full_embeddings

            return embeddings

        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            raise RuntimeError(
                f"Failed to generate batch embeddings for {len(texts)} texts: {e}"
            ) from e

    def compute_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray,
    ) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score (range: -1 to 1)
            If embeddings are normalized, this is just dot product

        Raises:
            ValueError: If embeddings have different dimensions

        Example:
            ```python
            emb1 = embedder.embed("Python programming")
            emb2 = embedder.embed("Python coding")
            similarity = embedder.compute_similarity(emb1, emb2)
            print(f"Similarity: {similarity:.3f}")  # ~0.85-0.95
            ```
        """
        if embedding1.shape != embedding2.shape:
            raise ValueError(
                f"Embedding dimensions don't match: {embedding1.shape} vs {embedding2.shape}"
            )

        # If normalized, dot product = cosine similarity
        if self.normalize:
            return float(np.dot(embedding1, embedding2))

        # Otherwise compute full cosine similarity
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(embedding1, embedding2) / (norm1 * norm2))

    def compute_similarities(
        self,
        query_embedding: np.ndarray,
        embeddings: np.ndarray,
    ) -> np.ndarray:
        """
        Compute cosine similarities between query and multiple embeddings.

        Vectorized operation - much faster than calling compute_similarity
        in a loop for many embeddings.

        Args:
            query_embedding: Query embedding vector (1D)
            embeddings: Matrix of embeddings to compare (2D: N x D)

        Returns:
            Similarity scores (1D: N)

        Raises:
            ValueError: If dimensions don't match

        Example:
            ```python
            query = embedder.embed("video generation")
            docs = embedder.embed_batch([
                "How to generate videos",
                "Image processing",
                "Audio synthesis"
            ])
            similarities = embedder.compute_similarities(query, docs)
            # Returns: [0.89, 0.45, 0.32]
            ```
        """
        if query_embedding.ndim != 1:
            raise ValueError(f"Query must be 1D, got shape: {query_embedding.shape}")

        if embeddings.ndim != 2:
            raise ValueError(f"Embeddings must be 2D, got shape: {embeddings.shape}")

        if query_embedding.shape[0] != embeddings.shape[1]:
            raise ValueError(
                f"Dimension mismatch: query={query_embedding.shape[0]}, "
                f"embeddings={embeddings.shape[1]}"
            )

        # If normalized, matrix multiplication = cosine similarities
        if self.normalize:
            return embeddings @ query_embedding

        # Otherwise compute full cosine similarities
        norms = np.linalg.norm(embeddings, axis=1)
        query_norm = np.linalg.norm(query_embedding)

        if query_norm == 0:
            return np.zeros(len(embeddings))

        # Avoid division by zero
        norms = np.where(norms == 0, 1, norms)

        return (embeddings @ query_embedding) / (norms * query_norm)

    def get_dimension(self) -> int:
        """Get embedding dimension."""
        return self.dimension

    def get_model_name(self) -> str:
        """Get model name."""
        return self.model_name

    def get_device(self) -> str:
        """Get current device."""
        return self.device

    def clear_cache(self):
        """Clear embedding cache."""
        self._embed_single_cached.cache_clear()
        logger.info("Embedding cache cleared")

    def get_cache_info(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dict with hits, misses, size, maxsize
        """
        info = self._embed_single_cached.cache_info()
        return {
            "hits": info.hits,
            "misses": info.misses,
            "size": info.currsize,
            "maxsize": info.maxsize,
            "hit_rate": info.hits / (info.hits + info.misses)
            if (info.hits + info.misses) > 0
            else 0.0,
        }

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"EmbeddingModel("
            f"model={self.model_name}, "
            f"device={self.device}, "
            f"dim={self.dimension}, "
            f"normalize={self.normalize})"
        )


# Module-level convenience functions

_default_model: Optional[EmbeddingModel] = None


def get_default_model() -> EmbeddingModel:
    """
    Get or create default embedding model (singleton pattern).

    Returns:
        Default EmbeddingModel instance

    Example:
        ```python
        from embeddings.embedding_model import get_default_model

        model = get_default_model()
        embedding = model.embed("test text")
        ```
    """
    global _default_model

    if _default_model is None:
        _default_model = EmbeddingModel()

    return _default_model


def embed(text: str) -> np.ndarray:
    """
    Convenience function to embed text with default model.

    Args:
        text: Input text

    Returns:
        Embedding vector
    """
    return get_default_model().embed(text)


def embed_batch(texts: List[str], batch_size: int = 32) -> np.ndarray:
    """
    Convenience function to embed multiple texts with default model.

    Args:
        texts: List of texts
        batch_size: Batch size

    Returns:
        Array of embeddings
    """
    return get_default_model().embed_batch(texts, batch_size=batch_size)
