"""Tool definitions and Pydantic models for AI agent tools.

This module contains the input/output models for all AI agent tools,
providing type safety and validation for tool operations.
"""

from typing import Any

from pydantic import BaseModel, Field


class ToolInput(BaseModel):
    """Base class for all tool inputs"""

    pass


class ToolOutput(BaseModel):
    """Base class for all tool outputs"""

    success: bool
    error_message: str | None = None
    metadata: dict[str, Any] | None = None


# File Operations
class FileReadInput(ToolInput):
    """Input for file reading operations"""

    file_path: str = Field(..., description="Path to file to read")
    encoding: str = Field("utf-8", description="File encoding")


class FileReadOutput(ToolOutput):
    """Output from file reading operations"""

    content: str | None = None
    file_path: str
    size_bytes: int


class FileWriteInput(ToolInput):
    """Input for file writing operations"""

    file_path: str = Field(..., description="Path to file to write")
    content: str = Field(..., description="Content to write")
    encoding: str = Field("utf-8", description="File encoding")
    create_dirs: bool = Field(True, description="Create parent directories")


class FileWriteOutput(ToolOutput):
    """Output from file writing operations"""

    file_path: str
    bytes_written: int


class FileListInput(ToolInput):
    """Input for directory listing operations"""

    directory_path: str = Field(..., description="Directory to list")
    pattern: str | None = Field(None, description="File pattern filter")
    recursive: bool = Field(False, description="List recursively")


class FileListOutput(ToolOutput):
    """Output from directory listing operations"""

    directory_path: str
    files: list[str]


# Command Operations
class CommandRunInput(ToolInput):
    """Input for command execution operations"""

    command: str = Field(..., description="Command to execute")
    cwd: str | None = Field(None, description="Working directory")
    timeout: float = Field(30.0, description="Timeout in seconds")
    shell: bool = Field(True, description="Use shell")
    env: dict[str, str] | None = Field(None, description="Environment variables")


class CommandRunOutput(ToolOutput):
    """Output from command execution operations"""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
