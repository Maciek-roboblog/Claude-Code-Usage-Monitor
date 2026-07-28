# Changelog

## [4.0.0] - Unreleased

### Bug Fixes
- **Model distribution shows all families**: `ModelUsageBar` now renders Sonnet, Opus, Fable, Mythos, Haiku, and an "Other" bucket instead of only Sonnet/Opus. Models no longer vanish from the usage bar or skew the displayed percentages. (#124, #164)
- **Plan is now saved and restored**: the selected `--plan` is persisted in `last_used.json` and reloaded on the next run; an explicit `--plan` on the command line still takes priority. (#162)
- **Saved theme no longer overwritten**: an explicitly chosen `light`/`dark`/`classic` theme is preserved across runs instead of being silently replaced by background auto-detection. (#102, #200)
- **Clear message on unsupported Python**: running on Python older than 3.9 now prints a clear "Python 3.9+ is required" message (with a `uv` install hint) instead of failing cryptically; the version check is now actually wired into startup and uses the documented 3.9 minimum. (#172)
- **Helpful "no data" diagnostic**: when no Claude data directory is found, the monitor now lists the exact paths it searched and how to fix it, instead of a single terse line / blank screen. (#110)
- **CLAUDE_CONFIG_DIR is honored**: when set, usage data under `$CLAUDE_CONFIG_DIR/projects` is discovered (comma-separated directories supported) and checked before the standard locations; path discovery also deduplicates repeated directories. (#116)
- **Up-to-date, version-specific model pricing**: token costs now use current Anthropic rates — Opus 4.5+ at $5/$25 (previously billed at the legacy $15/$75, a 3x overcharge), Haiku 4.5 at $1/$5, and Fable 5 at $10/$50 — while older models (Opus 3/4.0/4.1, Haiku 3/3.5) keep their original rates. (#182)
- **Claude 5 model support**: Fable 5, Sonnet 5, and Mythos 5 keep their full model IDs and appear in model-family output. Sonnet 5 usage before September 1, 2026 at 00:00 UTC uses its $2/$10 introductory rate; later usage uses $3/$15. Fable 5 and Mythos 5 use $10/$50.
- **`--reset-hour` is now actually applied**: the flag was accepted and persisted but never used in any calculation. It now sets the daily rollover boundary in the daily/monthly table views, so a usage day runs from `reset_hour` to `reset_hour` (e.g. `--reset-hour 4` counts 02:00 toward the previous day) instead of midnight to midnight. It deliberately does not shift the rolling 5-hour window, whose reset comes from the session/official data. (#95, #96, #106)
- **Reset time prefers what Claude reported**: when a session block contains a rate-limit message with a reset time, that time is shown as the reset instead of the start-plus-5h estimate, so the displayed reset matches what Claude actually told you. Official statusline limits still take precedence when available. (#114, #106)
- **Epoch reset timestamps parsed in UTC**: a numeric reset timestamp from a `limit reached|<epoch>` message was parsed as local wall time and then mislabeled as UTC, shifting the shown reset by the host's offset on non-UTC machines (e.g. two hours off in Central Europe). Epochs are now interpreted as the absolute UTC instant they are. (#106, #220)
- **Windows and local timezone detection now use IANA zones**: Windows auto-detection now uses `tzlocal` and refuses to return raw `tzutil` labels such as `Eastern Standard Time` as if they were valid `pytz` zones; the accepted `--timezone local` alias now resolves before display code runs. Added regression coverage for Istanbul reset display so reset times do not drift by an extra hour. (#188, #98, #121, #220)
- **Non-Anthropic models are no longer priced as Claude**: a model routed through Claude Code Router (e.g. a GPT or DeepSeek model) was silently billed at the Sonnet rate, inflating reported cost. Models that are not recognizably Anthropic now report as unpriced ($0) instead of a fabricated Claude cost; unknown but clearly-Claude models still use the family fallback. (#217, #199)
- **Official limits hardened against stale and malformed captures**: a statusline capture older than the freshness window no longer drives the displayed reset, status, or `confidence: official` label (it falls back to the local estimate, flagged `stale`); an official percentage drives the exit code even with no local session; and non-finite values (`NaN`/`Infinity`) in a capture are rejected instead of crashing the reader or emitting invalid JSON. (#119, #108)
- **Rich TUI now uses official-aware limit overlays**: the interactive live view and rich `--once` output now route token usage through the same snapshot used by compact/state/export surfaces, so fresh statusline limits can drive the displayed five-hour percentage with an explicit `official` label instead of showing a conflicting local-estimate bar.
- **Time-to-reset alignment and Windows glyph fallback**: progress rows now pad by terminal display width using `wcwidth`, so clock emoji no longer shift the "Time to Reset" bar. Startup forces UTF-8 output where possible and enables an ASCII fallback for non-UTF-8 Windows streams. (#144, #160)

### Features
- **`--hide-model-distribution`**: new flag to hide the model distribution bar in the live view. (#161)
- **`--no-header` / `--no-emoji`**: hide the header banner, or render the live view without emoji (plain output). (#57)
- **`--once --output {rich,json,text}`**: one-shot, machine-readable usage snapshot for hooks/CI/companions instead of parsing the live TUI. Emits a versioned schema (`schema_version`, `source`, `confidence`, `limits`, `local`, `local_history`, `forecast`) with every number labeled `local_estimate`, plus automation exit codes (0 ok, 10 near limit, 11 limit hit, 20 indeterminate, 30 no data). Official account/weekly limits are shaped in but deferred until the statusline reader lands. (#126)
- **`--write-state`**: continuously write the same versioned snapshot to a state file (default `~/.claude-monitor/state/latest.json`, override with `--state-file`) that status bars, tray apps, and dashboards can poll. Writes are atomic (temp file + replace) so a reader never sees a partial file; reuses the one-shot builder. (#184)
- **`--compact`**: single-line output for tmux/status bars — usage percent, tokens used/limit, burn rate, reset time, and session cost on one line. Works both live (updates in place) and one-shot with `--once`. Built from the same snapshot as `--once`, so the numbers never diverge from the full views. (#65, #17, #111)
- **`--set-terminal-title`**: opt-in terminal title updates from the canonical snapshot, with a validated `--title-format` template (`pct`, `plan`, `used`, `limit`, `cost`, `reset`) so live mode and `--once` use the same values as state/export surfaces. (#142)
- **Pace, official weekly, and forecast labels in snapshot outputs**: snapshots now include a source-labeled pace indicator based on the active five-hour reset, local history is explicitly labeled as history, and forecast displays use `Today`/`Tomorrow`/date context with an estimated tag. `--compact` adds one `pace=...` token and only renders `7d` when the official `seven_day` statusline block is present. Forecasts now stop instead of predicting beyond a hit limit. (#216, #183, #128)
- **`--data-paths` multi-source substrate**: the reader, live mode, table views, and one-shot snapshot path now accept multiple Claude data directories without collapsing to the first path. Entries are deduplicated across directories, tagged with `source.kind` and account path, and split into separate 5-hour blocks per source so multiple profiles/accounts do not merge into one limit window. WSL Claude data paths are discovered additively when available. (#196, #92, #127, #94)
- **`--warehouse` persistent usage store**: opt-in versioned JSON usage warehouse with atomic writes, retention pruning, per source/account/project/model/day records, and daily dimension queries. The default stays off; `--warehouse-file` and `--warehouse-retention-days` control location and retention. Daily/monthly tables also keep `--date-format` and `--abbreviate-tokens`, with sparklines available only behind `--sparklines`. (#145, #175, #8, #43, #120)
- **Warehouse reports and exports**: `--view entries|sessions|burn-rate --output json|csv` now exports warehouse-backed reports with source/provenance fields, valid CSV/JSON, session counts, P50/P90/P95 metrics, sessions ended by detected limits, burn-rate rows, and plan recommendations explicitly labeled as estimates. (#8, #120, #80, #43)
- **Team plan label and experimental usage API**: `--plan team` is accepted as an unverified estimate label with guidance to prefer official statusline data or `--plan custom`, and `--api` adds an opt-in experimental Anthropic OAuth usage reader with TTL cache and Retry-After backoff. Experimental API limits are labeled `confidence: experimental` and never override fresh official statusline limits. (#195, #202, #193, #157)
- **Related Tools and adapter boundary**: README now shows the Awesome Claude Code badge, documents external companion tools that should consume `--write-state` / `--once --output json`, and codifies that provider adapters must use separate `source.kind` values instead of auto-merging non-Claude data into the Claude 5-hour subscription window. Cursor and Claude Desktop are documented as out of scope unless they expose a local usage/limit signal. (#219, #109, #177, #146, #198, #178, #176, #133, #166, #24, #25)
- **`--filter-models anthropic`**: count only Claude models, excluding non-Anthropic ones (e.g. GPT or DeepSeek routed through Claude Code Router) from the usage, cost, and limit math so they no longer pollute the Claude session reading. Applies consistently to the live view, one-shot/state output, and the daily/monthly tables; defaults to `all` (no change). (#113)
- **Official limits via the statusline (`--statusline`)**: a Claude Code statusline hook that reads the session JSON on stdin, captures the official `rate_limits` (5-hour and 7-day `used_percentage` + `resets_at`, Pro/Max on Claude Code 2.1.80+), and prints a one-line status. Add `"statusLine": {"type": "command", "command": "claude-monitor --statusline"}` to Claude Code's settings. When a capture is present, the monitor uses the **official** percentage and reset as the source of truth (`confidence: official`) and labels it as such; the 5-hour figure also drives the `--once` exit code. Without it, every number stays a clearly-labeled local estimate. Captures older than 10 minutes are flagged `stale`. The known leak where `used_percentage` can carry the reset epoch is guarded against. (#119, #108, #104, #97, #150, #152)

## [3.1.0] - 2025-07-23

### 🆕 New Features
- **📊 Usage Analysis Views**: Added `--view` parameter for different time aggregation periods
  - `--view realtime` (default): Live monitoring with real-time updates
  - `--view daily`: Daily token usage aggregated in comprehensive table format
  - `--view monthly`: Monthly token usage aggregated for long-term trend analysis

### 📝 Use Cases
- **Daily Analysis**: Track daily usage patterns and identify peak consumption periods
- **Monthly Planning**: Long-term budget analysis and trend identification
- **Usage Optimization**: Historical data analysis for better resource planning

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

[4.0.0]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v4.0.0
[3.0.0]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v3.0.0
[2.0.0]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v2.0.0
[1.0.19]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v1.0.19
[1.0.17]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v1.0.17
[1.0.16]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v1.0.16
[1.0.11]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v1.0.11
[1.0.8]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v1.0.8
[1.0.7]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v1.0.7
[1.0.6]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v1.0.6
