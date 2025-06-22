# Changelog

## [1.0.11] - 2025-06-22

### Changed
- Replaced `init_dependency.py` with simpler `check_dependency.py` module
- Refactored dependency checking to use separate `test_node()` and `test_npx()` functions
- Removed automatic Node.js installation functionality in favor of explicit dependency checking
- Updated package includes in `pyproject.toml` to reference new dependency module

### Fixed
- Simplified dependency handling by removing complex installation logic
- Improved error messages for missing Node.js or npx dependencies

## [1.0.8] - 2025-06-21

### Added
- Automatic Node.js installation support

## [1.0.7] - 2025-06-21

### Changed
- Enhanced `init_dependency.py` module with improved documentation and error handling
- Added automatic `npx` installation if not available
- Improved cross-platform Node.js installation logic
- Better error messages throughout the dependency initialization process

## [1.0.6] - 2025-06-21

### Added
- Modern Python packaging with `pyproject.toml` and hatchling build system
- Automatic Node.js installation via `init_dependency.py` module
- Terminal handling improvements with input flushing and proper cleanup
- GitHub Actions workflow for automated code quality checks
- Pre-commit hooks configuration with Ruff linter and formatter
- VS Code settings for consistent development experience
- CLAUDE.md documentation for Claude Code AI assistant integration
- Support for `uv` tool as recommended installation method
- Console script entry point `claude-monitor` for system-wide usage
- Comprehensive .gitignore for Python projects
- CHANGELOG.md for tracking project history

### Changed
- Renamed main script from `ccusage_monitor.py` to `claude_monitor.py`
- Use `npx ccusage` instead of direct `ccusage` command for better compatibility
- Improved terminal handling to prevent input corruption during monitoring
- Updated all documentation files (README, CONTRIBUTING, DEVELOPMENT, TROUBLESHOOTING)
- Enhanced project structure for PyPI packaging readiness

### Fixed
- Terminal input corruption when typing during monitoring
- Proper Ctrl+C handling with cursor restoration
- Terminal settings restoration on exit

[1.0.11]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v1.0.11
[1.0.8]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v1.0.8
[1.0.7]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v1.0.7
[1.0.6]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v1.0.6
