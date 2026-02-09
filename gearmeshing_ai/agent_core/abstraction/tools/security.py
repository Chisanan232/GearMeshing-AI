"""Security validation utilities for AI agent tools.

This module provides security validation for file operations and command execution
to prevent dangerous operations and ensure safe tool usage.
"""

import os
import pathlib
from typing import List, Optional
from pydantic import BaseModel


class ValidationResult(BaseModel):
    """Result of security validation"""
    valid: bool
    error: Optional[str] = None


def validate_file_path(file_path: str, operation: str) -> ValidationResult:
    """Validate file path for security
    
    Args:
        file_path: The file path to validate
        operation: The operation type ('read', 'write', 'list')
        
    Returns:
        ValidationResult indicating if the path is safe to use
    """
    try:
        if not file_path:
            return ValidationResult(
                valid=False,
                error="File path cannot be empty"
            )
        
        # Check for directory traversal attempts before resolving
        if '..' in file_path:
            return ValidationResult(
                valid=False,
                error="Directory traversal not allowed"
            )
        
        path = pathlib.Path(file_path).resolve()
        
        # Check file extension restrictions for write operations
        dangerous_extensions = ['.exe', '.bat', '.sh', '.cmd', '.scr', '.vbs', '.com', '.pif']
        if path.suffix.lower() in dangerous_extensions and operation == "write":
            return ValidationResult(
                valid=False,
                error=f"File extension {path.suffix} not allowed for write operations"
            )
        
        # Additional security checks can be added here:
        # - Allowed directories check
        # - File size limits  
        # - Permission checks
        # - System directory protection
        
        return ValidationResult(valid=True)
        
    except Exception as e:
        return ValidationResult(
            valid=False,
            error=f"Path validation error: {str(e)}"
        )


def validate_command(command: str) -> ValidationResult:
    """Validate command for security
    
    Args:
        command: The command string to validate
        
    Returns:
        ValidationResult indicating if the command is safe to execute
    """
    try:
        if not command:
            return ValidationResult(
                valid=False,
                error="Command cannot be empty"
            )
        
        # Check for dangerous commands
        dangerous_commands = [
            'rm -rf', 'del /f', 'format', 'fdisk', 'mkfs', 'dd if=/dev/zero',
            'chmod 777', 'chown root', 'sudo rm', 'su root', 'passwd',
            'crontab', 'systemctl', 'service', 'init', 'shutdown', 'reboot'
        ]
        
        command_lower = command.lower()
        
        for dangerous in dangerous_commands:
            if dangerous in command_lower:
                return ValidationResult(
                    valid=False,
                    error=f"Command '{dangerous}' is not allowed"
                )
        
        # Check for shell injection attempts
        dangerous_patterns = ['&&', '||', ';', '|', '`', '$(', '>', '>>', '<']
        for pattern in dangerous_patterns:
            if pattern in command:
                return ValidationResult(
                    valid=False,
                    error=f"Command pattern '{pattern}' not allowed"
                )
        
        # Additional security checks can be added here:
        # - Command whitelist
        # - Argument validation
        # - Resource limits
        # - User permission checks
        
        return ValidationResult(valid=True)
        
    except Exception as e:
        return ValidationResult(
            valid=False,
            error=f"Command validation error: {str(e)}"
        )
