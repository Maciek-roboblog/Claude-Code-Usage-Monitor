# Changelog

## [2.0.0] - 2025-06-25

### Added
- **🎨 Smart Theme System**: Automatic light/dark theme detection for optimal terminal appearance
  - Intelligent theme detection based on terminal environment, system settings, and background color
  - Manual theme override options: `--theme light`, `--theme dark`, `--theme auto`
  - Theme debug mode: `--theme-debug` for troubleshooting theme detection
  - Platform-specific theme detection (macOS, Windows, Linux)
  - Support for VSCode integrated terminal, iTerm2, Windows Terminal
- **📊 Enhanced Progress Bar Colors**: Improved visual feedback with smart color coding
  - Token usage progress bars with three-tier color system:
    - 🟢 Green (0-49%): Safe usage level
    - 🟡 Yellow (50-89%): Warning - approaching limit  
    - 🔴 Red (90-100%): Critical - near or at limit
  - Time progress bars with consistent blue indicators
  - Burn rate velocity indicators with emoji feedback (🐌➡️🚀⚡)
- **🌈 Rich Theme Support**: Optimized color schemes for both light and dark terminals
  - Dark theme: Bright colors optimized for dark backgrounds
  - Light theme: Darker colors optimized for light backgrounds
  - Automatic terminal capability detection (truecolor, 256-color, 8-color)
- **🔧 Advanced Terminal Detection**: Comprehensive environment analysis
  - COLORTERM, TERM_PROGRAM, COLORFGBG environment variable support
  - Terminal background color querying using OSC escape sequences
  - Cross-platform system theme integration

### Changed
- **Breaking**: Progress bar color logic now uses semantic color names (`cost.low`, `cost.medium`, `cost.high`)
- Enhanced visual consistency across different terminal environments
- Improved accessibility with better contrast ratios in both themes

### Technical Details
- New `usage_analyzer/themes/` module with theme detection and color management
- `ThemeDetector` class with multi-method theme detection algorithm
- Rich theme integration with automatic console configuration
- Environment-aware color selection for maximum compatibility

## [1.0.19] - 2025-06-23

### Fixed
- Fixed timezone handling by locking calculation to Europe/Warsaw timezone
- Separated display timezone from reset time calculation for improved reliability
- Removed dynamic timezone input and related error handling to simplify reset time logic

## [1.0.17] - 2025-06-23

### Added
- Loading screen that displays immediately on startup to eliminate "black screen" experience
- Visual feedback with header and "Fetching Claude usage data..." message during initial data load

## [1.0.16] - 2025-06-23

### Fixed
- Fixed UnboundLocalError when Ctrl+C is pressed by initializing color variables at the start of main()
- Fixed ccusage command hanging indefinitely by adding 30-second timeout to subprocess calls
- Added ccusage availability check at startup with helpful error messages
- Improved error display when ccusage fails with better debugging information
- Fixed npm 7+ compatibility issue where npx doesn't find globally installed packages

### Added
- Timeout handling for all ccusage subprocess calls to prevent hanging
- Pre-flight check for ccusage availability before entering main loop
- More informative error messages suggesting installation steps and login requirements
- Dual command execution: tries direct `ccusage` command first, then falls back to `npx ccusage`
- Detection and reporting of which method (direct or npx) is being used

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

[2.0.0]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v2.0.0
[1.0.19]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v1.0.19
[1.0.17]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v1.0.17
[1.0.16]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v1.0.16
[1.0.11]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v1.0.11
[1.0.8]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v1.0.8
[1.0.7]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v1.0.7
[1.0.6]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v1.0.6
