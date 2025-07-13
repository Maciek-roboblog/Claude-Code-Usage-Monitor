# 🎯 Claude Code Usage Monitor v3.0.0
[![PyPI Version](https://img.shields.io/pypi/v/claude-monitor.svg)](https://pypi.org/project/claude-monitor/)
[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)
[![Test Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)]()

A beautiful real-time terminal monitoring tool for Claude AI token usage with advanced analytics, machine learning-based predictions, and Rich UI. Track your token consumption, burn rate, cost analysis, and get intelligent predictions about session limits.

![Claude Token Monitor Screenshot](https://raw.githubusercontent.com/Maciek-roboblog/Claude-Code-Usage-Monitor/main/doc/sc.png)

---

## 📑 Table of Contents

- [✨ Key Features](#-key-features)
- [🚀 Installation](#-installation)
  - [⚡ Modern Installation with uv (Recommended)](#-modern-installation-with-uv-recommended)
  - [📦 Installation with pip](#-installation-with-pip)
  - [🛠️ Other Package Managers](#️-other-package-managers)
- [📖 Usage](#-usage)
  - [Basic Usage](#basic-usage)
  - [Configuration Options](#configuration-options)
  - [Available Plans](#available-plans)
- [🙏 Please Help Test This Release!](#-please-help-test-this-release)
- [✨ Features & How It Works](#-features--how-it-works)
  - [Current Features](#current-features)
  - [Understanding Claude Sessions](#understanding-claude-sessions)
  - [Token Limits by Plan](#token-limits-by-plan)
  - [Smart Detection Features](#smart-detection-features)
- [🚀 Usage Examples](#-usage-examples)
  - [Common Scenarios](#common-scenarios)
  - [Best Practices](#best-practices)
- [🔧 Development Installation](#-development-installation)
- [Troubleshooting](#troubleshooting)
  - [Installation Issues](#installation-issues)
  - [Runtime Issues](#runtime-issues)
- [📞 Contact](#-contact)
- [📚 Additional Documentation](#-additional-documentation)
- [📝 License](#-license)
- [🤝 Contributors](#-contributors)
- [🙏 Acknowledgments](#-acknowledgments)



## ✨ Key Features

### 🚀 **v3.0.0 Major Update - Complete Architecture Rewrite**

- **🔄 Real-time monitoring** - Configurable refresh rates (0.1-20 Hz) with intelligent display updates
- **📊 Advanced Rich UI** - Beautiful color-coded progress bars, tables, and layouts with WCAG-compliant contrast
- **🔮 ML-based predictions** - P90 percentile calculations and intelligent session limit detection
- **🤖 Smart auto-detection** - Automatic plan switching with custom limit discovery
- **📋 Enhanced plan support** - Updated limits: Pro (44k), Max5 (88k), Max20 (220k), Custom (P90-based)
- **⚠️ Advanced warning system** - Multi-level alerts with cost and time predictions
- **💼 Professional Architecture** - Modular design with Single Responsibility Principle (SRP) compliance
- **🎨 Intelligent theming** - Scientific color schemes with automatic terminal background detection
- **⏰ Advanced scheduling** - Auto-detected system timezone and time format preferences
- **📈 Cost analytics** - Model-specific pricing with cache token calculations
- **🔧 Pydantic validation** - Type-safe configuration with automatic validation
- **📝 Comprehensive logging** - Optional file logging with configurable levels
- **🧪 Extensive testing** - 100+ test cases with full coverage
- **🎯 Error reporting** - Optional Sentry integration for production monitoring
- **⚡ Performance optimized** - Advanced caching and efficient data processing


## 🚀 Installation
### ⚡ Modern Installation with uv (Recommended)

**Why uv is the best choice:**
- ✅ Creates isolated environments automatically (no system conflicts)
- ✅ No Python version issues
- ✅ No "externally-managed-environment" errors
- ✅ Easy updates and uninstallation
- ✅ Works on all platforms

The fastest and easiest way to install and use the monitor:

[![PyPI](https://img.shields.io/pypi/v/claude-monitor.svg)](https://pypi.org/project/claude-monitor/)

#### Install from PyPI

```bash
# Install directly from PyPI with uv (easiest)
uv tool install claude-monitor

# Run from anywhere
claude-monitor  # or cmonitor for short
```

#### Install from Source

```bash
# Clone and install from source
git clone https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor.git
cd Claude-Code-Usage-Monitor
uv tool install .

# Run from anywhere
claude-monitor
```

#### First-time uv users
If you don't have uv installed yet, get it with one command:

```bash
# On Linux/macOS:
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows:
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# After installation, restart your terminal
```

### 📦 Installation with pip

```bash
# Install from PyPI
pip install claude-monitor

# If claude-monitor command is not found, add ~/.local/bin to PATH:
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc  # or restart your terminal

# Run from anywhere
claude-monitor  # or cmonitor for short
```

>
> **⚠️ PATH Setup**: If you see `WARNING: The script claude-monitor is installed in '/home/username/.local/bin' which is not on PATH`, follow the export PATH command above.
>
> **⚠️ Important**: On modern Linux distributions (Ubuntu 23.04+, Debian 12+, Fedora 38+), you may encounter an "externally-managed-environment" error. Instead of using `--break-system-packages`, we strongly recommend:
> 1. **Use uv instead** (see above) - it's safer and easier
> 2. **Use a virtual environment** - `python3 -m venv myenv && source myenv/bin/activate`
> 3. **Use pipx** - `pipx install claude-usage-monitor`
>
> See the Troubleshooting section for detailed solutions.

### 🛠️ Other Package Managers

#### pipx (Isolated Environments)
```bash
# Install with pipx
pipx install claude-monitor

# Run from anywhere
claude-monitor  # or cmonitor for short
```

#### conda/mamba
```bash
# Install with pip in conda environment
pip install claude-monitor

# Run from anywhere
claude-monitor  # or cmonitor for short
```

## 📖 Usage

### Basic Usage

#### With uv tool installation (Recommended)
```bash
# Default (Custom plan with auto-detection)
claude-monitor

# Alternative short command
cmonitor

# Exit the monitor
# Press Ctrl+C to gracefully exit
```

#### Development mode
If running from source, use `python -m claude_monitor` from the src/ directory.

### Configuration Options

#### Specify Your Plan

```bash
# Custom plan with P90 auto-detection (Default)
claude-monitor --plan custom

# Pro plan (~44,000 tokens)
claude-monitor --plan pro

# Max5 plan (~88,000 tokens)
claude-monitor --plan max5

# Max20 plan (~220,000 tokens)
claude-monitor --plan max20

# Custom plan with explicit token limit
claude-monitor --plan custom --custom-limit-tokens 100000
```

#### Custom Reset Times

```bash
# Reset at 3 AM
claude-monitor --reset-hour 3

# Reset at 10 PM
claude-monitor --reset-hour 22
```

#### Performance and Display Configuration

```bash
# Adjust refresh rate (1-60 seconds, default: 10)
claude-monitor --refresh-rate 5

# Adjust display refresh rate (0.1-20 Hz, default: 0.75)
claude-monitor --refresh-per-second 1.0

# Set time format (auto-detected by default)
claude-monitor --time-format 24h  # or 12h

# Force specific theme
claude-monitor --theme dark  # light, dark, classic, auto

# Clear saved configuration
claude-monitor --clear
```

#### Timezone Configuration

The default timezone is **auto-detected from your system**. Override with any valid timezone:

```bash
# Use US Eastern Time
claude-monitor --timezone America/New_York

# Use Tokyo time
claude-monitor --timezone Asia/Tokyo

# Use UTC
claude-monitor --timezone UTC

# Use London time
claude-monitor --timezone Europe/London
```

#### Logging and Debugging

```bash
# Enable debug logging
claude-monitor --debug

# Log to file
claude-monitor --log-file ~/.claude-monitor/logs/monitor.log

# Set log level
claude-monitor --log-level WARNING  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Available Plans

| Plan | Token Limit | Best For |
|------|-------------|----------|
| **custom** | P90 auto-detect | Intelligent limit detection (default) |
| **pro** | ~44,000 | Claude Pro subscription |
| **max5** | ~88,000 | Claude Max5 subscription |
| **max20** | ~220,000 | Claude Max20 subscription |

#### Advanced Plan Features

- **P90 Analysis**: Custom plan uses 90th percentile calculations from your usage history
- **Auto-switching**: Automatically switches plans when limits are exceeded
- **Cost Tracking**: Model-specific pricing with cache token calculations
- **Limit Detection**: Intelligent threshold detection with 95% confidence


## 🙏 Please Help Test This Release!

> **We need your help!** This is a new release and we want to ensure it works perfectly on all systems.
>
> **If something doesn't work:**
> 1. Switch to the [develop branch](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/tree/develop) for the latest fixes:
>    ```bash
>    git clone -b develop https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor.git
>    cd Claude-Code-Usage-Monitor
>    python3 -m venv venv
>    source venv/bin/activate  # On Windows: venv\Scripts\activate
>    pip install -e .
>    claude-monitor
>    ```
> 2. Create an issue with title format: **[MAIN-PROBLEM]: Your specific problem**
>    - Example: `[MAIN-PROBLEM]: Command not found after pip install on Ubuntu 24.04`
>    - Include your OS, Python version, and installation method
>    - [Create Issue Here](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/issues/new)
>
> **Thank you for helping make this tool better! 🚀**

## 🚀 What's New in v3.0.0

### Major Changes

#### **Complete Architecture Rewrite**
- Modular design with Single Responsibility Principle (SRP) compliance
- Pydantic-based configuration with type safety and validation
- Advanced error handling with optional Sentry integration
- Comprehensive test suite with 100+ test cases

#### **Enhanced Functionality**
- **P90 Analysis**: Machine learning-based limit detection using 90th percentile calculations
- **Updated Plan Limits**: Pro (44k), Max5 (88k), Max20 (220k) tokens
- **Cost Analytics**: Model-specific pricing with cache token calculations
- **Rich UI**: WCAG-compliant themes with automatic terminal background detection

#### **New CLI Options**
- `--refresh-per-second`: Configurable display refresh rate (0.1-20 Hz)
- `--time-format`: Automatic 12h/24h format detection
- `--custom-limit-tokens`: Explicit token limits for custom plans
- `--log-file` and `--log-level`: Advanced logging capabilities
- `--clear`: Reset saved configuration
- `cmonitor`: Short command alias

#### **Breaking Changes**
- Package name changed from `claude-usage-monitor` to `claude-monitor`
- Default plan changed from `pro` to `custom` (with auto-detection)
- Minimum Python version increased to 3.9+
- Command structure updated (see examples above)


## ✨ Features & How It Works

### v3.0.0 Architecture Overview

The new version features a complete rewrite with modular architecture following Single Responsibility Principle (SRP):

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   CLI Module    │  │ Settings/Config │  │ Error Handling  │
│ (Pydantic-based│  │ (Type-safe)     │  │ (Sentry-ready)  │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                      │                      │
┌─────────────────────────────────────────────────────────────┐
│                 Monitoring Orchestrator                      │
├─────────────────┬─────────────────┬─────────────────────────┤
│  Data Manager   │ Session Monitor │   UI Display Controller │
│ (Cache, Load)   │ (Real-time)     │    (Rich Components)    │
└─────────────────┴─────────────────┴─────────────────────────┘
         │                      │                      │
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Core Models     │  │ Analysis Engine │  │ Terminal Themes │
│ (Pydantic)      │  │ (P90 Calculator)│  │ (Adaptive)      │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Current Features

#### 🔄 Advanced Real-time Monitoring
- Configurable update intervals (1-60 seconds)
- High-precision display refresh (0.1-20 Hz)
- Intelligent change detection to minimize CPU usage
- Multi-threaded orchestration with callback system

#### 📊 Rich UI Components
- **Progress Bars**: WCAG-compliant color schemes with scientific contrast ratios
- **Data Tables**: Sortable columns with model-specific statistics
- **Layout Manager**: Responsive design that adapts to terminal size
- **Theme System**: Auto-detects terminal background for optimal readability

#### 🔮 Machine Learning Predictions
- **P90 Calculator**: 90th percentile analysis for intelligent limit detection
- **Burn Rate Analytics**: Multi-session consumption pattern analysis
- **Cost Projections**: Model-specific pricing with cache token calculations
- **Session Forecasting**: Predicts when sessions will expire based on usage patterns

#### 🤖 Intelligent Auto-Detection
- **Background Detection**: Automatically determines terminal theme (light/dark)
- **System Integration**: Auto-detects timezone and time format preferences
- **Plan Recognition**: Analyzes usage patterns to suggest optimal plans
- **Limit Discovery**: Scans historical data to find actual token limits

### Understanding Claude Sessions

#### How Claude Code Sessions Work

Claude Code operates on a **5-hour rolling session window system**:

1. **Session Start**: Begins with your first message to Claude
2. **Session Duration**: Lasts exactly 5 hours from that first message
3. **Token Limits**: Apply within each 5-hour session window
4. **Multiple Sessions**: Can have several active sessions simultaneously
5. **Rolling Windows**: New sessions can start while others are still active

#### Session Reset Schedule

**Default reference times** (in your configured timezone):
- `04:00`, `09:00`, `14:00`, `18:00`, `23:00`

> **⚠️ Important**: These are reference times for planning. Your actual token refresh happens exactly 5 hours after YOUR first message in each session.

**Example Session Timeline:**
```
10:30 AM - First message (Session A starts)
03:30 PM - Session A expires (5 hours later)

12:15 PM - First message (Session B starts)
05:15 PM - Session B expires (5 hours later)
```

#### Burn Rate Calculation

The monitor calculates burn rate using sophisticated analysis:

1. **Data Collection**: Gathers token usage from all sessions in the last hour
2. **Pattern Analysis**: Identifies consumption trends across overlapping sessions
3. **Velocity Tracking**: Calculates tokens consumed per minute
4. **Prediction Engine**: Estimates when current session tokens will deplete
5. **Real-time Updates**: Adjusts predictions as usage patterns change

### Token Limits by Plan

#### v3.0.0 Updated Plan Limits

| Plan | Limit (Tokens) | Cost Limit | Messages | Algorithm |
|------|---------------|------------|----------|-----------|
| **Claude Pro** | 44,000 | $18.00 | 250 | Fixed limit |
| **Claude Max5** | 88,000 | $35.00 | 1,000 | Fixed limit |
| **Claude Max20** | 220,000 | $140.00 | 2,000 | Fixed limit |
| **Custom** | P90-based | $200.00 | 250+ | Machine learning |

#### Advanced Limit Detection

- **P90 Analysis**: Uses 90th percentile of your historical usage
- **Confidence Threshold**: 95% accuracy in limit detection
- **Cache Support**: Includes cache creation and read token costs
- **Model-Specific**: Adapts to Claude 3.5, Claude 4, and future models

### Technical Requirements

#### Dependencies (v3.0.0)

```toml
# Core dependencies (automatically installed)
pytz>=2023.3                # Timezone handling
rich>=13.7.0                # Rich terminal UI
pydantic>=2.0.0             # Type validation
pydantic-settings>=2.0.0    # Configuration management
numpy>=1.21.0               # Statistical calculations
sentry-sdk>=1.40.0          # Error reporting (optional)
pyyaml>=6.0                 # Configuration files
tzdata                      # Windows timezone data
```

#### Python Requirements

- **Minimum**: Python 3.9+
- **Recommended**: Python 3.11+
- **Tested on**: Python 3.9, 3.10, 3.11, 3.12, 3.13

### Smart Detection Features

#### Automatic Plan Switching

When using the default Pro plan:

1. **Detection**: Monitor notices token usage exceeding 7,000
2. **Analysis**: Scans previous sessions for actual limits
3. **Switch**: Automatically changes to custom_max mode
4. **Notification**: Displays clear message about the change
5. **Continuation**: Keeps monitoring with new, higher limit

#### Limit Discovery Process

The auto-detection system:

1. **Scans History**: Examines all available session blocks
2. **Finds Peaks**: Identifies highest token usage achieved
3. **Validates Data**: Ensures data quality and recency
4. **Sets Limits**: Uses discovered maximum as new limit
5. **Learns Patterns**: Adapts to your actual usage capabilities


## 🚀 Usage Examples

### Common Scenarios

#### 🌅 Morning Developer
**Scenario**: You start work at 9 AM and want tokens to reset aligned with your schedule.

```bash
# Set custom reset time to 9 AM
./claude_monitor.py --reset-hour 9

# With your timezone
./claude_monitor.py --reset-hour 9 --timezone US/Eastern
```

**Benefits**:
- Reset times align with your work schedule
- Better planning for daily token allocation
- Predictable session windows

#### 🌙 Night Owl Coder
**Scenario**: You often work past midnight and need flexible reset scheduling.

```bash
# Reset at midnight for clean daily boundaries
./claude_monitor.py --reset-hour 0

# Late evening reset (11 PM)
./claude_monitor.py --reset-hour 23
```

**Strategy**:
- Plan heavy coding sessions around reset times
- Use late resets to span midnight work sessions
- Monitor burn rate during peak hours

#### 🔄 Heavy User with Variable Limits
**Scenario**: Your token limits seem to change, and you're not sure of your exact plan.

```bash
# Auto-detect your highest previous usage
claude-monitor --plan custom_max

# Monitor with custom scheduling
claude-monitor --plan custom_max --reset-hour 6
```

**Approach**:
- Let auto-detection find your real limits
- Monitor for a week to understand patterns
- Note when limits change or reset

#### 🌍 International User
**Scenario**: You're working across different timezones or traveling.

```bash
# US East Coast
claude-monitor --timezone America/New_York

# Europe
claude-monitor --timezone Europe/London

# Asia Pacific
claude-monitor --timezone Asia/Singapore

# UTC for international team coordination
claude-monitor --timezone UTC --reset-hour 12
```

#### ⚡ Quick Check
**Scenario**: You just want to see current status without configuration.

```bash
# Just run it with defaults
claude-monitor

# Press Ctrl+C after checking status
```

### Plan Selection Strategies

#### How to Choose Your Plan

**Start with Default (Recommended for New Users)**
```bash
# Pro plan detection with auto-switching
claude-monitor
```
- Monitor will detect if you exceed Pro limits
- Automatically switches to custom_max if needed
- Shows notification when switching occurs

**Known Subscription Users**
```bash
# If you know you have Max5
claude-monitor --plan max5

# If you know you have Max20
claude-monitor --plan max20
```

**Unknown Limits**
```bash
# Auto-detect from previous usage
claude-monitor --plan custom_max
```

### Best Practices

#### Setup Best Practices

1. **Start Early in Sessions**
   ```bash
   # Begin monitoring when starting Claude work (uv installation)
   claude-monitor

   # Or development mode
   ./claude_monitor.py
   ```
   - Gives accurate session tracking from the start
   - Better burn rate calculations
   - Early warning for limit approaches

2. **Use Modern Installation (Recommended)**
   ```bash
   # Easy installation and updates with uv
   uv tool install claude-monitor
   claude-monitor --plan max5
   ```
   - Clean system installation
   - Easy updates and maintenance
   - Available from anywhere

3. **Custom Shell Alias (Legacy Setup)**
   ```bash
   # Add to ~/.bashrc or ~/.zshrc (only for development setup)
   alias claude-monitor='cd ~/Claude-Code-Usage-Monitor && source venv/bin/activate && ./claude_monitor.py'
   ```

#### Usage Best Practices

1. **Monitor Burn Rate Velocity**
   - Watch for sudden spikes in token consumption
   - Adjust coding intensity based on remaining time
   - Plan big refactors around session resets

2. **Strategic Session Planning**
   ```bash
   # Plan heavy usage around reset times
   claude-monitor --reset-hour 9
   ```
   - Schedule large tasks after resets
   - Use lighter tasks when approaching limits
   - Leverage multiple overlapping sessions

3. **Timezone Awareness**
   ```bash
   # Always use your actual timezone
   claude-monitor --timezone Europe/Warsaw
   ```
   - Accurate reset time predictions
   - Better planning for work schedules
   - Correct session expiration estimates

#### Optimization Tips

1. **Terminal Setup**
   - Use terminals with at least 80 character width
   - Enable color support for better visual feedback (check `COLORTERM` environment variable)
   - Consider dedicated terminal window for monitoring
   - Use terminals with truecolor support for best theme experience

2. **Workflow Integration**
   ```bash
   # Start monitoring with your development session (uv installation)
   tmux new-session -d -s claude-monitor 'claude-monitor'

   # Or development mode
   tmux new-session -d -s claude-monitor './claude_monitor.py'

   # Check status anytime
   tmux attach -t claude-monitor
   ```

3. **Multi-Session Strategy**
   - Remember sessions last exactly 5 hours
   - You can have multiple overlapping sessions
   - Plan work across session boundaries

#### Real-World Workflows

**Large Project Development**
```bash
# Setup for sustained development
claude-monitor --plan max20 --reset-hour 8 --timezone America/New_York
```

**Daily Routine**:
1. **8:00 AM**: Fresh tokens, start major features
2. **10:00 AM**: Check burn rate, adjust intensity
3. **12:00 PM**: Monitor for afternoon session planning
4. **2:00 PM**: New session window, tackle complex problems
5. **4:00 PM**: Light tasks, prepare for evening session

**Learning & Experimentation**
```bash
# Flexible setup for learning
claude-monitor --plan pro
```

**Sprint Development**
```bash
# High-intensity development setup
claude-monitor --plan max20 --reset-hour 6
```

## 🔧 Development Installation

For contributors and developers who want to work with the source code:

### Quick Start (Development/Testing)

```bash
# Clone the repository
git clone https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor.git
cd Claude-Code-Usage-Monitor

# Install in development mode
pip install -e .

# Run from source
python -m claude_monitor
```

### v3.0.0 Testing Features

The new version includes a comprehensive test suite:

- **100+ test cases** with full coverage
- **Unit tests** for all components
- **Integration tests** for end-to-end workflows
- **Performance tests** with benchmarking
- **Mock objects** for isolated testing

```bash
# Run tests
cd src/
python -m pytest

# Run with coverage
python -m pytest --cov=claude_monitor --cov-report=html

# Run specific test modules
python -m pytest tests/test_analysis.py -v
```

### Prerequisites

1. **Python 3.9+** installed on your system
2. **Git** for cloning the repository


### Virtual Environment Setup

#### Why Use Virtual Environment?

Using a virtual environment is **strongly recommended** because:

- **🛡️ Isolation**: Keeps your system Python clean and prevents dependency conflicts
- **📦 Portability**: Easy to replicate the exact environment on different machines
- **🔄 Version Control**: Lock specific versions of dependencies for stability
- **🧹 Clean Uninstall**: Simply delete the virtual environment folder to remove everything
- **👥 Team Collaboration**: Everyone uses the same Python and package versions

#### Installing virtualenv (if needed)

If you don't have `venv` module available:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3-venv

# Fedora/RHEL/CentOS
sudo dnf install python3-venv

# macOS (usually comes with Python)
# If not available, install Python via Homebrew:
brew install python3

# Windows (usually comes with Python)
# If not available, reinstall Python from python.org
# Make sure to check "Add Python to PATH" during installation
```

Alternatively, use the `virtualenv` package:
```bash
# Install virtualenv via pip
pip install virtualenv

# Then create virtual environment with:
virtualenv venv
# instead of: python3 -m venv venv
```

#### Step-by-Step Setup

```bash
# 1. Clone the repository
git clone https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor.git
cd Claude-Code-Usage-Monitor

# 2. Create virtual environment
python3 -m venv venv
# Or if using virtualenv package:
# virtualenv venv

# 3. Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# 4. Install Python dependencies
pip install pytz
pip install rich>=13.0.0
# 5. Make script executable (Linux/Mac only)
chmod +x claude_monitor.py

# 6. Run the monitor
python claude_monitor.py
```

#### Daily Usage

After initial setup, you only need:

```bash
# Navigate to project directory
cd Claude-Code-Usage-Monitor

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Run monitor
./claude_monitor.py  # Linux/Mac
# python claude_monitor.py  # Windows

# When done, deactivate
deactivate
```

#### Pro Tip: Shell Alias

Create an alias for quick access:
```bash
# Add to ~/.bashrc or ~/.zshrc
alias claude-monitor='cd ~/Claude-Code-Usage-Monitor && source venv/bin/activate && ./claude_monitor.py'

# Then just run:
claude-monitor
```

## Troubleshooting

### Installation Issues

#### "externally-managed-environment" Error

On modern Linux distributions (Ubuntu 23.04+, Debian 12+, Fedora 38+), you may encounter:
```
error: externally-managed-environment
× This environment is externally managed
```

**Solutions (in order of preference):**

1. **Use uv (Recommended)**
   ```bash
   # Install uv first
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Then install with uv
   uv tool install claude-monitor
   ```

2. **Use pipx (Isolated Environment)**
   ```bash
   # Install pipx
   sudo apt install pipx  # Ubuntu/Debian
   # or
   python3 -m pip install --user pipx

   # Install claude-monitor
   pipx install claude-monitor
   ```

3. **Use virtual environment**
   ```bash
   python3 -m venv myenv
   source myenv/bin/activate
   pip install claude-monitor
   ```

4. **Force installation (Not Recommended)**
   ```bash
   pip install --user claude-monitor --break-system-packages
   ```
   ⚠️ **Warning**: This bypasses system protection and may cause conflicts. We strongly recommend using a virtual environment instead.

#### Command Not Found After pip Install

If `claude-monitor` command is not found after pip installation:

1. **Check if it's a PATH issue**
   ```bash
   # Look for the warning message during pip install:
   # WARNING: The script claude-monitor is installed in '/home/username/.local/bin' which is not on PATH
   ```

2. **Add to PATH**
   ```bash
   # Add this to ~/.bashrc or ~/.zshrc
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

   # Reload shell
   source ~/.bashrc  # or source ~/.zshrc
   ```

3. **Verify installation location**
   ```bash
   # Find where pip installed the script
   pip show -f claude-monitor | grep claude-monitor
   ```

4. **Run directly with Python**
   ```bash
   python3 -m claude_monitor
   ```

#### Python Version Conflicts

If you have multiple Python versions:

1. **Check Python version**
   ```bash
   python3 --version
   pip3 --version
   ```

2. **Use specific Python version**
   ```bash
   python3.11 -m pip install claude-monitor
   python3.11 -m claude_monitor
   ```

3. **Use uv (handles Python versions automatically)**
   ```bash
   uv tool install claude-monitor
   ```

### Runtime Issues

#### No active session found
If you encounter the error `No active session found`, please follow these steps:

1. **Initial Test**:
   Launch Claude Code and send at least two messages. In some cases, the session may not initialize correctly on the first attempt, but it resolves after a few interactions.

2. **Configuration Path**:
   If the issue persists, consider specifying a custom configuration path. By default, Claude Code uses `~/.config/claude`. You may need to adjust this path depending on your environment.

```bash
CLAUDE_CONFIG_DIR=~/.config/claude ./claude_monitor.py
```


## 📞 Contact

Have questions, suggestions, or want to collaborate? Feel free to reach out!

**📧 Email**: [maciek@roboblog.eu](mailto:maciek@roboblog.eu)

Whether you need help with setup, have feature requests, found a bug, or want to discuss potential improvements, don't hesitate to get in touch. I'm always happy to help and hear from users of the Claude Code Usage Monitor!


## 📚 Additional Documentation

- **[Development Roadmap](DEVELOPMENT.md)** - ML features, PyPI package, Docker plans
- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute, development guidelines
- **[Troubleshooting](TROUBLESHOOTING.md)** - Common issues and solutions


## 📝 License

[MIT License](LICENSE) - feel free to use and modify as needed.

## 🤝 Contributors

- [@adawalli](https://github.com/adawalli)
- [@taylorwilsdon](https://github.com/taylorwilsdon)
- [@moneroexamples](https://github.com/moneroexamples)

Want to contribute? Check out our [Contributing Guide](CONTRIBUTING.md)!


## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Maciek-roboblog/Claude-Code-Usage-Monitor&type=Date)](https://www.star-history.com/#Maciek-roboblog/Claude-Code-Usage-Monitor&Date)

---

<div align="center">

**⭐ Star this repo if you find it useful! ⭐**

[Report Bug](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/issues) • [Request Feature](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/issues) • [Contribute](CONTRIBUTING.md)

</div>
