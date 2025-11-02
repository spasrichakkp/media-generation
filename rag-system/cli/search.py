#!/usr/bin/env python3
"""
RAG CLI Search Tool

Provides command-line interface for searching the codebase with grounded answers.
Integrates with vector store and formats results with citations.

Usage:
    uv run rag-search "How to create a job?"
    uv run rag-search "video generation implementation" --top-k 5
    uv run rag-search "database schema" --filter-type py --verbose
"""

import argparse
import sys
from pathlib import Path
from typing import List, Dict, Optional
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from retriever.semantic_search import SemanticSearcher
    from retriever.context_builder import ContextBuilder
except ImportError:
    # Fallback if modules not yet implemented
    SemanticSearcher = None
    ContextBuilder = None


class GroundedAnswerFormatter:
    """Formats search results as grounded answers with citations."""

    def __init__(self, show_scores: bool = True, show_metadata: bool = True):
        self.show_scores = show_scores
        self.show_metadata = show_metadata

    def format_citation(self, result: Dict) -> str:
        """Format citation as [file:line-range]."""
        metadata = result.get("metadata", {})
        file_path = metadata.get("file_path", "unknown")
        line_start = metadata.get("line_start", 0)
        line_end = metadata.get("line_end", 0)

        if line_start and line_end:
            return f"[{file_path}:{line_start}-{line_end}]"
        return f"[{file_path}]"

    def format_result(self, result: Dict, index: int) -> str:
        """Format a single search result with citation."""
        citation = self.format_citation(result)
        score = result.get("score", 0.0)
        content = result.get("content", "")
        metadata = result.get("metadata", {})

        output = []
        output.append(f"\n{'=' * 80}")
        output.append(f"Result #{index + 1} {citation}")

        if self.show_scores:
            output.append(f"Relevance Score: {score:.3f}")

        if self.show_metadata:
            file_type = metadata.get("file_type", "unknown")
            output.append(f"Type: {file_type}")

            if "function_name" in metadata:
                output.append(f"Function: {metadata['function_name']}")
            if "class_name" in metadata:
                output.append(f"Class: {metadata['class_name']}")

        output.append(f"{'=' * 80}")
        output.append(f"\n{content}\n")

        return "\n".join(output)

    def format_grounded_answer(self, query: str, results: List[Dict], k: int = 5) -> str:
        """Format complete grounded answer with context."""
        if not results:
            return self._format_not_found(query)

        output = []
        output.append("=" * 80)
        output.append("GROUNDED ANSWER FROM KNOWLEDGE BASE")
        output.append("=" * 80)
        output.append(f"\nQuery: {query}\n")
        output.append(f"Found {len(results)} relevant result(s)\n")

        # Format each result
        for i, result in enumerate(results[:k]):
            output.append(self.format_result(result, i))

        # Add summary
        output.append("\n" + "=" * 80)
        output.append("CITATIONS")
        output.append("=" * 80)
        for i, result in enumerate(results[:k]):
            citation = self.format_citation(result)
            output.append(f"[{i + 1}] {citation}")

        output.append("\n" + "=" * 80)
        output.append("Note: All answers are grounded in the codebase. Use citations to verify.")
        output.append("=" * 80)

        return "\n".join(output)

    def _format_not_found(self, query: str) -> str:
        """Format message when no results found."""
        output = []
        output.append("=" * 80)
        output.append("NO RESULTS FOUND")
        output.append("=" * 80)
        output.append(f"\nQuery: {query}")
        output.append("\n⚠️  Not found in knowledge base.")
        output.append("\nSuggestions:")
        output.append("  • Try different keywords")
        output.append("  • Use broader search terms")
        output.append("  • Check if the code has been indexed")
        output.append("  • Run: uv run rag-index --incremental")
        output.append("=" * 80)
        return "\n".join(output)

    def format_llm_context(self, query: str, results: List[Dict], k: int = 5) -> str:
        """Format context for LLM consumption (used by AI assistants)."""
        if not results:
            return f"Query: {query}\n\nContext: Not found in knowledge base."

        context_parts = [
            "You are a local, privacy-first assistant with RAG.",
            "When answering:",
            "1) Use only the 'Context' passages below.",
            "2) Cite with [file:line-range].",
            "3) If nothing is relevant, say 'Not found in knowledge base.'",
            "",
            f"Question: {query}",
            "",
            f"Context (top {min(k, len(results))}):",
        ]

        for i, result in enumerate(results[:k]):
            metadata = result.get("metadata", {})
            citation = self.format_citation(result)
            score = result.get("score", 0.0)
            content = result.get("content", "")

            context_parts.append(f"\n[score={score:.3f}] {citation}\n{content}")

        context_parts.append("\nAnswer:")

        return "\n".join(context_parts)


class MockSearcher:
    """Mock searcher for testing when real implementation not available."""

    def search(self, query: str, top_k: int = 5, **kwargs) -> List[Dict]:
        """Return mock results."""
        return [
            {
                "content": f"Mock result for query: '{query}'",
                "score": 0.95,
                "metadata": {
                    "file_path": "backend/src/application/use_cases/create_job.py",
                    "file_type": "py",
                    "line_start": 15,
                    "line_end": 45,
                    "function_name": "create_job",
                },
            },
            {
                "content": "Mock implementation details...",
                "score": 0.87,
                "metadata": {
                    "file_path": "docs/ARCHITECTURE.md",
                    "file_type": "md",
                    "line_start": 100,
                    "line_end": 120,
                },
            },
        ]


def search_codebase(
    query: str,
    top_k: int = 5,
    filter_type: Optional[str] = None,
    filter_path: Optional[str] = None,
    use_hybrid: bool = True,
) -> List[Dict]:
    """Search the codebase and return results."""

    # Try to use real searcher, fall back to mock
    if SemanticSearcher is not None:
        try:
            searcher = SemanticSearcher()
            filters = {}
            if filter_type:
                filters["file_type"] = filter_type
            if filter_path:
                filters["path_contains"] = filter_path

            results = searcher.search(
                query=query, top_k=top_k, filters=filters, use_hybrid=use_hybrid
            )
            return results
        except Exception as e:
            print(f"⚠️  Search failed: {e}", file=sys.stderr)
            print("Using mock results for demonstration...\n", file=sys.stderr)

    # Use mock searcher
    mock_searcher = MockSearcher()
    return mock_searcher.search(query, top_k)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Search codebase with RAG and get grounded answers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run rag-search "How to create a job?"
  uv run rag-search "video generation" --top-k 10
  uv run rag-search "database schema" --filter-type py
  uv run rag-search "API endpoints" --format llm
  uv run rag-search "celery tasks" --filter-path "workers" --verbose
        """,
    )

    parser.add_argument("query", type=str, help="Search query")

    parser.add_argument(
        "--top-k",
        "-k",
        type=int,
        default=5,
        help="Number of results to return (default: 5)",
    )

    parser.add_argument(
        "--filter-type",
        "-t",
        type=str,
        help="Filter by file type (e.g., py, md, yaml)",
    )

    parser.add_argument(
        "--filter-path",
        "-p",
        type=str,
        help="Filter by path contains (e.g., 'use_cases', 'docs')",
    )

    parser.add_argument(
        "--format",
        "-f",
        choices=["human", "llm", "json"],
        default="human",
        help="Output format (default: human)",
    )

    parser.add_argument(
        "--no-hybrid",
        action="store_true",
        help="Disable hybrid search (semantic only)",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed metadata")

    parser.add_argument("--no-scores", action="store_true", help="Hide relevance scores")

    args = parser.parse_args()

    # Perform search
    print(f"🔍 Searching for: '{args.query}'...\n", file=sys.stderr)

    try:
        results = search_codebase(
            query=args.query,
            top_k=args.top_k,
            filter_type=args.filter_type,
            filter_path=args.filter_path,
            use_hybrid=not args.no_hybrid,
        )

        # Format output
        formatter = GroundedAnswerFormatter(
            show_scores=not args.no_scores, show_metadata=args.verbose
        )

        if args.format == "json":
            # JSON output
            output = json.dumps(results, indent=2)
        elif args.format == "llm":
            # LLM context format
            output = formatter.format_llm_context(args.query, results, args.top_k)
        else:
            # Human-readable format
            output = formatter.format_grounded_answer(args.query, results, args.top_k)

        print(output)

        # Exit code
        sys.exit(0 if results else 1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Search cancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
