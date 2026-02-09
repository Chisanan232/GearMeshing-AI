"""AI Agent Tools Module.

This module provides tool handlers, definitions, and security validation
for AI agent operations including file operations and command execution.
"""

# Tool handlers
# Tool definitions
from .definitions import (
    CommandRunInput,
    CommandRunOutput,
    FileListInput,
    FileListOutput,
    FileReadInput,
    FileReadOutput,
    FileWriteInput,
    FileWriteOutput,
    ToolInput,
    ToolOutput,
)
from .handlers import (
    list_files_handler,
    read_file_handler,
    run_command_handler,
    write_file_handler,
)

# Security utilities
from .security import (
    ValidationResult,
    validate_command,
    validate_file_path,
)

__all__ = [
    # Handlers
    "read_file_handler",
    "write_file_handler",
    "list_files_handler",
    "run_command_handler",
    # Base definitions
    "ToolInput",
    "ToolOutput",
    # File operations
    "FileReadInput",
    "FileReadOutput",
    "FileWriteInput",
    "FileWriteOutput",
    "FileListInput",
    "FileListOutput",
    # Command operations
    "CommandRunInput",
    "CommandRunOutput",
    # Security
    "ValidationResult",
    "validate_file_path",
    "validate_command",
]
