"""AI Agent Tools Module.

This module provides tool handlers, definitions, and security validation
for AI agent operations including file operations and command execution.
"""

# Tool handlers
from .handlers import (
    read_file_handler,
    write_file_handler,
    list_files_handler,
    run_command_handler,
)

# Tool definitions
from .definitions import (
    ToolInput,
    ToolOutput,
    FileReadInput,
    FileReadOutput,
    FileWriteInput,
    FileWriteOutput,
    FileListInput,
    FileListOutput,
    CommandRunInput,
    CommandRunOutput,
)

# Security utilities
from .security import (
    ValidationResult,
    validate_file_path,
    validate_command,
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
