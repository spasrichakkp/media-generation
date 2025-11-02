#!/usr/bin/env python3
"""
Main indexing script for the Media Generation Platform RAG system.

This script orchestrates the indexing of all code, documentation, and configuration files
in the project. It supports full indexing, incremental updates, and watch mode.

Usage:
    python index_all.py --full              # Full reindex
    python index_all.py --incremental       # Update changed files only
    python index_all.py --watch             # Continuous monitoring
    python index_all.py --path ../backend   # Index specific directory
"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import List, Dict, Set, Optional
import hashlib
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from code_parser import CodeParser
from doc_parser import DocParser
from chunker import SemanticChunker
from metadata_extractor import MetadataExtractor

# Import vector store and embeddings
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class IndexManager:
    """Manages the indexing process for the RAG system."""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the index manager.

        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        self.base_path = Path(self.config["indexing"]["base_path"]).resolve()
        self.code_parser = CodeParser()
        self.doc_parser = DocParser()
        self.chunker = SemanticChunker(self.config)
        self.metadata_extractor = MetadataExtractor()

        # Track indexed files
        self.index_state_file = Path("./data/index_state.json")
        self.index_state = self._load_index_state()

        # Statistics
        self.stats = {
            "files_processed": 0,
            "files_skipped": 0,
            "chunks_created": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None,
        }

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            sys.exit(1)

    def _load_index_state(self) -> Dict:
        """Load previous index state for incremental updates."""
        if self.index_state_file.exists():
            try:
                with open(self.index_state_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load index state: {e}")
        return {"files": {}, "last_update": None}

    def _save_index_state(self):
        """Save current index state."""
        self.index_state["last_update"] = datetime.now().isoformat()
        self.index_state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_state_file, "w") as f:
            json.dump(self.index_state, f, indent=2)

    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate hash of file content."""
        try:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Failed to hash {file_path}: {e}")
            return ""

    def _should_index_file(self, file_path: Path, force: bool = False) -> bool:
        """Check if file should be indexed.

        Args:
            file_path: Path to file
            force: Force reindex even if unchanged

        Returns:
            True if file should be indexed
        """
        if force:
            return True

        # Check if file has been modified
        file_key = str(file_path.relative_to(self.base_path))
        current_hash = self._get_file_hash(file_path)

        if file_key in self.index_state["files"]:
            previous_hash = self.index_state["files"][file_key].get("hash", "")
            if current_hash == previous_hash:
                logger.debug(f"Skipping unchanged file: {file_path}")
                self.stats["files_skipped"] += 1
                return False

        return True

    def _get_files_to_index(self, path: Optional[Path] = None) -> List[Path]:
        """Get list of files to index based on include/exclude patterns.

        Args:
            path: Specific path to index, or None for all

        Returns:
            List of file paths to index
        """
        if path:
            base_path = path
        else:
            base_path = self.base_path

        include_patterns = self.config["indexing"]["include_patterns"]
        exclude_patterns = self.config["indexing"]["exclude_patterns"]

        all_files = []

        # Collect all matching files
        for pattern in include_patterns:
            matched = list(base_path.glob(pattern))
            all_files.extend(matched)

        # Remove duplicates
        all_files = list(set(all_files))

        # Apply exclude patterns
        filtered_files = []
        for file_path in all_files:
            should_include = True
            for exclude_pattern in exclude_patterns:
                if file_path.match(exclude_pattern):
                    should_include = False
                    break

            if should_include and file_path.is_file():
                filtered_files.append(file_path)

        # Sort by priority (if configured)
        priorities = self.config["indexing"].get("priorities", {})

        def get_priority(file_path: Path) -> int:
            """Get priority score for file based on its directory."""
            rel_path = str(file_path.relative_to(self.base_path))
            for dir_pattern, priority in priorities.items():
                if rel_path.startswith(dir_pattern):
                    return priority
            return 0

        filtered_files.sort(key=get_priority, reverse=True)

        logger.info(f"Found {len(filtered_files)} files to index")
        return filtered_files

    def _parse_file(self, file_path: Path) -> Optional[Dict]:
        """Parse a single file based on its type.

        Args:
            file_path: Path to file

        Returns:
            Parsed content and metadata, or None if parsing failed
        """
        suffix = file_path.suffix.lower()

        try:
            if suffix == ".py":
                return self.code_parser.parse_python(file_path)
            elif suffix in [".md", ".markdown"]:
                return self.doc_parser.parse_markdown(file_path)
            elif suffix in [".yaml", ".yml"]:
                return self.doc_parser.parse_yaml(file_path)
            elif suffix == ".sql":
                return self.code_parser.parse_sql(file_path)
            elif suffix == ".sh":
                return self.code_parser.parse_shell(file_path)
            elif suffix in [".json", ".toml", ".ini", ".cfg"]:
                return self.doc_parser.parse_config(file_path)
            elif "dockerfile" in file_path.name.lower():
                return self.code_parser.parse_dockerfile(file_path)
            else:
                # Plain text fallback
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                return {
                    "content": content,
                    "type": "text",
                    "metadata": {"file_path": str(file_path)},
                }
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            self.stats["errors"] += 1
            return None

    def _chunk_content(self, parsed_data: Dict, file_path: Path) -> List[Dict]:
        """Chunk parsed content into smaller pieces.

        Args:
            parsed_data: Parsed file data
            file_path: Original file path

        Returns:
            List of chunks with metadata
        """
        content = parsed_data.get("content", "")
        content_type = parsed_data.get("type", "text")
        file_metadata = parsed_data.get("metadata", {})

        # Choose chunking strategy based on content type
        if content_type in ["python", "code"]:
            chunks = self.chunker.chunk_code(content, language="python")
        elif content_type in ["markdown", "documentation"]:
            chunks = self.chunker.chunk_markdown(content)
        else:
            chunks = self.chunker.chunk_text(content)

        # Enrich chunks with metadata
        enriched_chunks = []
        for i, chunk in enumerate(chunks):
            chunk_data = {
                "content": chunk["text"],
                "metadata": {
                    "file_path": str(file_path.relative_to(self.base_path)),
                    "file_name": file_path.name,
                    "file_type": file_path.suffix[1:],
                    "content_type": content_type,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "line_start": chunk.get("line_start"),
                    "line_end": chunk.get("line_end"),
                    "last_modified": datetime.fromtimestamp(
                        file_path.stat().st_mtime
                    ).isoformat(),
                    **file_metadata,
                },
            }
            enriched_chunks.append(chunk_data)

        return enriched_chunks

    def index_file(self, file_path: Path, force: bool = False) -> int:
        """Index a single file.

        Args:
            file_path: Path to file
            force: Force reindex even if unchanged

        Returns:
            Number of chunks created
        """
        if not self._should_index_file(file_path, force):
            return 0

        logger.info(f"Indexing: {file_path.relative_to(self.base_path)}")

        # Parse file
        parsed_data = self._parse_file(file_path)
        if not parsed_data:
            return 0

        # Chunk content
        chunks = self._chunk_content(parsed_data, file_path)

        # TODO: Generate embeddings and store in vector database
        # This will be implemented when vector_store module is ready

        # Update index state
        file_key = str(file_path.relative_to(self.base_path))
        self.index_state["files"][file_key] = {
            "hash": self._get_file_hash(file_path),
            "chunks": len(chunks),
            "last_indexed": datetime.now().isoformat(),
        }

        self.stats["files_processed"] += 1
        self.stats["chunks_created"] += len(chunks)

        return len(chunks)

    def index_all(self, path: Optional[Path] = None, force: bool = False):
        """Index all files in the project.

        Args:
            path: Specific path to index, or None for all
            force: Force full reindex
        """
        self.stats["start_time"] = time.time()

        logger.info("=" * 60)
        logger.info("Starting indexing process")
        logger.info("=" * 60)

        files_to_index = self._get_files_to_index(path)

        total_files = len(files_to_index)
        for idx, file_path in enumerate(files_to_index, 1):
            logger.info(f"[{idx}/{total_files}] Processing: {file_path.name}")
            self.index_file(file_path, force)

        # Save index state
        self._save_index_state()

        self.stats["end_time"] = time.time()
        self._print_statistics()

    def _print_statistics(self):
        """Print indexing statistics."""
        duration = self.stats["end_time"] - self.stats["start_time"]

        logger.info("=" * 60)
        logger.info("Indexing Complete")
        logger.info("=" * 60)
        logger.info(f"Files processed:  {self.stats['files_processed']}")
        logger.info(f"Files skipped:    {self.stats['files_skipped']}")
        logger.info(f"Chunks created:   {self.stats['chunks_created']}")
        logger.info(f"Errors:           {self.stats['errors']}")
        logger.info(f"Duration:         {duration:.2f} seconds")
        logger.info(
            f"Throughput:       {self.stats['files_processed'] / duration:.2f} files/sec"
        )
        logger.info("=" * 60)

    def watch_mode(self, path: Optional[Path] = None):
        """Watch for file changes and incrementally update index.

        Args:
            path: Specific path to watch, or None for all
        """
        logger.info("Starting watch mode (Ctrl+C to stop)")

        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            class IndexEventHandler(FileSystemEventHandler):
                def __init__(self, index_manager):
                    self.index_manager = index_manager

                def on_modified(self, event):
                    if not event.is_directory:
                        file_path = Path(event.src_path)
                        if self._should_process(file_path):
                            logger.info(f"File modified: {file_path}")
                            self.index_manager.index_file(file_path, force=True)

                def on_created(self, event):
                    if not event.is_directory:
                        file_path = Path(event.src_path)
                        if self._should_process(file_path):
                            logger.info(f"File created: {file_path}")
                            self.index_manager.index_file(file_path, force=True)

                def _should_process(self, file_path: Path) -> bool:
                    # Check if file matches include patterns
                    include_patterns = self.index_manager.config["indexing"][
                        "include_patterns"
                    ]
                    for pattern in include_patterns:
                        if file_path.match(pattern):
                            return True
                    return False

            event_handler = IndexEventHandler(self)
            observer = Observer()
            watch_path = path if path else self.base_path
            observer.schedule(event_handler, str(watch_path), recursive=True)
            observer.start()

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                observer.stop()
            observer.join()

        except ImportError:
            logger.error(
                "watchdog package not installed. Install with: pip install watchdog"
            )
            sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Index code and documentation for RAG system"
    )
    parser.add_argument(
        "--full", action="store_true", help="Perform full reindex (ignore cache)"
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Incremental update (index only changed files)",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch mode (continuously monitor for changes)",
    )
    parser.add_argument(
        "--path", type=str, help="Specific path to index (default: entire project)"
    )
    parser.add_argument(
        "--config", type=str, default="config.yaml", help="Path to configuration file"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize index manager
    index_manager = IndexManager(args.config)

    # Determine path to index
    target_path = Path(args.path) if args.path else None

    # Execute indexing operation
    if args.watch:
        index_manager.watch_mode(target_path)
    elif args.full:
        index_manager.index_all(target_path, force=True)
    elif args.incremental:
        index_manager.index_all(target_path, force=False)
    else:
        # Default: incremental
        index_manager.index_all(target_path, force=False)


if __name__ == "__main__":
    main()
