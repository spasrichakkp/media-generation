"""
Context Builder for RAG System

This module builds contextual information for LLMs from search results,
formatting them appropriately for different use cases (chat assistants, etc.).
"""

import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    Builds optimized context from search results for LLM consumption.

    Features:
        - Multiple output formats (LLM context, chat messages, markdown)
        - Context formatting and cleaning
        - Citation generation
        - Content relevance scoring
        - Context length management
        - Metadata enrichment

    Example:
        ```python
        builder = ContextBuilder(max_tokens=4096, format_type="llm")
        
        # Build context from search results
        context = builder.build_context(
            query="How to create a job?",
            results=search_results,
            include_metadata=True
        )
        ```
    """

    def __init__(
        self,
        max_tokens: int = 8000,
        format_type: str = "llm",
        include_citations: bool = True,
        include_metadata: bool = True,
        preserve_structure: bool = True,
    ):
        """
        Initialize context builder.

        Args:
            max_tokens: Maximum tokens to include in context
            format_type: Output format ('llm', 'chat', 'markdown', 'json')
            include_citations: Include citations in output
            include_metadata: Include metadata with results
            preserve_structure: Preserve code structure and formatting
        """
        self.max_tokens = max_tokens
        self.format_type = format_type
        self.include_citations = include_citations
        self.include_metadata = include_metadata
        self.preserve_structure = preserve_structure

        # Token estimation (rough approximation: 1 token ~ 4 characters for code)
        self.chars_per_token = 4

    def build_context(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: Optional[int] = None,
        include_query: bool = True,
        include_instructions: bool = True,
        min_score: float = 0.0,
    ) -> str:
        """
        Build context from search results.

        Args:
            query: Original search query
            results: Search results from semantic search
            top_k: Maximum number of results to include
            include_query: Include original query in context
            include_instructions: Include LLM instructions
            min_score: Minimum relevance score threshold

        Returns:
            Formatted context string
        """
        if not results:
            return self._format_no_results(query)

        # Filter results by minimum score
        filtered_results = [
            r for r in results
            if r.get("score", 0.0) >= min_score
        ]

        if not filtered_results:
            return self._format_no_results(query)

        # Limit to top_k if specified
        if top_k:
            filtered_results = filtered_results[:top_k]

        # Build context based on format type
        if self.format_type == "llm":
            return self._build_llm_context(query, filtered_results, include_query, include_instructions)
        elif self.format_type == "chat":
            return self._build_chat_context(query, filtered_results, include_query)
        elif self.format_type == "markdown":
            return self._build_markdown_context(query, filtered_results)
        elif self.format_type == "json":
            return self._build_json_context(query, filtered_results)
        else:
            return self._build_llm_context(query, filtered_results, include_query, include_instructions)

    def _build_llm_context(
        self,
        query: str,
        results: List[Dict[str, Any]],
        include_query: bool = True,
        include_instructions: bool = True,
    ) -> str:
        """Build context optimized for LLM consumption."""
        parts = []

        # Add instructions
        if include_instructions:
            parts.append(self._get_llm_instructions())

        # Add query
        if include_query:
            parts.append(f"**Query:** {query}\n")

        # Add context header
        parts.append(f"**Relevant Context (top {len(results)} results):**\n")

        # Add each result
        for i, result in enumerate(results, 1):
            parts.append(self._format_result_for_llm(result, i))

        # Add footer
        parts.append(self._get_context_footer(results))

        return "\n".join(parts)

    def _build_chat_context(
        self,
        query: str,
        results: List[Dict[str, Any]],
        include_query: bool = True,
    ) -> str:
        """Build context optimized for chat applications."""
        parts = []

        # Add query
        if include_query:
            parts.append(f"Query: {query}\n")

        # Add results in chat-friendly format
        for i, result in enumerate(results, 1):
            parts.append(self._format_result_for_chat(result, i))

        return "\n".join(parts)

    def _build_markdown_context(
        self,
        query: str,
        results: List[Dict[str, Any]],
    ) -> str:
        """Build context in markdown format."""
        parts = [
            f"# RAG Search Results for: {query}\n",
            f"*Found {len(results)} relevant results*\n"
        ]

        for i, result in enumerate(results, 1):
            parts.append(self._format_result_as_markdown(result, i))

        return "\n".join(parts)

    def _build_json_context(
        self,
        query: str,
        results: List[Dict[str, Any]],
    ) -> str:
        """Build context as formatted JSON."""
        import json

        context_obj = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "results_count": len(results),
            "results": [
                self._format_result_as_dict(result)
                for result in results
            ]
        }

        return json.dumps(context_obj, indent=2, ensure_ascii=False)

    def _format_result_for_llm(self, result: Dict[str, Any], index: int) -> str:
        """Format a single result for LLM context."""
        metadata = result.get("metadata", {})
        content = result.get("content", "")
        score = result.get("score", 0.0)

        lines = [f"---"]
        lines.append(f"**Result #{index}**")

        # Add citation
        if self.include_citations:
            citation = self._format_citation(metadata)
            lines.append(f"**Source:** {citation}")

        # Add relevance score
        lines.append(f"**Relevance:** {score:.3f}")

        # Add metadata
        if self.include_metadata:
            meta_parts = []
            if metadata.get("file_path"):
                meta_parts.append(f"Path: `{metadata['file_path']}`")
            if metadata.get("file_type"):
                meta_parts.append(f"Type: {metadata['file_type']}")
            if metadata.get("function_name"):
                meta_parts.append(f"Function: `{metadata['function_name']}`")
            if metadata.get("class_name"):
                meta_parts.append(f"Class: `{metadata['class_name']}`")
            
            if meta_parts:
                lines.append(f"**Metadata:** {', '.join(meta_parts)}")

        # Add content with proper formatting
        lines.append(f"\n```{metadata.get('file_type', 'text')}")
        lines.append(content.strip())
        lines.append("```\n")

        return "\n".join(lines)

    def _format_result_for_chat(self, result: Dict[str, Any], index: int) -> str:
        """Format a single result for chat."""
        metadata = result.get("metadata", {})
        content = result.get("content", "")
        score = result.get("score", 0.0)

        citation = self._format_citation(metadata)
        
        lines = [
            f"🔍 Result {index} ({score:.2f})",
            f"📄 Source: {citation}",
            f"📝 Content:",
            f"```\n{content.strip()}\n```",
            ""
        ]

        return "\n".join(lines)

    def _format_result_as_markdown(self, result: Dict[str, Any], index: int) -> str:
        """Format a single result as markdown."""
        metadata = result.get("metadata", {})
        content = result.get("content", "")
        score = result.get("score", 0.0)

        lines = [
            f"## Result {index} (Score: {score:.3f})",
            ""
        ]

        # Add metadata
        meta_info = []
        if metadata.get("file_path"):
            meta_info.append(f"**File:** `{metadata['file_path']}`")
        if metadata.get("file_type"):
            meta_info.append(f"**Type:** `{metadata['file_type']}`")
        if metadata.get("function_name"):
            meta_info.append(f"**Function:** `{metadata['function_name']}`")
        if metadata.get("class_name"):
            meta_info.append(f"**Class:** `{metadata['class_name']}`")

        if meta_info:
            lines.append(" | ".join(meta_info))
            lines.append("")

        # Add content
        lines.append("### Content")
        lines.append(f"```{metadata.get('file_type', 'text')}")
        lines.append(content.strip())
        lines.append("```")
        lines.append("")

        return "\n".join(lines)

    def _format_result_as_dict(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format a single result as dictionary for JSON."""
        return {
            "content": result.get("content", ""),
            "score": result.get("score", 0.0),
            "metadata": result.get("metadata", {}),
            "formatted_citation": self._format_citation(result.get("metadata", {}))
        }

    def _format_citation(self, metadata: Dict[str, Any]) -> str:
        """Format citation from metadata."""
        if not metadata:
            return "unknown"

        file_path = metadata.get("file_path", "unknown")
        line_start = metadata.get("line_start")
        line_end = metadata.get("line_end")

        if line_start and line_end:
            return f"{file_path}:{line_start}-{line_end}"
        else:
            return file_path

    def _get_llm_instructions(self) -> str:
        """Get instructions for LLM consumption."""
        return """---
**INSTRUCTIONS FOR AI ASSISTANT:**

You are a code assistant with access to the Media Generation Platform codebase.
Use ONLY the context provided below to answer questions.
Cite sources using [file:line-range] format.
If information is not in the context, say "Not found in provided context."
Be specific and reference actual code patterns shown.
Maintain consistency with existing architecture.

---
"""

    def _get_context_footer(self, results: List[Dict[str, Any]]) -> str:
        """Get context footer with citations."""
        lines = [
            "\n---",
            "**CITATIONS:**"
        ]

        for i, result in enumerate(results, 1):
            metadata = result.get("metadata", {})
            citation = self._format_citation(metadata)
            lines.append(f"[{i}] {citation}")

        lines.extend([
            "\n---",
            "*All content above is from the actual codebase. Use it to provide grounded answers.*",
            "---"
        ])

        return "\n".join(lines)

    def _format_no_results(self, query: str) -> str:
        """Format message when no results found."""
        if self.format_type == "json":
            import json
            return json.dumps({
                "query": query,
                "results_count": 0,
                "message": "No relevant results found in codebase"
            }, indent=2)
        else:
            return f"""---
**Query:** {query}

**Result:** ⚠️  No relevant results found in the indexed codebase.

**Suggestions:**
- Try different keywords
- Use broader search terms  
- Check if the code has been indexed properly
- Search for related concepts

---
"""

    def estimate_token_count(self, text: str) -> int:
        """
        Estimate token count for text.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated number of tokens
        """
        return len(text) // self.chars_per_token

    def truncate_context(self, context: str, max_tokens: Optional[int] = None) -> str:
        """
        Truncate context to fit within token limit.

        Args:
            context: Context string to truncate
            max_tokens: Override maximum tokens (uses instance default if None)

        Returns:
            Truncated context
        """
        target_max = max_tokens or self.max_tokens
        current_tokens = self.estimate_token_count(context)

        if current_tokens <= target_max:
            return context

        # Simple truncation - in practice, you'd want more sophisticated approaches
        # like truncating individual results while preserving citations
        chars_per_token = self.chars_per_token
        max_chars = target_max * chars_per_token
        
        # Find a reasonable truncation point (try to end at sentence boundary)
        truncated = context[:max_chars]
        
        # Try to find a good cutoff point
        last_sentence = truncated.rfind('.')
        if last_sentence > max_chars * 0.8:  # Only truncate if we can keep most content
            truncated = truncated[:last_sentence + 1]

        logger.warning(f"Context truncated from {current_tokens} to {self.estimate_token_count(truncated)} tokens")

        return truncated + "\n\n[Context was truncated due to length limitations]"

    def build_summarized_context(
        self,
        query: str,
        results: List[Dict[str, Any]],
        max_results: int = 5,
    ) -> str:
        """
        Build a summarized context focusing on the most relevant results.

        Args:
            query: Original query
            results: Search results
            max_results: Maximum results to include

        Returns:
            Summarized context string
        """
        # Sort by score if not already sorted
        sorted_results = sorted(results, key=lambda x: x.get('score', 0.0), reverse=True)
        
        # Take top results
        top_results = sorted_results[:max_results]
        
        # Build basic context
        context = self.build_context(
            query=query,
            results=top_results,
            top_k=max_results,
            include_instructions=True
        )
        
        # Truncate if necessary
        return self.truncate_context(context)

    def __repr__(self) -> str:
        """String representation."""
        return f"ContextBuilder(format={self.format_type}, max_tokens={self.max_tokens})"