from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest


class FileTestHelper:
    """Helper class for file operations in smoke tests."""

    @staticmethod
    def create_test_file(file_path: str | Path, content: str, encoding: str = "utf-8") -> None:
        """Create a test file with specified content.

        Args:
            file_path: Path where to create the file
            content: Content to write to the file
            encoding: File encoding (default: utf-8)
        """
        file_path = Path(file_path)

        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding=encoding) as f:
            f.write(content)

    @staticmethod
    def read_test_file(file_path: str | Path, encoding: str = "utf-8") -> str:
        """Read content from a test file.

        Args:
            file_path: Path to the file to read
            encoding: File encoding (default: utf-8)

        Returns:
            File content as string
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Test file not found: {file_path}")

        with open(file_path, encoding=encoding) as f:
            return f.read()

    @staticmethod
    def read_json_file(file_path: str | Path, encoding: str = "utf-8") -> dict[str, Any]:
        """Read and parse JSON from a test file.

        Args:
            file_path: Path to the JSON file
            encoding: File encoding (default: utf-8)

        Returns:
            Parsed JSON data as dictionary
        """
        content = FileTestHelper.read_test_file(file_path, encoding)
        return json.loads(content)

    @staticmethod
    def write_json_file(file_path: str | Path, data: dict[str, Any], encoding: str = "utf-8", indent: int = 2) -> None:
        """Write dictionary data to a JSON file.

        Args:
            file_path: Path where to create the JSON file
            data: Dictionary data to write
            encoding: File encoding (default: utf-8)
            indent: JSON indentation (default: 2)
        """
        file_path = Path(file_path)

        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding=encoding) as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)

    @staticmethod
    def cleanup_files(*file_paths: str | Path) -> None:
        """Clean up multiple test files safely.

        Args:
            *file_paths: Variable number of file paths to clean up
        """
        for file_path in file_paths:
            try:
                path = Path(file_path)
                if path.exists():
                    if path.is_file():
                        path.unlink()
                    elif path.is_dir():
                        # Remove directory and all contents
                        import shutil

                        shutil.rmtree(path)
            except Exception as e:
                print(f"Warning: Failed to clean up {file_path}: {e}")

    @staticmethod
    def file_contains(file_path: str | Path, content: str, encoding: str = "utf-8") -> bool:
        """Check if file contains specific content.

        Args:
            file_path: Path to the file to check
            content: Content to search for
            encoding: File encoding (default: utf-8)

        Returns:
            True if content is found, False otherwise
        """
        try:
            file_content = FileTestHelper.read_test_file(file_path, encoding)
            return content in file_content
        except FileNotFoundError:
            return False

    @staticmethod
    def create_temp_file(content: str, suffix: str = ".tmp", encoding: str = "utf-8") -> Path:
        """Create a temporary file with content.

        Args:
            content: Content to write to the temporary file
            suffix: File suffix (default: .tmp)
            encoding: File encoding (default: utf-8)

        Returns:
            Path to the created temporary file
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, encoding=encoding, delete=False) as f:
            f.write(content)
            return Path(f.name)

    @staticmethod
    def get_file_size(file_path: str | Path) -> int:
        """Get file size in bytes.

        Args:
            file_path: Path to the file

        Returns:
            File size in bytes
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        return path.stat().st_size

    @staticmethod
    def files_exist(*file_paths: str | Path) -> bool:
        """Check if multiple files exist.

        Args:
            *file_paths: Variable number of file paths to check

        Returns:
            True if all files exist, False otherwise
        """
        return all(Path(path).exists() for path in file_paths)

    @staticmethod
    def count_files_in_directory(directory: str | Path, pattern: str = "*") -> int:
        """Count files in a directory matching a pattern.

        Args:
            directory: Directory path to search
            pattern: Glob pattern to match (default: *)

        Returns:
            Number of matching files
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            return 0

        return len(list(dir_path.glob(pattern)))

    @staticmethod
    def find_files_by_content(directory: str | Path, search_content: str, encoding: str = "utf-8") -> list[Path]:
        """Find files containing specific content in a directory.

        Args:
            directory: Directory to search
            search_content: Content to search for
            encoding: File encoding (default: utf-8)

        Returns:
            List of file paths containing the content
        """
        dir_path = Path(directory)
        matching_files: list[Path] = []

        if not dir_path.exists():
            return matching_files

        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                try:
                    if FileTestHelper.file_contains(file_path, search_content, encoding):
                        matching_files.append(file_path)
                except Exception:
                    # Skip files that can't be read
                    continue

        return matching_files


@pytest.fixture
def file_helper() -> FileTestHelper:
    """Provide file test helper for smoke tests."""
    return FileTestHelper()
