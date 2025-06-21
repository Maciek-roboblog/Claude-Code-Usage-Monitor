# 🎯 Claude Code Usage Monitor

[![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

A beautiful real-time terminal monitoring tool for Claude AI token usage. Track your token consumption, burn rate, and get predictions about when you'll run out of tokens.

![Claude Token Monitor Screenshot](doc/sc.png)

---

## 📑 Table of Contents

- [✨ Key Features](#-key-features)
- [🚀 Installation](#-installation)
  - [⚡ Quick Start](#-quick-start)
  - [🔒 Production Setup (Recommended)](#-production-setup-recommended)
  - [Virtual Environment Setup](#virtual-environment-setup)
- [📖 Usage](#-usage)
  - [Basic Usage](#basic-usage)
  - [Configuration Options](#configuration-options)
  - [Available Plans](#available-plans)
- [✨ Features & How It Works](#-features--how-it-works)
  - [Current Features](#current-features)
  - [Understanding Claude Sessions](#understanding-claude-sessions)
  - [Token Limits by Plan](#token-limits-by-plan)
  - [Smart Detection Features](#smart-detection-features)
- [🚀 Usage Examples](#-usage-examples)
  - [Common Scenarios](#common-scenarios)
  - [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
  - [No active session found](#no-active-session-found)
- [📞 Contact](#-contact)
- [📚 Additional Documentation](#-additional-documentation)

---

## ✨ Key Features

- **🔄 Real-time monitoring** - Updates every 3 seconds with smooth refresh
- **📊 Visual progress bars** - Beautiful color-coded token and time progress bars
- **🔮 Smart predictions** - Calculates when tokens will run out based on current burn rate
- **🤖 Auto-detection** - Automatically switches to custom max when Pro limit is exceeded
- **📋 Multiple plan support** - Works with Pro, Max5, Max20, and auto-detect plans
- **⚠️ Warning system** - Alerts when tokens exceed limits or will deplete before session reset
- **💼 Professional UI** - Clean, colorful terminal interface with emojis
- **⏰ Customizable scheduling** - Set your own reset times and timezones

---

## 🚀 Installation

### ⚡ Quick Start

For immediate testing (not recommended for regular use):

```bash
# Install dependencies
npm install -g ccusage
pip install pytz

# Clone and run
git clone https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor.git
cd Claude-Code-Usage-Monitor
python ccusage_monitor.py
```

### 🔒 Production Setup (Recommended)

#### Prerequisites

1. **Python 3.6+** installed on your system
2. **Node.js** for ccusage CLI tool

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
# 1. Install ccusage globally
npm install -g ccusage

# 2. Clone the repository
git clone https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor.git
cd Claude-Code-Usage-Monitor

# 3. Create virtual environment
python3 -m venv venv
# Or if using virtualenv package:
# virtualenv venv

# 4. Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# 5. Install Python dependencies
pip install pytz

# 6. Make script executable (Linux/Mac only)
chmod +x ccusage_monitor.py

# 7. Run the monitor
python ccusage_monitor.py
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
./ccusage_monitor.py  # Linux/Mac
# python ccusage_monitor.py  # Windows

# When done, deactivate
deactivate
```

#### Pro Tip: Shell Alias

Create an alias for quick access:
```bash
# Add to ~/.bashrc or ~/.zshrc
alias claude-monitor='cd ~/Claude-Code-Usage-Monitor && source venv/bin/activate && ./ccusage_monitor.py'

# Then just run:
claude-monitor
```

---

## 📖 Usage

### Basic Usage

```bash
# Default (Pro plan - 7,000 tokens)
./ccusage_monitor.py

# Exit the monitor
# Press Ctrl+C to gracefully exit
```

### Configuration Options

#### Specify Your Plan

```bash
# Pro plan (~7,000 tokens) - Default
./ccusage_monitor.py --plan pro

# Max5 plan (~35,000 tokens)
./ccusage_monitor.py --plan max5

# Max20 plan (~140,000 tokens)
./ccusage_monitor.py --plan max20

# Auto-detect from highest previous session
./ccusage_monitor.py --plan custom_max
```

#### Custom Reset Times

```bash
# Reset at 3 AM
./ccusage_monitor.py --reset-hour 3

# Reset at 10 PM
./ccusage_monitor.py --reset-hour 22
```

#### Timezone Configuration

The default timezone is **Europe/Warsaw**. Change it to any valid timezone:

```bash
# Use US Eastern Time
./ccusage_monitor.py --timezone US/Eastern

# Use Tokyo time
./ccusage_monitor.py --timezone Asia/Tokyo

# Use UTC
./ccusage_monitor.py --timezone UTC

# Use London time
./ccusage_monitor.py --timezone Europe/London
```

### Available Plans

| Plan | Token Limit | Best For |
|------|-------------|----------|
| **pro** | ~7,000 | Light usage, testing (default) |
| **max5** | ~35,000 | Regular development |
| **max20** | ~140,000 | Heavy usage, large projects |
| **custom_max** | Auto-detect | Uses highest from previous sessions |

---

## ✨ Features & How It Works

### Current Features

#### 🔄 Real-time Monitoring
- Updates every 3 seconds with smooth refresh
- No screen flicker - intelligent display updates
- Live token consumption tracking across multiple sessions

#### 📊 Visual Progress Bars
- **Token Progress**: Color-coded bars showing current usage vs limits
- **Time Progress**: Visual countdown to next session reset
- **Burn Rate Indicator**: Real-time consumption velocity

#### 🔮 Smart Predictions
- Calculates when tokens will run out based on current burn rate
- Warns if tokens will deplete before next session reset
- Analyzes usage patterns from the last hour

#### 🤖 Auto-Detection System
- **Smart Plan Switching**: Automatically switches from Pro to custom_max when limits exceeded
- **Limit Discovery**: Scans previous sessions to find your actual token limits
- **Intelligent Notifications**: Shows when automatic switches occur

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

#### Standard Plans

| Plan | Approximate Limit | Typical Usage |
|------|------------------|---------------|
| **Claude Pro** | ~7,000 tokens | Light coding, testing, learning |
| **Claude Max5** | ~35,000 tokens | Regular development work |
| **Claude Max20** | ~140,000 tokens | Heavy usage, large projects |

#### Auto-Detection Plans

| Plan | How It Works | Best For |
|------|-------------|----------|
| **custom_max** | Scans all previous sessions, uses highest token count found | Users with variable/unknown limits |

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

---

## 🚀 Usage Examples

### Common Scenarios

#### 🌅 Morning Developer
**Scenario**: You start work at 9 AM and want tokens to reset aligned with your schedule.

```bash
# Set custom reset time to 9 AM
./ccusage_monitor.py --reset-hour 9

# With your timezone
./ccusage_monitor.py --reset-hour 9 --timezone US/Eastern
```

**Benefits**:
- Reset times align with your work schedule
- Better planning for daily token allocation
- Predictable session windows

#### 🌙 Night Owl Coder
**Scenario**: You often work past midnight and need flexible reset scheduling.

```bash
# Reset at midnight for clean daily boundaries
./ccusage_monitor.py --reset-hour 0

# Late evening reset (11 PM)
./ccusage_monitor.py --reset-hour 23
```

**Strategy**:
- Plan heavy coding sessions around reset times
- Use late resets to span midnight work sessions
- Monitor burn rate during peak hours

#### 🔄 Heavy User with Variable Limits
**Scenario**: Your token limits seem to change, and you're not sure of your exact plan.

```bash
# Auto-detect your highest previous usage
./ccusage_monitor.py --plan custom_max

# Monitor with custom scheduling
./ccusage_monitor.py --plan custom_max --reset-hour 6
```

**Approach**:
- Let auto-detection find your real limits
- Monitor for a week to understand patterns
- Note when limits change or reset

#### 🌍 International User
**Scenario**: You're working across different timezones or traveling.

```bash
# US East Coast
./ccusage_monitor.py --timezone America/New_York

# Europe
./ccusage_monitor.py --timezone Europe/London

# Asia Pacific
./ccusage_monitor.py --timezone Asia/Singapore

# UTC for international team coordination
./ccusage_monitor.py --timezone UTC --reset-hour 12
```

#### ⚡ Quick Check
**Scenario**: You just want to see current status without configuration.

```bash
# Just run it with defaults
./ccusage_monitor.py

# Press Ctrl+C after checking status
```

### Plan Selection Strategies

#### How to Choose Your Plan

**Start with Default (Recommended for New Users)**
```bash
# Pro plan detection with auto-switching
./ccusage_monitor.py
```
- Monitor will detect if you exceed Pro limits
- Automatically switches to custom_max if needed
- Shows notification when switching occurs

**Known Subscription Users**
```bash
# If you know you have Max5
./ccusage_monitor.py --plan max5

# If you know you have Max20
./ccusage_monitor.py --plan max20
```

**Unknown Limits**
```bash
# Auto-detect from previous usage
./ccusage_monitor.py --plan custom_max
```

### Best Practices

#### Setup Best Practices

1. **Start Early in Sessions**
   ```bash
   # Begin monitoring when starting Claude work
   ./ccusage_monitor.py
   ```
   - Gives accurate session tracking from the start
   - Better burn rate calculations
   - Early warning for limit approaches

2. **Use Virtual Environment**
   ```bash
   # Production setup with isolation
   python3 -m venv venv
   source venv/bin/activate
   pip install pytz
   ```
   - Prevents dependency conflicts
   - Clean uninstallation
   - Reproducible environments

3. **Custom Shell Alias**
   ```bash
   # Add to ~/.bashrc or ~/.zshrc
   alias claude-monitor='cd ~/Claude-Code-Usage-Monitor && source venv/bin/activate && ./ccusage_monitor.py'
   ```

#### Usage Best Practices

1. **Monitor Burn Rate Velocity**
   - Watch for sudden spikes in token consumption
   - Adjust coding intensity based on remaining time
   - Plan big refactors around session resets

2. **Strategic Session Planning**
   ```bash
   # Plan heavy usage around reset times
   ./ccusage_monitor.py --reset-hour 9
   ```
   - Schedule large tasks after resets
   - Use lighter tasks when approaching limits
   - Leverage multiple overlapping sessions

3. **Timezone Awareness**
   ```bash
   # Always use your actual timezone
   ./ccusage_monitor.py --timezone Europe/Warsaw
   ```
   - Accurate reset time predictions
   - Better planning for work schedules
   - Correct session expiration estimates

#### Optimization Tips

1. **Terminal Setup**
   - Use terminals with at least 80 character width
   - Enable color support for better visual feedback
   - Consider dedicated terminal window for monitoring

2. **Workflow Integration**
   ```bash
   # Start monitoring with your development session
   tmux new-session -d -s claude-monitor './ccusage_monitor.py'
   
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
./ccusage_monitor.py --plan max20 --reset-hour 8 --timezone America/New_York
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
./ccusage_monitor.py --plan pro
```

**Sprint Development**
```bash
# High-intensity development setup
./ccusage_monitor.py --plan max20 --reset-hour 6
```

## Troubleshooting

### No active session found
If you encounter the error `No active session found`, please follow these steps:

1. **Initial Test**:
   Launch Claude Code and send at least two messages. In some cases, the session may not initialize correctly on the first attempt, but it resolves after a few interactions.

2. **Configuration Path**:
   If the issue persists, consider specifying a custom configuration path. By default, Claude Code uses `~/.config/claude`. You may need to adjust this path depending on your environment.

```bash
CLAUDE_CONFIG_DIR=~/.config/claude ./ccusage_monitor.py
```
---

## 📞 Contact

Have questions, suggestions, or want to collaborate? Feel free to reach out!

**📧 Email**: [maciek@roboblog.eu](mailto:maciek@roboblog.eu)

Whether you need help with setup, have feature requests, found a bug, or want to discuss potential improvements, don't hesitate to get in touch. I'm always happy to help and hear from users of the Claude Code Usage Monitor!

---

## 📚 Additional Documentation

- **[Development Roadmap](DEVELOPMENT.md)** - ML features, PyPI package, Docker plans
- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute, development guidelines
- **[Troubleshooting](TROUBLESHOOTING.md)** - Common issues and solutions

---

## 📝 License

[MIT License](LICENSE) - feel free to use and modify as needed.

---

## 🙏 Acknowledgments

This tool builds upon the excellent [ccusage](https://github.com/ryoppippi/ccusage) by [@ryoppippi](https://github.com/ryoppippi), adding a real-time monitoring interface with visual progress bars, burn rate calculations, and predictive analytics.

---

<div align="center">

**⭐ Star this repo if you find it useful! ⭐**

[Report Bug](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/issues) • [Request Feature](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/issues) • [Contribute](CONTRIBUTING.md)

</div>

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Maciek-roboblog/Claude-Code-Usage-Monitor&type=Date)](https://www.star-history.com/#Maciek-roboblog/Claude-Code-Usage-Monitor&Date)
