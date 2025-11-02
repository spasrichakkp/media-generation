"""
Documentation Parser - Parse Markdown, YAML, and other documentation files
"""

from pathlib import Path
from typing import Dict, Optional
import re


class DocParser:
    """Parser for documentation files (Markdown, YAML, JSON, etc.)."""

    def parse_markdown(self, file_path: Path) -> Optional[Dict]:
        """Parse Markdown file.

        Args:
            file_path: Path to Markdown file

        Returns:
            Parsed content with metadata
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Extract headers
            headers = re.findall(r"^(#{1,6})\s+(.+)$", content, re.MULTILINE)

            # Extract code blocks
            code_blocks = re.findall(r"```(\w+)?\n(.*?)```", content, re.DOTALL)

            return {
                "content": content,
                "type": "markdown",
                "metadata": {
                    "file_path": str(file_path),
                    "headers": [{"level": len(h[0]), "text": h[1]} for h in headers],
                    "code_blocks": [
                        {"language": cb[0] or "text", "code": cb[1]} for cb in code_blocks
                    ],
                    "num_headers": len(headers),
                    "num_code_blocks": len(code_blocks),
                },
            }

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def parse_yaml(self, file_path: Path) -> Optional[Dict]:
        """Parse YAML file.

        Args:
            file_path: Path to YAML file

        Returns:
            Parsed content with metadata
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Try to parse YAML structure
            try:
                import yaml

                data = yaml.safe_load(content)
                top_keys = list(data.keys()) if isinstance(data, dict) else []
            except Exception:
                top_keys = []

            return {
                "content": content,
                "type": "yaml",
                "metadata": {
                    "file_path": str(file_path),
                    "top_keys": top_keys,
                },
            }

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def parse_config(self, file_path: Path) -> Optional[Dict]:
        """Parse configuration files (JSON, TOML, INI, etc.).

        Args:
            file_path: Path to config file

        Returns:
            Parsed content with metadata
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            suffix = file_path.suffix.lower()

            return {
                "content": content,
                "type": "config",
                "metadata": {
                    "file_path": str(file_path),
                    "config_type": suffix[1:] if suffix else "unknown",
                },
            }

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None
