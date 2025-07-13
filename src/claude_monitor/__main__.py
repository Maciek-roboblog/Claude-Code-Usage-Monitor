#!/usr/bin/env python3
"""Module execution entry point for Claude Monitor.

Allows running the package as a module: python -m claude_monitor
"""

from .cli.main import main

if __name__ == "__main__":
    main()
