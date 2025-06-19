# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Claude Code Usage Monitor is a Python-based terminal application that provides real-time monitoring of Claude AI token usage. The project tracks token consumption, calculates burn rates, and predicts when tokens will be depleted across different Claude subscription plans.

## Core Architecture

### Main Components
- **ccusage_monitor.py**: Single-file Python application containing all monitoring logic
- **ccusage CLI integration**: Uses the `ccusage` npm package to fetch token usage data via `ccusage blocks --json`
- **Session management**: Tracks 5-hour rolling session windows with automatic detection
- **Plan detection**: Supports Pro (~7K), Max5 (~35K), Max20 (~140K), and custom_max (auto-detected) plans

### Key Functions
- `run_ccusage()`: Executes ccusage CLI and parses JSON output at ccusage_monitor.py:13
- `calculate_hourly_burn_rate()`: Analyzes token consumption patterns from the last hour at ccusage_monitor.py:101
- Session tracking logic handles overlapping 5-hour windows and automatic plan switching

## Development Commands

### Setup and Installation

#### Modern Installation with uv (Recommended)
```bash
# Install global dependency
npm install -g ccusage

# Install the tool directly with uv
uv tool install claude-usage-monitor

# Run from anywhere
ccusage-monitor
# or
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
chmod +x ccusage_monitor.py
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
uv run ccusage_monitor.py
```

### Running the Monitor

#### With uv tool installation
```bash
# Default mode (Pro plan)
ccusage-monitor
# or
claude-monitor

# Different plans
ccusage-monitor --plan max5
ccusage-monitor --plan max20
ccusage-monitor --plan custom_max

# Custom configuration
ccusage-monitor --reset-hour 9 --timezone US/Eastern
```

#### Traditional/Development mode
```bash
# Default mode (Pro plan)
python ccusage_monitor.py
./ccusage_monitor.py  # If made executable

# Different plans
./ccusage_monitor.py --plan max5
./ccusage_monitor.py --plan max20
./ccusage_monitor.py --plan custom_max

# Custom configuration
./ccusage_monitor.py --reset-hour 9 --timezone US/Eastern

# With uv in development
uv run ccusage_monitor.py --plan max5
```

### Testing
Currently no automated test suite. Manual testing involves:
- Running on different platforms (Linux, macOS, Windows)
- Testing with different Python versions (3.6+)
- Verifying plan detection and session tracking

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

### Future Development
See DEVELOPMENT.md for roadmap including:
- ML-powered auto-detection with DuckDB storage
- PyPI package distribution
- Docker containerization with web dashboard
- Enhanced analytics and prediction features