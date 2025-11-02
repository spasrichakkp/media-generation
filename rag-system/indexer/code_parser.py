"""
Code Parser - Parse various code file types

This module provides parsers for different file types using AST and other
language-specific parsing techniques.
"""

import ast
from pathlib import Path
from typing import Dict, List, Optional


class CodeParser:
    """Parser for code files (Python, SQL, Shell, etc.)."""

    def parse_python(self, file_path: Path) -> Optional[Dict]:
        """Parse Python file using AST.

        Args:
            file_path: Path to Python file

        Returns:
            Parsed content with metadata
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                source = f.read()

            # Parse AST
            try:
                tree = ast.parse(source)
            except SyntaxError:
                # If AST parsing fails, return raw content
                return {
                    "content": source,
                    "type": "python",
                    "metadata": {"file_path": str(file_path), "parse_error": "AST parsing failed"},
                }

            # Extract metadata
            functions = []
            classes = []
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(
                        {
                            "name": node.name,
                            "line": node.lineno,
                            "end_line": node.end_lineno,
                            "docstring": ast.get_docstring(node),
                        }
                    )
                elif isinstance(node, ast.ClassDef):
                    classes.append(
                        {
                            "name": node.name,
                            "line": node.lineno,
                            "end_line": node.end_lineno,
                            "docstring": ast.get_docstring(node),
                        }
                    )
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    try:
                        imports.append(ast.unparse(node))
                    except:
                        pass

            return {
                "content": source,
                "type": "python",
                "metadata": {
                    "file_path": str(file_path),
                    "functions": functions,
                    "classes": classes,
                    "imports": imports,
                    "num_functions": len(functions),
                    "num_classes": len(classes),
                },
            }

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def parse_sql(self, file_path: Path) -> Optional[Dict]:
        """Parse SQL file.

        Args:
            file_path: Path to SQL file

        Returns:
            Parsed content with metadata
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Extract table names (simple regex-based)
            import re

            tables = re.findall(
                r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)", content, re.IGNORECASE
            )

            return {
                "content": content,
                "type": "sql",
                "metadata": {
                    "file_path": str(file_path),
                    "tables": tables,
                },
            }

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def parse_shell(self, file_path: Path) -> Optional[Dict]:
        """Parse shell script.

        Args:
            file_path: Path to shell script

        Returns:
            Parsed content with metadata
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Extract function definitions
            import re

            functions = re.findall(r"^(\w+)\s*\(\s*\)\s*\{", content, re.MULTILINE)

            return {
                "content": content,
                "type": "shell",
                "metadata": {
                    "file_path": str(file_path),
                    "functions": functions,
                },
            }

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def parse_dockerfile(self, file_path: Path) -> Optional[Dict]:
        """Parse Dockerfile.

        Args:
            file_path: Path to Dockerfile

        Returns:
            Parsed content with metadata
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Extract FROM, RUN, CMD instructions
            import re

            from_images = re.findall(r"^FROM\s+(\S+)", content, re.MULTILINE)

            return {
                "content": content,
                "type": "dockerfile",
                "metadata": {
                    "file_path": str(file_path),
                    "base_images": from_images,
                },
            }

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None
