"""GearMeshing-AI Command Line Interface.

This package provides a comprehensive CLI for managing GearMeshing-AI agents,
workflows, and system operations.

Usage:
    from gearmeshing_ai.command_line import main
    main()
"""

from gearmeshing_ai.command_line.app import main, app

__all__ = ["main", "app"]
