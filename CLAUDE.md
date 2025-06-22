# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Claude Code Usage Monitor is a Python-based terminal application that provides real-time monitoring of Claude AI token usage. The project tracks token consumption, calculates burn rates, and predicts when tokens will be depleted across different Claude subscription plans.

## Core Architecture

### Project Structure
This is a single-file Python application (545 lines) with modern packaging:
- **claude_monitor.py**: Main application containing all monitoring logic
- **pyproject.toml**: Modern Python packaging configuration with console script entry points
- **ccusage CLI integration**: External dependency on `ccusage` npm package for data fetching

### Key Components
- **Data Collection**: Uses `ccusage blocks --json` to fetch Claude usage data
- **Session Management**: Tracks 5-hour rolling session windows with automatic detection
- **Plan Detection**: Supports Pro (~7K), Max5 (~35K), Max20 (~140K), and custom_max (auto-detected) plans
- **Real-time Display**: Terminal UI with progress bars and burn rate calculations
- **Console Scripts**: Single entry point (`claude-monitor`) calling `main()`

### Key Functions
- `run_ccusage()`: Executes ccusage CLI and parses JSON output at claude_monitor.py:13
- `calculate_hourly_burn_rate()`: Analyzes token consumption patterns from the last hour at claude_monitor.py:101
- `main()`: Entry point function at claude_monitor.py:249 for console script integration
- Session tracking logic handles overlapping 5-hour windows and automatic plan switching

## Development Commands

### Setup and Installation

#### Modern Installation with uv (Recommended)
```bash
# Install global dependency
npm install -g ccusage

# Clone and install the tool with uv
git clone https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor.git
cd Claude-Code-Usage-Monitor
uv tool install .

# Run from anywhere
claude-monitor
```

#### Traditional Installation
```bash
# Install global dependency
npm install -g ccusage

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install Python dependencies
pip install pytz

# Make executable (Linux/Mac)
chmod +x claude_monitor.py
```

#### Development Setup with uv
```bash
# Install global dependency
npm install -g ccusage

# Clone and set up for development
git clone https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor.git
cd Claude-Code-Usage-Monitor

# Install in development mode with uv
uv sync
uv run claude_monitor.py
```

### Running the Monitor

#### With uv tool installation
```bash
# Default mode (Pro plan)
claude-monitor

# Different plans
claude-monitor --plan max5
claude-monitor --plan max20
claude-monitor --plan custom_max

# Custom configuration
claude-monitor --reset-hour 9 --timezone US/Eastern
```

#### Traditional/Development mode
```bash
# Default mode (Pro plan)
python claude_monitor.py
./claude_monitor.py  # If made executable

# Different plans
./claude_monitor.py --plan max5
./claude_monitor.py --plan max20
./claude_monitor.py --plan custom_max

# Custom configuration
./claude_monitor.py --reset-hour 9 --timezone US/Eastern

# With uv in development
uv run claude_monitor.py --plan max5
```

### Building and Testing

#### Package Building
```bash
# Build package with uv
uv build

# Verify build artifacts
ls dist/  # Should show .whl and .tar.gz files
```

#### Testing Installation
```bash
# Test local installation
uv tool install --editable .

# Verify commands work
claude-monitor --help

# Test uninstall
uv tool uninstall claude-usage-monitor
```

#### Manual Testing
Currently no automated test suite. Manual testing involves:
- Running on different platforms (Linux, macOS, Windows)
- Testing with different Python versions (3.6+)
- Verifying plan detection and session tracking
- Testing console script entry points (`claude-monitor`)

## Dependencies

### External Dependencies
- **ccusage**: npm package for Claude token usage data (must be installed globally)
- **pytz**: Python timezone handling library

### Standard Library Usage
- subprocess: For executing ccusage CLI commands
- json: For parsing ccusage output
- datetime/timedelta: For session time calculations
- argparse: For command-line interface

## Development Notes

### Session Logic
The monitor operates on Claude's 5-hour rolling session system:
- Sessions start with first message and last exactly 5 hours
- Multiple sessions can be active simultaneously
- Token limits apply per 5-hour session window
- Burn rate calculated from all sessions in the last hour

### Plan Detection
- Starts with Pro plan (7K tokens) by default
- Automatically switches to custom_max when Pro limit exceeded
- custom_max scans previous sessions to find actual token limits
- Supports manual plan specification via command line

## Package Structure

### Console Script Entry Points
The `pyproject.toml` defines one console command:
```toml
[project.scripts]
claude-monitor = "claude_monitor:main"
```
This command calls the `main()` function in claude_monitor.py.

### Build Configuration
- **Build backend**: hatchling (modern Python build system)
- **Python requirement**: >=3.6 for broad compatibility
- **Package includes**: Main script, documentation files, license

### Future Development
See DEVELOPMENT.md for roadmap including:
- ML-powered auto-detection with DuckDB storage
- PyPI package distribution
- Docker containerization with web dashboard
- Enhanced analytics and prediction features
