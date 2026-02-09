"""Unit tests for AI agent tool handlers."""

import asyncio
import pathlib
import tempfile

from gearmeshing_ai.agent_core.abstraction.tools.definitions import (
    CommandRunInput,
    FileListInput,
    FileReadInput,
    FileWriteInput,
)
from gearmeshing_ai.agent_core.abstraction.tools.handlers import (
    list_files_handler,
    read_file_handler,
    run_command_handler,
    write_file_handler,
)


class TestFileHandlers:
    """Test file operation handlers."""

    def test_read_file_success(self):
        """Test successful file reading."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            f.flush()

            input_data = FileReadInput(file_path=f.name)
            result = asyncio.run(read_file_handler(input_data))

            assert result.success is True
            assert result.content == "test content"
            assert result.size_bytes > 0

        pathlib.Path(f.name).unlink()

    def test_read_file_not_found(self):
        """Test reading non-existent file."""
        input_data = FileReadInput(file_path="/nonexistent/file.txt")
        result = asyncio.run(read_file_handler(input_data))

        assert result.success is False
        assert "not found" in result.error_message

    def test_read_file_encoding(self):
        """Test reading file with different encoding."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("Hello, 世界! 🌍")
            f.flush()

            input_data = FileReadInput(file_path=f.name, encoding="utf-8")
            result = asyncio.run(read_file_handler(input_data))

            assert result.success is True
            assert "世界" in result.content
            assert "🌍" in result.content

        pathlib.Path(f.name).unlink()

    def test_write_file_success(self):
        """Test successful file writing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = pathlib.Path(temp_dir) / "test.txt"

            input_data = FileWriteInput(file_path=str(file_path), content="Hello, World!", create_dirs=True)
            result = asyncio.run(write_file_handler(input_data))

            assert result.success is True
            assert result.bytes_written > 0
            assert file_path.exists()
            assert file_path.read_text() == "Hello, World!"

    def test_write_file_create_dirs(self):
        """Test writing file with directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_path = pathlib.Path(temp_dir) / "nested" / "subdir" / "test.txt"

            input_data = FileWriteInput(file_path=str(nested_path), content="Nested content", create_dirs=True)
            result = asyncio.run(write_file_handler(input_data))

            assert result.success is True
            assert nested_path.exists()
            assert nested_path.read_text() == "Nested content"

    def test_write_file_no_create_dirs(self):
        """Test writing file without directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_path = pathlib.Path(temp_dir) / "nonexistent" / "test.txt"

            input_data = FileWriteInput(file_path=str(nested_path), content="Content", create_dirs=False)
            result = asyncio.run(write_file_handler(input_data))

            assert result.success is False
            assert "No such file or directory" in result.error_message

    def test_list_files_success(self):
        """Test successful directory listing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            (pathlib.Path(temp_dir) / "file1.txt").touch()
            (pathlib.Path(temp_dir) / "file2.py").touch()
            (pathlib.Path(temp_dir) / "subdir").mkdir()

            input_data = FileListInput(directory_path=temp_dir)
            result = asyncio.run(list_files_handler(input_data))

            assert result.success is True
            assert len(result.files) >= 2
            assert any("file1.txt" in f for f in result.files)
            assert any("file2.py" in f for f in result.files)

    def test_list_files_with_pattern(self):
        """Test directory listing with pattern filter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            (pathlib.Path(temp_dir) / "test1.txt").touch()
            (pathlib.Path(temp_dir) / "test2.txt").touch()
            (pathlib.Path(temp_dir) / "other.py").touch()

            input_data = FileListInput(directory_path=temp_dir, pattern="*.txt")
            result = asyncio.run(list_files_handler(input_data))

            assert result.success is True
            assert len(result.files) == 2
            assert all(f.endswith(".txt") for f in result.files)

    def test_list_files_recursive(self):
        """Test recursive directory listing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create nested structure
            (pathlib.Path(temp_dir) / "subdir").mkdir()
            (pathlib.Path(temp_dir) / "subdir" / "nested.txt").touch()
            (pathlib.Path(temp_dir) / "root.txt").touch()

            input_data = FileListInput(directory_path=temp_dir, recursive=True)
            result = asyncio.run(list_files_handler(input_data))

            assert result.success is True
            assert len(result.files) >= 2
            assert any("nested.txt" in f for f in result.files)
            assert any("root.txt" in f for f in result.files)

    def test_list_files_directory_not_found(self):
        """Test listing non-existent directory."""
        input_data = FileListInput(directory_path="/nonexistent/directory")
        result = asyncio.run(list_files_handler(input_data))

        assert result.success is False
        assert "not found" in result.error_message


class TestCommandHandlers:
    """Test command execution handlers."""

    def test_run_command_success(self):
        """Test successful command execution."""
        input_data = CommandRunInput(command="echo 'Hello, World!'")
        result = asyncio.run(run_command_handler(input_data))

        assert result.success is True
        assert "Hello, World!" in result.stdout
        assert result.exit_code == 0

    def test_run_command_with_cwd(self):
        """Test command execution with custom working directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_data = CommandRunInput(command="pwd", cwd=temp_dir)
            result = asyncio.run(run_command_handler(input_data))

            assert result.success is True
            assert temp_dir in result.stdout

    def test_run_command_failure(self):
        """Test command execution failure."""
        input_data = CommandRunInput(command="exit 1")
        result = asyncio.run(run_command_handler(input_data))

        assert result.success is False
        assert result.exit_code == 1

    def test_run_command_timeout(self):
        """Test command execution timeout."""
        input_data = CommandRunInput(command="sleep 10", timeout=0.1)
        result = asyncio.run(run_command_handler(input_data))

        assert result.success is False
        assert "timed out" in result.error_message

    def test_run_command_with_env(self):
        """Test command execution with environment variables."""
        input_data = CommandRunInput(command="echo $TEST_VAR", env={"TEST_VAR": "test_value"})
        result = asyncio.run(run_command_handler(input_data))

        assert result.success is True
        assert "test_value" in result.stdout

    def test_run_command_no_shell(self):
        """Test command execution without shell."""
        input_data = CommandRunInput(command="echo", shell=False)
        result = asyncio.run(run_command_handler(input_data))

        assert result.success is True
        # Without shell, echo should just print empty line or its arguments
        assert result.exit_code == 0
