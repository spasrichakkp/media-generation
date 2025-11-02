"""
Semantic Chunker - Chunk code and documents intelligently

This module provides semantic chunking that splits content at natural boundaries
like function definitions, class definitions, or section headers.
"""

from typing import List, Dict, Optional


class SemanticChunker:
    """Semantic chunker for code and documentation."""

    def __init__(self, config: Dict):
        """Initialize chunker with configuration.

        Args:
            config: Configuration dictionary with chunking settings
        """
        self.config = config
        self.code_config = config.get("chunking", {}).get("code", {})
        self.docs_config = config.get("chunking", {}).get("docs", {})

    def chunk_code(self, content: str, language: str = "python") -> List[Dict[str, any]]:
        """Chunk code content at function/class boundaries.

        Args:
            content: Source code content
            language: Programming language (python, sql, etc.)

        Returns:
            List of chunks with metadata
        """
        max_chunk_size = self.code_config.get("max_chunk_size", 1000)
        overlap = self.code_config.get("overlap", 100)

        chunks = []
        lines = content.split("\n")

        if language == "python":
            chunks = self._chunk_python(lines, max_chunk_size, overlap)
        else:
            chunks = self._chunk_generic(lines, max_chunk_size, overlap)

        return chunks

    def chunk_markdown(self, content: str) -> List[Dict[str, any]]:
        """Chunk markdown content at header boundaries.

        Args:
            content: Markdown content

        Returns:
            List of chunks with metadata
        """
        max_chunk_size = self.docs_config.get("max_chunk_size", 500)
        overlap = self.docs_config.get("overlap", 50)

        lines = content.split("\n")
        chunks = []
        current_chunk = []
        current_size = 0
        line_start = 1

        for i, line in enumerate(lines, 1):
            # Check if this is a header
            is_header = line.startswith("#")

            # If header and we have content, save current chunk
            if is_header and current_chunk:
                chunk_text = "\n".join(current_chunk)
                chunks.append(
                    {
                        "text": chunk_text,
                        "line_start": line_start,
                        "line_end": i - 1,
                        "size": len(chunk_text),
                    }
                )
                # Start new chunk with overlap
                if overlap > 0:
                    current_chunk = current_chunk[-overlap:]
                else:
                    current_chunk = []
                line_start = i - len(current_chunk)

            current_chunk.append(line)
            current_size += len(line)

            # If chunk is too large, split it
            if current_size > max_chunk_size:
                chunk_text = "\n".join(current_chunk)
                chunks.append(
                    {
                        "text": chunk_text,
                        "line_start": line_start,
                        "line_end": i,
                        "size": len(chunk_text),
                    }
                )
                # Start new chunk with overlap
                if overlap > 0:
                    current_chunk = current_chunk[-overlap:]
                else:
                    current_chunk = []
                line_start = i - len(current_chunk) + 1
                current_size = sum(len(l) for l in current_chunk)

        # Add remaining chunk
        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                {
                    "text": chunk_text,
                    "line_start": line_start,
                    "line_end": len(lines),
                    "size": len(chunk_text),
                }
            )

        return chunks

    def chunk_text(self, content: str) -> List[Dict[str, any]]:
        """Chunk plain text content.

        Args:
            content: Text content

        Returns:
            List of chunks with metadata
        """
        max_chunk_size = self.docs_config.get("max_chunk_size", 500)
        overlap = self.docs_config.get("overlap", 50)

        lines = content.split("\n")
        return self._chunk_generic(lines, max_chunk_size, overlap)

    def _chunk_python(self, lines: List[str], max_size: int, overlap: int) -> List[Dict[str, any]]:
        """Chunk Python code at function/class boundaries.

        Args:
            lines: Lines of Python code
            max_size: Maximum chunk size in characters
            overlap: Overlap size in characters

        Returns:
            List of chunks
        """
        chunks = []
        current_chunk = []
        current_size = 0
        line_start = 1
        in_function = False
        indent_level = 0

        for i, line in enumerate(lines, 1):
            # Detect function or class definitions
            stripped = line.lstrip()
            if stripped.startswith(("def ", "class ", "async def ")):
                # If we have accumulated content, save it
                if current_chunk and current_size > 0:
                    chunk_text = "\n".join(current_chunk)
                    chunks.append(
                        {
                            "text": chunk_text,
                            "line_start": line_start,
                            "line_end": i - 1,
                            "size": len(chunk_text),
                        }
                    )
                    # Start new chunk with overlap
                    if overlap > 0 and len(current_chunk) > 5:
                        current_chunk = current_chunk[-5:]
                    else:
                        current_chunk = []
                    line_start = i - len(current_chunk)
                    current_size = sum(len(l) for l in current_chunk)

                in_function = True
                indent_level = len(line) - len(stripped)

            current_chunk.append(line)
            current_size += len(line)

            # If chunk is too large, split it
            if current_size > max_size:
                chunk_text = "\n".join(current_chunk)
                chunks.append(
                    {
                        "text": chunk_text,
                        "line_start": line_start,
                        "line_end": i,
                        "size": len(chunk_text),
                    }
                )
                # Start new chunk
                current_chunk = []
                line_start = i + 1
                current_size = 0
                in_function = False

        # Add remaining chunk
        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                {
                    "text": chunk_text,
                    "line_start": line_start,
                    "line_end": len(lines),
                    "size": len(chunk_text),
                }
            )

        return chunks

    def _chunk_generic(self, lines: List[str], max_size: int, overlap: int) -> List[Dict[str, any]]:
        """Generic line-based chunking.

        Args:
            lines: Lines of text
            max_size: Maximum chunk size in characters
            overlap: Overlap size in characters

        Returns:
            List of chunks
        """
        chunks = []
        current_chunk = []
        current_size = 0
        line_start = 1

        for i, line in enumerate(lines, 1):
            current_chunk.append(line)
            current_size += len(line)

            # If chunk is large enough, save it
            if current_size >= max_size:
                chunk_text = "\n".join(current_chunk)
                chunks.append(
                    {
                        "text": chunk_text,
                        "line_start": line_start,
                        "line_end": i,
                        "size": len(chunk_text),
                    }
                )

                # Calculate overlap
                if overlap > 0:
                    overlap_lines = []
                    overlap_size = 0
                    for l in reversed(current_chunk):
                        if overlap_size < overlap:
                            overlap_lines.insert(0, l)
                            overlap_size += len(l)
                        else:
                            break
                    current_chunk = overlap_lines
                    current_size = overlap_size
                    line_start = i - len(overlap_lines) + 1
                else:
                    current_chunk = []
                    current_size = 0
                    line_start = i + 1

        # Add remaining chunk
        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                {
                    "text": chunk_text,
                    "line_start": line_start,
                    "line_end": len(lines),
                    "size": len(chunk_text),
                }
            )

        return chunks
