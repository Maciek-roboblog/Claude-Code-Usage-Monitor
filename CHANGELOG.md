# Changelog

## [3.0.0] - 2025-01-13

### 🚨 Breaking Changes
- **Package Name Change**: Renamed from `claude-usage-monitor` to `claude-monitor`
  - New installation: `pip install claude-monitor` or `uv tool install claude-monitor`
  - New command aliases: `claude-monitor` and `cmonitor`
- **Python Requirement**: Minimum Python version raised from 3.8 to 3.9
- **Architecture Overhaul**: Complete rewrite from single-file to modular package structure
- **Entry Point Changes**: Module execution now via `claude_monitor.__main__:main`

### 🏗️ Complete Architectural Restructuring
- **📁 Professional Package Layout**: Migrated to `src/claude_monitor/` structure with proper namespace isolation
  - Replaced single `claude_monitor.py` file with comprehensive modular architecture
  - Implemented clean separation of concerns across 8 specialized modules
- **🔧 Modular Design**: New package organization:
  - `cli/` - Command-line interface and bootstrap logic
  - `core/` - Business logic, models, settings, calculations, and pricing
  - `data/` - Data management, analysis, and reading utilities
  - `monitoring/` - Real-time session monitoring and orchestration
  - `ui/` - User interface components, layouts, and display controllers
  - `terminal/` - Terminal management and theme handling
  - `utils/` - Formatting, notifications, timezone, and model utilities
- **⚡ Enhanced Performance**: Optimized data processing with caching, threading, and efficient session management

### 🎨 Rich Terminal UI System
- **💫 Rich Integration**: Complete UI overhaul using Rich library for professional terminal interface
  - Advanced progress bars with semantic color coding (🟢🟡🔴)
  - Responsive layouts with proper terminal width handling (80+ characters required)
  - Enhanced typography and visual hierarchy
- **🌈 Improved Theme System**: Enhanced automatic theme detection with better contrast ratios
- **📊 Advanced Display Components**: New progress visualization with burn rate indicators and time-based metrics

### 🔒 Type Safety and Validation
- **🛡️ Pydantic Integration**: Complete type safety implementation
  - Comprehensive settings validation with user-friendly error messages
  - Type-safe data models (`UsageEntry`, `SessionBlock`, `TokenCounts`)
  - CLI parameter validation with detailed feedback
- **⚙️ Smart Configuration**: Pydantic-based settings with last-used parameter persistence
- **🔍 Enhanced Error Handling**: Centralized error management with optional Sentry integration

### 📈 Advanced Analytics Features
- **🧮 P90 Percentile Calculations**: Machine learning-inspired usage prediction and limit detection
- **📊 Smart Plan Detection**: Auto-detection of Claude plan limits with custom plan support
- **⏱️ Real-time Monitoring**: Enhanced session tracking with threading and callback systems
- **💡 Intelligent Insights**: Advanced burn rate calculations and velocity indicators

### 🔧 Developer Experience Improvements
- **🚀 Modern Build System**: Migrated from Hatchling to Setuptools with src layout
- **🧪 Comprehensive Testing**: Professional test infrastructure with pytest and coverage reporting
- **📝 Enhanced Documentation**: Updated troubleshooting guide with v3.0.0-specific solutions
- **🔄 CI/CD Reactivation**: Restored and enhanced GitHub Actions workflows:
  - Multi-Python version testing (3.9-3.12)
  - Automated linting with Ruff
  - Trusted PyPI publishing with OIDC
  - Automated version bumping and changelog management

### 📦 Dependency and Packaging Updates
- **🆕 Core Dependencies Added**:
  - `pydantic>=2.0.0` & `pydantic-settings>=2.0.0` - Type validation and settings
  - `numpy>=1.21.0` - Advanced calculations
  - `sentry-sdk>=1.40.0` - Optional error tracking
  - `pyyaml>=6.0` - Configuration file support
- **⬆️ Dependency Upgrades**:
  - `rich`: `>=13.0.0` → `>=13.7.0` - Enhanced UI features
  - `pytz`: No constraint → `>=2023.3` - Improved timezone handling
- **🛠️ Development Tools**: Expanded with MyPy, Bandit, testing frameworks, and documentation tools

### 🎯 Enhanced User Features
- **🎛️ Flexible Configuration**: Support for auto-detection, manual overrides, and persistent settings
- **🌍 Improved Timezone Handling**: Enhanced timezone detection and validation
- **⚡ Performance Optimizations**: Faster startup times and reduced memory usage
- **🔔 Smart Notifications**: Enhanced feedback system with contextual messaging

### 🔧 Installation and Compatibility
- **📋 Installation Method Updates**: Full support for `uv`, `pipx`, and traditional pip installation
- **🐧 Platform Compatibility**: Enhanced support for modern Linux distributions with externally-managed environments
- **🛣️ Migration Path**: Automatic handling of legacy configurations and smooth upgrade experience

### 📚 Technical Implementation Details
- **🏢 Professional Architecture**: Implementation of SOLID principles with single responsibility modules
- **🔄 Async-Ready Design**: Threading infrastructure for real-time monitoring capabilities
- **💾 Efficient Data Handling**: Optimized JSONL parsing with error resilience
- **🔐 Security Enhancements**: Secure configuration handling and optional telemetry integration

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

[3.0.0]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v3.0.0
[2.0.0]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v2.0.0
[1.0.19]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v1.0.19
[1.0.17]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v1.0.17
[1.0.16]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v1.0.16
[1.0.11]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v1.0.11
[1.0.8]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v1.0.8
[1.0.7]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v1.0.7
[1.0.6]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v1.0.6
