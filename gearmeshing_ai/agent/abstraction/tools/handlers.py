"""Tool handlers for AI agent operations.

This module contains the core implementation of tool handlers that perform
file operations and command execution with security validation.
"""

import asyncio
import os
import pathlib

from .definitions import (
    CommandRunInput,
    CommandRunOutput,
    FileListInput,
    FileListOutput,
    FileReadInput,
    FileReadOutput,
    FileWriteInput,
    FileWriteOutput,
)
from .security import validate_command, validate_file_path


async def read_file_handler(input_data: FileReadInput) -> FileReadOutput:
    """Handle file read operations with security validation

    Args:
        input_data: File read parameters including path and encoding

    Returns:
        FileReadOutput with file content or error information

    """
    try:
        # Security validation
        validation_result = validate_file_path(input_data.file_path, "read")
        if not validation_result.valid:
            return FileReadOutput(
                success=False, error_message=validation_result.error, file_path=input_data.file_path, size_bytes=0
            )

        path = pathlib.Path(input_data.file_path)
        if not path.exists():
            return FileReadOutput(
                success=False,
                error_message=f"File not found: {input_data.file_path}",
                file_path=input_data.file_path,
                size_bytes=0,
            )

        content = path.read_text(encoding=input_data.encoding)
        return FileReadOutput(
            success=True, content=content, file_path=str(path), size_bytes=len(content.encode(input_data.encoding))
        )
    except Exception as e:
        return FileReadOutput(success=False, error_message=str(e), file_path=input_data.file_path, size_bytes=0)


async def write_file_handler(input_data: FileWriteInput) -> FileWriteOutput:
    """Handle file write operations with security validation

    Args:
        input_data: File write parameters including path, content, and options

    Returns:
        FileWriteOutput with write result or error information

    """
    try:
        # Security validation
        validation_result = validate_file_path(input_data.file_path, "write")
        if not validation_result.valid:
            return FileWriteOutput(
                success=False, error_message=validation_result.error, file_path=input_data.file_path, bytes_written=0
            )

        path = pathlib.Path(input_data.file_path)

        # Create parent directories if needed
        if input_data.create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)

        bytes_written = path.write_text(input_data.content, encoding=input_data.encoding)

        return FileWriteOutput(success=True, file_path=str(path), bytes_written=bytes_written)
    except Exception as e:
        return FileWriteOutput(success=False, error_message=str(e), file_path=input_data.file_path, bytes_written=0)


async def list_files_handler(input_data: FileListInput) -> FileListOutput:
    """Handle directory listing operations with security validation

    Args:
        input_data: Directory listing parameters including path and filters

    Returns:
        FileListOutput with file list or error information

    """
    try:
        # Security validation
        validation_result = validate_file_path(input_data.directory_path, "list")
        if not validation_result.valid:
            return FileListOutput(
                success=False, error_message=validation_result.error, directory_path=input_data.directory_path, files=[]
            )

        path = pathlib.Path(input_data.directory_path)
        if not path.exists():
            return FileListOutput(
                success=False,
                error_message=f"Directory not found: {input_data.directory_path}",
                directory_path=input_data.directory_path,
                files=[],
            )

        if input_data.recursive:
            if input_data.pattern:
                files = [str(p) for p in path.rglob(input_data.pattern)]
            else:
                files = [str(p) for p in path.rglob("*")]
        else:
            if input_data.pattern:
                files = [str(p) for p in path.glob(input_data.pattern)]
            else:
                files = [str(p) for p in path.iterdir()]

        return FileListOutput(success=True, directory_path=str(path), files=sorted(files))
    except Exception as e:
        return FileListOutput(success=False, error_message=str(e), directory_path=input_data.directory_path, files=[])


async def run_command_handler(input_data: CommandRunInput) -> CommandRunOutput:
    """Handle command execution with security validation

    Args:
        input_data: Command execution parameters including command and options

    Returns:
        CommandRunOutput with execution result or error information

    """
    try:
        # Security validation
        validation_result = validate_command(input_data.command)
        if not validation_result.valid:
            return CommandRunOutput(
                success=False,
                error_message=validation_result.error,
                command=input_data.command,
                exit_code=-1,
                stdout="",
                stderr="",
                duration_seconds=0.0,
            )

        start_time = asyncio.get_event_loop().time()

        # Prepare environment
        env = None
        if input_data.env:
            current_env = os.environ.copy()
            current_env.update(input_data.env)
            env = current_env

        # Execute command
        process = await asyncio.create_subprocess_shell(
            input_data.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=input_data.cwd,
            env=env,
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=input_data.timeout)
        except TimeoutError:
            process.kill()
            await process.wait()
            return CommandRunOutput(
                success=False,
                error_message=f"Command timed out after {input_data.timeout} seconds",
                command=input_data.command,
                exit_code=-1,
                stdout="",
                stderr="",
                duration_seconds=input_data.timeout,
            )

        duration = asyncio.get_event_loop().time() - start_time

        return CommandRunOutput(
            success=process.returncode == 0,
            command=input_data.command,
            exit_code=process.returncode,
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
            duration_seconds=duration,
        )

    except Exception as e:
        return CommandRunOutput(
            success=False,
            error_message=str(e),
            command=input_data.command,
            exit_code=-1,
            stdout="",
            stderr="",
            duration_seconds=0.0,
        )
