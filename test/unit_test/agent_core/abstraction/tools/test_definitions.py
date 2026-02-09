"""Unit tests for tool definitions."""

import pytest
from pydantic import ValidationError
from gearmeshing_ai.agent_core.abstraction.tools.definitions import (
    ToolInput, ToolOutput,
    FileReadInput, FileReadOutput,
    FileWriteInput, FileWriteOutput,
    FileListInput, FileListOutput,
    CommandRunInput, CommandRunOutput
)


class TestToolDefinitions:
    """Test Pydantic model definitions for tools."""

    def test_file_read_input_validation(self):
        """Test FileReadInput validation."""
        # Valid input
        input_data = FileReadInput(file_path="/path/to/file.txt", encoding="utf-8")
        assert input_data.file_path == "/path/to/file.txt"
        assert input_data.encoding == "utf-8"
        
        # Missing required field
        with pytest.raises(ValidationError):
            FileReadInput()

    def test_file_read_input_defaults(self):
        """Test FileReadInput default values."""
        input_data = FileReadInput(file_path="/path/to/file.txt")
        assert input_data.encoding == "utf-8"  # Default value

    def test_file_write_input_validation(self):
        """Test FileWriteInput validation."""
        # Valid input
        input_data = FileWriteInput(
            file_path="/path/to/file.txt",
            content="Hello, World!",
            encoding="utf-8",
            create_dirs=True
        )
        assert input_data.file_path == "/path/to/file.txt"
        assert input_data.content == "Hello, World!"
        assert input_data.encoding == "utf-8"
        assert input_data.create_dirs is True
        
        # Missing required fields
        with pytest.raises(ValidationError):
            FileWriteInput(file_path="/path/to/file.txt")

    def test_file_write_input_defaults(self):
        """Test FileWriteInput default values."""
        input_data = FileWriteInput(
            file_path="/path/to/file.txt",
            content="content"
        )
        assert input_data.encoding == "utf-8"  # Default
        assert input_data.create_dirs is True  # Default

    def test_file_list_input_validation(self):
        """Test FileListInput validation."""
        # Valid input
        input_data = FileListInput(
            directory_path="/path/to/dir",
            pattern="*.txt",
            recursive=True
        )
        assert input_data.directory_path == "/path/to/dir"
        assert input_data.pattern == "*.txt"
        assert input_data.recursive is True
        
        # Missing required field
        with pytest.raises(ValidationError):
            FileListInput()

    def test_file_list_input_defaults(self):
        """Test FileListInput default values."""
        input_data = FileListInput(directory_path="/path/to/dir")
        assert input_data.pattern is None  # Default
        assert input_data.recursive is False  # Default

    def test_command_run_input_validation(self):
        """Test CommandRunInput validation."""
        # Valid input
        input_data = CommandRunInput(
            command="echo 'Hello, World!'",
            cwd="/tmp",
            timeout=30.0,
            shell=True,
            env={"TEST_VAR": "value"}
        )
        assert input_data.command == "echo 'Hello, World!'"
        assert input_data.cwd == "/tmp"
        assert input_data.timeout == 30.0
        assert input_data.shell is True
        assert input_data.env == {"TEST_VAR": "value"}
        
        # Missing required field
        with pytest.raises(ValidationError):
            CommandRunInput()

    def test_command_run_input_defaults(self):
        """Test CommandRunInput default values."""
        input_data = CommandRunInput(command="echo hello")
        assert input_data.cwd is None  # Default
        assert input_data.timeout == 30.0  # Default
        assert input_data.shell is True  # Default
        assert input_data.env is None  # Default

    def test_tool_output_validation(self):
        """Test ToolOutput validation."""
        # Successful output
        output = ToolOutput(
            success=True,
            error_message=None,
            metadata={"key": "value"}
        )
        assert output.success is True
        assert output.error_message is None
        assert output.metadata == {"key": "value"}
        
        # Failed output
        output = ToolOutput(
            success=False,
            error_message="Something went wrong"
        )
        assert output.success is False
        assert output.error_message == "Something went wrong"

    def test_tool_output_defaults(self):
        """Test ToolOutput default values."""
        output = ToolOutput(success=True)
        assert output.error_message is None  # Default
        assert output.metadata is None  # Default

    def test_file_read_output_validation(self):
        """Test FileReadOutput validation."""
        output = FileReadOutput(
            success=True,
            content="file content",
            file_path="/path/to/file.txt",
            size_bytes=100
        )
        assert output.success is True
        assert output.content == "file content"
        assert output.file_path == "/path/to/file.txt"
        assert output.size_bytes == 100

    def test_file_write_output_validation(self):
        """Test FileWriteOutput validation."""
        output = FileWriteOutput(
            success=True,
            file_path="/path/to/file.txt",
            bytes_written=50
        )
        assert output.success is True
        assert output.file_path == "/path/to/file.txt"
        assert output.bytes_written == 50

    def test_file_list_output_validation(self):
        """Test FileListOutput validation."""
        output = FileListOutput(
            success=True,
            directory_path="/path/to/dir",
            files=["file1.txt", "file2.py"]
        )
        assert output.success is True
        assert output.directory_path == "/path/to/dir"
        assert output.files == ["file1.txt", "file2.py"]

    def test_command_run_output_validation(self):
        """Test CommandRunOutput validation."""
        output = CommandRunOutput(
            success=True,
            command="echo hello",
            exit_code=0,
            stdout="hello\n",
            stderr="",
            duration_seconds=0.1
        )
        assert output.success is True
        assert output.command == "echo hello"
        assert output.exit_code == 0
        assert output.stdout == "hello\n"
        assert output.stderr == ""
        assert output.duration_seconds == 0.1

    def test_serialization(self):
        """Test that models can be serialized to JSON."""
        input_data = FileReadInput(file_path="/path/to/file.txt")
        json_str = input_data.model_dump_json()
        assert "file_path" in json_str
        assert "/path/to/file.txt" in json_str
        
        output = FileReadOutput(
            success=True,
            content="content",
            file_path="/path/to/file.txt",
            size_bytes=7
        )
        json_str = output.model_dump_json()
        assert "success" in json_str
        assert "content" in json_str

    def test_deserialization(self):
        """Test that models can be deserialized from JSON."""
        json_str = '{"file_path": "/path/to/file.txt", "encoding": "utf-8"}'
        input_data = FileReadInput.model_validate_json(json_str)
        assert input_data.file_path == "/path/to/file.txt"
        assert input_data.encoding == "utf-8"

    def test_inheritance(self):
        """Test that tool inputs inherit from ToolInput."""
        assert issubclass(FileReadInput, ToolInput)
        assert issubclass(FileWriteInput, ToolInput)
        assert issubclass(FileListInput, ToolInput)
        assert issubclass(CommandRunInput, ToolInput)
        
        # Test that tool outputs inherit from ToolOutput
        assert issubclass(FileReadOutput, ToolOutput)
        assert issubclass(FileWriteOutput, ToolOutput)
        assert issubclass(FileListOutput, ToolOutput)
        assert issubclass(CommandRunOutput, ToolOutput)
