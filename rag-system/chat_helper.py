#!/usr/bin/env python3
"""
RAG Chat Helper - Integration with AI Chat Sessions

This script provides grounded context from your codebase for AI assistants.
Use it to get relevant code snippets before asking questions in chat.

Usage:
    # Quick search with LLM-formatted output
    uv run python chat_helper.py "How to create a job?"

    # Copy output and paste into your chat with AI
    uv run python chat_helper.py "video generation" | pbcopy  # macOS
    uv run python chat_helper.py "video generation" | xclip   # Linux

    # Save to file
    uv run python chat_helper.py "database schema" > context.txt

    # Interactive mode
    uv run python chat_helper.py --interactive
"""

import sys
import argparse
from pathlib import Path
from typing import List, Dict, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from cli.search import search_codebase, GroundedAnswerFormatter
except ImportError:
    print("⚠️  Required modules not found. Using mock implementation.", file=sys.stderr)
    search_codebase = None
    GroundedAnswerFormatter = None


class ChatContextBuilder:
    """Build optimized context for AI chat sessions."""

    def __init__(self):
        self.formatter = GroundedAnswerFormatter() if GroundedAnswerFormatter else None

    def build_chat_context(
        self,
        query: str,
        results: List[Dict],
        max_results: int = 5,
        include_instructions: bool = True,
    ) -> str:
        """Build context optimized for AI chat."""

        if not results:
            return self._no_results_message(query)

        parts = []

        # Add instructions
        if include_instructions:
            parts.append(self._get_instructions())

        # Add query
        parts.append(f"**User Query:** {query}\n")

        # Add context header
        parts.append(f"**Context from Codebase (top {min(max_results, len(results))} results):**\n")

        # Add each result
        for i, result in enumerate(results[:max_results], 1):
            parts.append(self._format_result(result, i))

        # Add footer
        parts.append(self._get_footer(results[:max_results]))

        return "\n".join(parts)

    def _get_instructions(self) -> str:
        """Get instructions for AI assistant."""
        return """---
**INSTRUCTIONS FOR AI ASSISTANT:**

You are helping with the Media Generation Platform codebase.

When answering:
1. Use ONLY the context provided below from the actual codebase
2. Cite sources using [file:line-range] format
3. If information is not in the context, say "Not found in provided context"
4. Be specific and reference actual code/documentation shown
5. Maintain consistency with existing patterns in the codebase

---
"""

    def _format_result(self, result: Dict, index: int) -> str:
        """Format a single result for chat context."""
        metadata = result.get("metadata", {})
        content = result.get("content", "")
        score = result.get("score", 0.0)

        # Build citation
        file_path = metadata.get("file_path", "unknown")
        line_start = metadata.get("line_start", "")
        line_end = metadata.get("line_end", "")

        if line_start and line_end:
            citation = f"[{file_path}:{line_start}-{line_end}]"
        else:
            citation = f"[{file_path}]"

        # Build result
        lines = [
            f"\n**Result #{index}** {citation}",
            f"*Relevance: {score:.2f}*",
        ]

        # Add metadata if available
        if metadata.get("function_name"):
            lines.append(f"*Function: `{metadata['function_name']}`*")
        if metadata.get("class_name"):
            lines.append(f"*Class: `{metadata['class_name']}`*")

        # Add content
        file_type = metadata.get("file_type", "text")
        lines.append(f"\n```{file_type}")
        lines.append(content.strip())
        lines.append("```\n")

        return "\n".join(lines)

    def _get_footer(self, results: List[Dict]) -> str:
        """Get footer with citations."""
        lines = ["\n---", "**CITATIONS:**"]

        for i, result in enumerate(results, 1):
            metadata = result.get("metadata", {})
            file_path = metadata.get("file_path", "unknown")
            line_start = metadata.get("line_start", "")
            line_end = metadata.get("line_end", "")

            if line_start and line_end:
                citation = f"{file_path}:{line_start}-{line_end}"
            else:
                citation = file_path

            lines.append(f"[{i}] {citation}")

        lines.append("\n---")
        lines.append(
            "*All content above is from the actual codebase. Use it to provide accurate, grounded answers.*"
        )
        lines.append("---\n")

        return "\n".join(lines)

    def _no_results_message(self, query: str) -> str:
        """Message when no results found."""
        return f"""---
**Query:** {query}

**Result:** ⚠️  No relevant results found in the indexed codebase.

**Suggestions:**
- Try different keywords
- Use broader search terms
- Check if the code has been indexed: `uv run python indexer/index_all.py --incremental`
- Search for related concepts

---
"""


def interactive_mode():
    """Run in interactive mode."""
    print("=" * 80)
    print("RAG Chat Helper - Interactive Mode")
    print("=" * 80)
    print("\nType your questions. Use 'quit' or Ctrl+C to exit.\n")

    builder = ChatContextBuilder()

    try:
        while True:
            query = input("\n🔍 Query: ").strip()

            if not query:
                continue

            if query.lower() in ["quit", "exit", "q"]:
                print("\nGoodbye! 👋\n")
                break

            print("\n⏳ Searching...\n")

            # Search
            if search_codebase:
                results = search_codebase(query, top_k=5)
            else:
                # Mock results
                results = [
                    {
                        "content": f"Mock result for: {query}",
                        "score": 0.95,
                        "metadata": {
                            "file_path": "backend/src/example.py",
                            "line_start": 10,
                            "line_end": 20,
                        },
                    }
                ]

            # Format
            context = builder.build_chat_context(query, results)

            # Print
            print(context)
            print("\n💡 Copy the above and paste into your AI chat!")
            print("-" * 80)

    except KeyboardInterrupt:
        print("\n\nGoodbye! 👋\n")
        sys.exit(0)


def quick_search(query: str, max_results: int = 5, minimal: bool = False) -> str:
    """Quick search and format for chat."""
    builder = ChatContextBuilder()

    # Search
    if search_codebase:
        try:
            results = search_codebase(query, top_k=max_results)
        except Exception as e:
            return f"Error searching: {e}\nUsing mock results...\n\n" + builder._no_results_message(
                query
            )
    else:
        # Mock results for testing
        results = [
            {
                "content": f"# Mock implementation for: {query}\n\nThis is example code that would be found in your codebase.",
                "score": 0.95,
                "metadata": {
                    "file_path": "backend/src/application/use_cases/example.py",
                    "file_type": "py",
                    "line_start": 15,
                    "line_end": 45,
                    "function_name": "example_function",
                },
            }
        ]

    # Format
    context = builder.build_chat_context(
        query, results, max_results=max_results, include_instructions=not minimal
    )

    return context


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="RAG Chat Helper - Get grounded context for AI chat",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (output to terminal)
  uv run python chat_helper.py "How to create a job?"

  # Copy to clipboard (macOS)
  uv run python chat_helper.py "video generation" | pbcopy

  # Copy to clipboard (Linux)
  uv run python chat_helper.py "video generation" | xclip -selection clipboard

  # Save to file
  uv run python chat_helper.py "database schema" > context.txt

  # More results
  uv run python chat_helper.py "API endpoints" --max-results 10

  # Minimal output (no instructions)
  uv run python chat_helper.py "celery tasks" --minimal

  # Interactive mode
  uv run python chat_helper.py --interactive

Workflow:
  1. Run this script with your question
  2. Copy the output
  3. Paste into your AI chat (Claude, GitHub Copilot Chat, etc.)
  4. AI will answer based on YOUR codebase context
        """,
    )

    parser.add_argument("query", nargs="?", type=str, help="Search query")

    parser.add_argument(
        "--max-results", "-k", type=int, default=5, help="Maximum results to include (default: 5)"
    )

    parser.add_argument(
        "--minimal", "-m", action="store_true", help="Minimal output (no instructions)"
    )

    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")

    parser.add_argument(
        "--copy", "-c", action="store_true", help="Attempt to copy to clipboard (macOS/Linux)"
    )

    args = parser.parse_args()

    # Interactive mode
    if args.interactive:
        interactive_mode()
        return

    # Need query if not interactive
    if not args.query:
        parser.print_help()
        sys.exit(1)

    # Search and format
    context = quick_search(args.query, max_results=args.max_results, minimal=args.minimal)

    # Copy to clipboard if requested
    if args.copy:
        try:
            import subprocess
            import platform

            system = platform.system()
            if system == "Darwin":  # macOS
                subprocess.run(["pbcopy"], input=context.encode(), check=True)
                print("✓ Copied to clipboard!", file=sys.stderr)
            elif system == "Linux":
                subprocess.run(
                    ["xclip", "-selection", "clipboard"], input=context.encode(), check=True
                )
                print("✓ Copied to clipboard!", file=sys.stderr)
            else:
                print("⚠️  Clipboard copy not supported on this system", file=sys.stderr)
        except Exception as e:
            print(f"⚠️  Failed to copy to clipboard: {e}", file=sys.stderr)

    # Print context
    print(context)


if __name__ == "__main__":
    main()
