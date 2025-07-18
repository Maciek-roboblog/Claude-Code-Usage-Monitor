"""
Scripts module for Claude Code Usage Monitor.

This module contains utility scripts for Docker deployment and health monitoring.
"""

# Version information
__version__ = "1.0.19"

# Import main components for easier access
try:
    from .health_server import HealthCheckHandler, run_health_server

    __all__ = ["HealthCheckHandler", "run_health_server"]
except ImportError:
    # Module may not be available in all environments
    __all__ = []
