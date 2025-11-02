"""
Metadata Extractor - Extract metadata from files for indexing

This module extracts rich metadata from files including file information,
git metadata, and content-specific metadata.
"""

import hashlib
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime


class MetadataExtractor:
    """Extract metadata from files for enhanced search and filtering."""

    def __init__(self):
        """Initialize metadata extractor."""
        self.git_available = self._check_git_available()

    def _check_git_available(self) -> bool:
        """Check if git is available."""
        try:
            import subprocess

            result = subprocess.run(["git", "--version"], capture_output=True, timeout=1)
            return result.returncode == 0
        except Exception:
            return False

    def extract(self, file_path: Path) -> Dict:
        """Extract comprehensive metadata from file.

        Args:
            file_path: Path to file

        Returns:
            Dictionary of metadata
        """
        metadata = {}

        # File information
        metadata.update(self._extract_file_info(file_path))

        # Git information (if available)
        if self.git_available:
            metadata.update(self._extract_git_info(file_path))

        # Content hash
        metadata["content_hash"] = self._calculate_hash(file_path)

        return metadata

    def _extract_file_info(self, file_path: Path) -> Dict:
        """Extract basic file information.

        Args:
            file_path: Path to file

        Returns:
            File metadata
        """
        try:
            stat = file_path.stat()

            return {
                "file_name": file_path.name,
                "file_type": file_path.suffix[1:] if file_path.suffix else "",
                "file_size": stat.st_size,
                "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            }
        except Exception as e:
            return {
                "file_name": file_path.name,
                "file_type": file_path.suffix[1:] if file_path.suffix else "",
                "error": str(e),
            }

    def _extract_git_info(self, file_path: Path) -> Dict:
        """Extract git metadata for file.

        Args:
            file_path: Path to file

        Returns:
            Git metadata
        """
        git_info = {}

        try:
            import subprocess

            # Get current branch
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    cwd=file_path.parent,
                )
                if result.returncode == 0:
                    git_info["git_branch"] = result.stdout.strip()
            except Exception:
                pass

            # Get last commit hash for this file
            try:
                result = subprocess.run(
                    ["git", "log", "-1", "--format=%H", str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    cwd=file_path.parent,
                )
                if result.returncode == 0:
                    git_info["git_commit"] = result.stdout.strip()
            except Exception:
                pass

            # Get last author for this file
            try:
                result = subprocess.run(
                    ["git", "log", "-1", "--format=%an", str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    cwd=file_path.parent,
                )
                if result.returncode == 0:
                    git_info["git_author"] = result.stdout.strip()
            except Exception:
                pass

        except Exception:
            pass

        return git_info

    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file content.

        Args:
            file_path: Path to file

        Returns:
            Hex digest of file hash
        """
        try:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return ""

    def get_file_hash(self, file_path: Path) -> str:
        """Get file hash (alias for _calculate_hash).

        Args:
            file_path: Path to file

        Returns:
            File hash
        """
        return self._calculate_hash(file_path)
