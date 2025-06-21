# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Running the Monitor
```bash
# Default Pro plan monitoring
python ccusage_monitor.py

# With specific plan
python ccusage_monitor.py --plan max5
python ccusage_monitor.py --plan max20
python ccusage_monitor.py --plan custom_max

# With custom timezone and reset hour
python ccusage_monitor.py --timezone America/New_York --reset-hour 9
```

### Development Setup
```bash
# Install global dependency
npm install -g ccusage

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install Python dependencies
pip install pytz

# Make executable (Linux/Mac)
chmod +x ccusage_monitor.py
```

### Testing
```bash
# Test ccusage integration
ccusage --version
ccusage blocks --json

# Verify monitor functionality
python ccusage_monitor.py --plan pro
```

## Architecture Overview

### Core Components

**Main Script (`ccusage_monitor.py`)**
- Single-file Python application (419 lines)
- Real-time monitoring with 3-second refresh intervals
- Terminal-based UI with ANSI colors and progress bars

**External Dependencies**
- `ccusage` (Node.js): CLI tool for Claude usage data (`npm install -g ccusage`)
- `pytz`: Python timezone handling library

### Key Functions

**Data Collection**
- `run_ccusage()`: Executes `ccusage blocks --json` and parses output
- `calculate_hourly_burn_rate()`: Analyzes token consumption across all sessions in last hour

**Display & UI**
- `create_token_progress_bar()`: Visual progress bars with color coding
- `create_time_progress_bar()`: Time-based progress visualization
- `print_header()`: Stylized terminal header with sparkles

**Time Management**
- `get_next_reset_time()`: Calculates session reset predictions based on 5-hour windows
- Supports custom timezones and reset hours

**Plan Detection**
- `get_token_limit()`: Dynamic token limits based on plan type
- Auto-switching from Pro to custom_max when limits exceeded
- Plans: pro (7K), max5 (35K), max20 (140K), custom_max (auto-detect)

### Session Logic

**Claude Code Sessions**
- 5-hour rolling windows from first message
- Multiple overlapping sessions possible
- Token limits apply per session
- Default reference reset times: 04:00, 09:00, 14:00, 18:00, 23:00

**Monitoring Features**
- Real-time token usage tracking
- Burn rate calculation (tokens/minute)
- Predictive analytics (when tokens will run out)
- Smart plan switching when limits exceeded
- Visual progress bars and status indicators

### Error Handling
- Graceful handling of ccusage failures
- Automatic cursor restoration on exit
- Clear error messages for common issues
- Fallback behaviors for missing data

## Development Notes

### Future Architecture Plans
- ML-powered auto-detection with DuckDB storage
- PyPI package structure with proper CLI entry points
- Docker containerization with optional web dashboard
- Modular architecture separating core logic, UI, and ML components

### Code Style
- Python 3.6+ compatible
- Single-file design for simplicity
- Extensive use of datetime and timezone handling
- Terminal optimization with ANSI escape sequences
- Real-time updates without screen flicker

### Integration Points
- Depends on `ccusage` CLI tool for data fetching
- Reads Claude Code session data via JSON API
- Terminal-based display with cross-platform compatibility
- Virtual environment recommended for Python dependencies