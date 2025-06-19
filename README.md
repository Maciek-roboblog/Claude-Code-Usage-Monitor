# 🎯 Claude Code Usage Monitor

[![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

A beautiful real-time terminal monitoring tool for Claude AI token usage. Track your token consumption, burn rate, and get predictions about when you'll run out of tokens.

![Claude Token Monitor Screenshot](doc/sc.png)

---

## 📑 Table of Contents

- [✨ Features](#-features)
- [🚀 Installation](#-installation)
  - [🔒 Production Setup (Recommended - with virtualenv)](#-production-setup-recommended---with-virtualenv)
    - [Why Use Virtual Environment?](#why-use-virtual-environment)
    - [Step-by-Step Setup](#step-by-step-setup)
    - [Daily Usage](#daily-usage)
  - [⚡ Quick Setup (without virtualenv)](#-quick-setup-without-virtualenv)
- [📖 Usage](#-usage)
  - [Basic Usage](#basic-usage)
  - [Specify Your Plan](#specify-your-plan)
  - [Custom Reset Times](#custom-reset-times)
  - [Timezone Configuration](#timezone-configuration)
  - [Exit the Monitor](#exit-the-monitor)
- [📊 Understanding Claude Sessions](#-understanding-claude-sessions)
  - [How Sessions Work](#how-sessions-work)
  - [Token Reset Schedule](#token-reset-schedule)
  - [Burn Rate Calculation](#burn-rate-calculation)
- [🛠️ Token Limits by Plan](#️-token-limits-by-plan)
- [🔧 Advanced Features](#-advanced-features)
  - [🧠 ML-Powered Auto Mode (Currently in Development!)](#-ml-powered-auto-mode-currently-in-development)
  - [Auto-Detection Mode (Current)](#auto-detection-mode-current)
  - [Smart Pro Plan Switching](#smart-pro-plan-switching)
- [⚡ Best Practices](#-best-practices)
- [🐛 Troubleshooting](#-troubleshooting)
- [🚀 Example Usage Scenarios](#-example-usage-scenarios)
- [🤝 Contributing](#-contributing)
  - [How to Contribute](#how-to-contribute)
  - [Development Guidelines](#development-guidelines)
  - [Help Us Improve Token Limit Detection](#help-us-improve-token-limit-detection)
- [📝 License](#-license)
- [🙏 Acknowledgments](#-acknowledgments)

---

## ✨ Features

- **🔄 Real-time monitoring** - Updates every 3 seconds with smooth refresh
- **📊 Visual progress bars** - Beautiful color-coded token and time progress bars
- **🔮 Smart predictions** - Calculates when tokens will run out based on current burn rate
- **🤖 Auto-detection** - Automatically switches to custom max when Pro limit is exceeded
- **🧠 ML-Powered Auto Mode** *(In Development)* - Will use machine learning with DuckDB to learn your actual token limits
- **📋 Multiple plan support** - Works with Pro, Max5, Max20, and auto-detect plans
- **⚠️ Warning system** - Alerts when tokens exceed limits or will deplete before session reset
- **💼 Professional UI** - Clean, colorful terminal interface with emojis
- **✨ No screen flicker** - Smooth updates without clearing the entire screen
- **⏰ Customizable reset times** - Set your own token reset schedule

---

## 🚀 Installation

### 🔒 Production Setup (Recommended - with virtualenv)

#### Why Use Virtual Environment?

Using a virtual environment is the **recommended approach** for production use because:

- **🛡️ Isolation**: Keeps your system Python clean and prevents dependency conflicts
- **📦 Portability**: Easy to replicate the exact environment on different machines
- **🔄 Version Control**: Lock specific versions of dependencies for stability
- **🧹 Clean Uninstall**: Simply delete the virtual environment folder to remove everything
- **👥 Team Collaboration**: Everyone uses the same Python and package versions

#### Installing virtualenv (if not available)

If you don't have `venv` module available, install it first:

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

Alternatively, you can use the `virtualenv` package:
```bash
# Install virtualenv via pip
pip install virtualenv

# Then create virtual environment with:
virtualenv venv
# instead of: python3 -m venv venv
```

📚 **Learn More**: For detailed virtualenv documentation, visit [Python Virtual Environments Guide](https://docs.python.org/3/tutorial/venv.html)

#### Step-by-Step Setup

```bash
# 1. Prerequisites: Install Node.js and ccusage globally
npm install -g ccusage

# 2. Clone the repository
git clone https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor.git
cd Claude-Code-Usage-Monitor

# 3. Create a virtual environment
python3 -m venv venv
# Or if using virtualenv package:
# virtualenv venv

# 4. Activate the virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# 5. Install Python dependencies
pip install pytz

# Note: Future ML features will require:
# pip install duckdb pandas scikit-learn
# (Not needed for current version)

# 6. Make the script executable (Linux/Mac only)
chmod +x ccusage_monitor.py

# 7. Run the monitor
python ccusage_monitor.py
```

#### Daily Usage

After initial setup, you only need:

```bash
# Navigate to the project directory
cd Claude-Code-Usage-Monitor

# Activate the virtual environment
source venv/bin/activate  # Linux/Mac
# or
# venv\Scripts\activate   # Windows

# Run the monitor
./ccusage_monitor.py  # Linux/Mac
# or
python ccusage_monitor.py  # Windows

# When done, deactivate the virtual environment
deactivate
```

💡 **Pro Tip**: Create an alias in your shell configuration for quick access:
```bash
# Add to ~/.bashrc or ~/.zshrc
alias claude-monitor='cd ~/Claude-Code-Usage-Monitor && source venv/bin/activate && ./ccusage_monitor.py'
```

---

### ⚡ Quick Setup (without virtualenv)

For quick testing or if you prefer system-wide installation:

1. **Python 3.6+** installed on your system
2. **Required Python packages**:
   ```bash
   pip install pytz
   ```
3. **ccusage** CLI tool installed globally:
   ```bash
   npm install -g ccusage
   ```

```bash
# Clone and run
git clone https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor.git
cd Claude-Code-Usage-Monitor
chmod +x ccusage_monitor.py
./ccusage_monitor.py
```

⚠️ **Note**: This method may cause conflicts with other Python projects on your system.

---

## 📖 Usage

### Basic Usage

Run with default settings (Pro plan - 7,000 tokens):

```bash
./ccusage_monitor.py
```

> **💡 Smart Detection**: When tokens exceed the Pro limit, the monitor automatically switches to custom_max mode and displays a notification.

> **🚀 Coming Soon**: ML-powered auto mode will intelligently learn your actual token limits. Stay tuned!

### Specify Your Plan

```bash
# Pro plan (~7,000 tokens) - Default
./ccusage_monitor.py --plan pro

# Max5 plan (~35,000 tokens)
./ccusage_monitor.py --plan max5

# Max20 plan (~140,000 tokens)
./ccusage_monitor.py --plan max20

# Auto-detect from highest previous session
./ccusage_monitor.py --plan custom_max

# Coming Soon: ML Auto Mode (--plan ml_auto)
# Will learn your actual limits using machine learning!
```

### Custom Reset Times

Set a custom daily reset hour (0-23):

```bash
# Reset at 3 AM
./ccusage_monitor.py --reset-hour 3

# Reset at 10 PM
./ccusage_monitor.py --reset-hour 22
```

### Timezone Configuration

The default timezone is **Europe/Warsaw**. You can change it to any valid timezone:

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

### Exit the Monitor

Press `Ctrl+C` to gracefully exit the monitoring tool.

---

## 📊 Understanding Claude Sessions

### How Sessions Work

Claude Code operates on a **5-hour rolling session window system**:

- **Sessions start** with your first message to Claude
- **Sessions last** for exactly 5 hours from that first message
- **Token limits** apply within each 5-hour session window
- **Multiple sessions** can be active simultaneously

### Token Reset Schedule

**Default reset times** (in your configured timezone, default: Europe/Warsaw):
- `04:00`, `09:00`, `14:00`, `18:00`, `23:00`

> **⚠️ Important**: These are reference times. Your actual token refresh happens 5 hours after YOUR first message in each session.

> **🌍 Timezone Note**: The default timezone is Europe/Warsaw. You can change it using the `--timezone` parameter with any valid timezone name.

### Burn Rate Calculation

The monitor calculates burn rate based on all sessions from the last hour:

- Analyzes token consumption across overlapping sessions
- Provides accurate recent usage patterns
- Updates predictions in real-time

---

## 🛠️ Token Limits by Plan

| Plan | Token Limit | Best For |
|------|-------------|----------|
| **Pro** | ~7,000 | Light usage, testing (default) |
| **Max5** | ~35,000 | Regular development |
| **Max20** | ~140,000 | Heavy usage, large projects |
| **Custom Max** | Auto-detect | Automatically uses highest from previous sessions |
| **ML Auto** | *(Coming Soon!)* | 🧠 Will learn your actual limits using ML |

---

## 🔧 Advanced Features

### 🧠 ML-Powered Auto Mode (Currently in Development!)

The **intelligent Auto Mode** with machine learning is now implemented and actively learns your actual token limits:

#### How It Works:

1. **📊 Data Collection**: 
   - Monitors and stores your token usage patterns in a local DuckDB database
   - Tracks session starts, token consumption rates, and limit boundaries
   - Builds a comprehensive dataset of YOUR specific usage patterns

2. **🤖 Machine Learning Pipeline**:
   - **Pattern Recognition**: Identifies recurring usage patterns and peak times
   - **Anomaly Detection**: Spots when your token allocation changes
   - **Regression Models**: Predicts future token consumption based on historical data
   - **Classification**: Automatically categorizes your usage tier (Pro/Max5/Max20/Custom)

3. **💾 DuckDB Integration**:
   - Lightweight, embedded analytical database
   - No external server required - all data stays local
   - Efficient SQL queries for real-time analysis
   - Automatic data optimization and compression

4. **🎯 Dynamic Adaptation**:
   - Learns your actual limits, not predefined ones
   - Adapts when Claude changes your allocation
   - Improves predictions with each session
   - No manual plan selection needed

#### Technical Implementation:

```python
# The system uses several ML algorithms:
- Time Series Analysis (ARIMA) for trend prediction
- Random Forest for limit classification
- Linear Regression for burn rate calculation
- K-means clustering for usage pattern grouping
```

#### Benefits Over Static Limits:

| Static Approach | ML-Powered Approach |
|----------------|---------------------|
| Fixed 7K, 35K, 140K limits | Learns YOUR actual limits |
| Manual plan selection | Automatic detection |
| Basic linear predictions | Advanced ML predictions |
| No historical learning | Improves over time |
| Can't adapt to changes | Dynamic adaptation |

#### Data Privacy & Security:

- **🔒 100% Local**: All ML processing happens on your machine
- **🚫 No Cloud**: Your usage data never leaves your computer
- **💾 Local Database**: DuckDB stores data in `~/.claude_monitor/usage.db`
- **🗑️ Easy Cleanup**: Delete the database file to reset ML learning
- **🔐 Your Data, Your Control**: No telemetry, no tracking, no sharing

#### Recommended Future Enhancements:

While the core ML functionality is implemented, contributors can extend it with:

- **📈 Advanced Visualizations**: Real-time ML prediction graphs
- **🔔 Smart Alerts**: ML-based anomaly notifications
- **📊 Weekly/Monthly Reports**: AI-generated usage insights
- **🌐 Multi-user Learning**: Anonymous pattern sharing (opt-in)
- **🎨 Neural Network Models**: Deep learning for complex patterns
- **📱 Mobile Dashboard**: View ML insights on the go

### Auto-Detection Mode (Current)

The original auto-detection still works alongside ML mode:

1. 🔍 Scans all previous session blocks
2. 📈 Finds the highest token count used
3. ⚙️ Sets that as your limit automatically
4. ✅ Perfect for users who prefer simple detection

### Smart Pro Plan Switching

When using the default Pro plan:

- 🔍 Monitor detects when usage exceeds 7,000 tokens
- 🔄 Automatically switches to custom_max mode
- 📢 Shows notification of the switch
- ▶️ Continues monitoring with the new limit
- 🧠 Future: Will switch to ML-powered mode for intelligent predictions

---

## ⚡ Best Practices

1. **🚀 Start Early**: Begin monitoring when you start a new session
2. **👀 Watch Velocity**: Monitor burn rate indicators to manage usage
3. **📅 Plan Ahead**: If tokens will deplete before reset, adjust your usage
4. **⏰ Custom Schedule**: Set `--reset-hour` to match your typical work schedule
5. **🤖 Use Auto-Detect**: Let the monitor figure out your limits with `--plan custom_max`
6. **🧠 Stay Tuned**: ML-powered mode coming soon for even better predictions!

---

## 🐛 Troubleshooting

### "Failed to get usage data"

- Ensure `ccusage` is installed: `npm install -g ccusage`
- Check if you have an active Claude session
- Verify `ccusage` works: `ccusage blocks --json`

### "No active session found"

- Start a new Claude Code session
- The monitor only works when there's an active session

### Cursor remains hidden after exit

```bash
printf '\033[?25h'
```

### Display issues or overlapping text

- Ensure your terminal window is at least 80 characters wide
- Try resizing your terminal and restarting the monitor

---

## 🚀 Example Usage Scenarios

### Morning Developer
```bash
# Start work at 9 AM daily
./ccusage_monitor.py --reset-hour 9
```

### Night Owl Coder
```bash
# Often work past midnight
./ccusage_monitor.py --reset-hour 0
```

### Heavy User with Variable Limits
```bash
# Use auto-detect to find your highest previous usage
./ccusage_monitor.py --plan custom_max
```

### Quick Check with Default Settings
```bash
# Just run it!
./ccusage_monitor.py
```

### International User
```bash
# Use your local timezone
./ccusage_monitor.py --timezone America/New_York
./ccusage_monitor.py --timezone Asia/Singapore
./ccusage_monitor.py --timezone Australia/Sydney
```

### Future: ML-Powered Monitoring
```bash
# Coming soon! Let ML learn your patterns
# ./ccusage_monitor.py --plan ml_auto
```

---

## 🤝 Contributing

We welcome contributions from the community! This project thrives on your input and improvements.

### How to Contribute

1. **🍴 Fork the repository**
   ```bash
   git clone https://github.com/YOUR-USERNAME/Claude-Code-Usage-Monitor.git
   ```

2. **🌿 Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **💻 Make your changes**
   - Add new features
   - Fix bugs
   - Improve documentation
   - Enhance UI/UX

4. **✅ Test your changes**
   ```bash
   # Set up virtual environment
   python3 -m venv venv
   source venv/bin/activate
   pip install pytz
   
   # Run the monitor to test
   python ccusage_monitor.py
   ```

5. **📝 Commit with clear messages**
   ```bash
   git commit -m "Add: Brief description of your change"
   ```

6. **🚀 Push to your fork**
   ```bash
   git push origin feature/amazing-feature
   ```

7. **🔄 Open a Pull Request**
   - Describe what your changes do
   - Reference any related issues
   - Include screenshots for UI changes

### Development Guidelines

- **Code Style**: Follow PEP 8 for Python code
- **Comments**: Add clear comments for complex logic
- **Documentation**: Update README if adding new features
- **Testing**: Ensure your changes work on different platforms
- **Commits**: Use meaningful commit messages

### Help Us Improve Token Limit Detection

We're collecting data about actual token limits to improve the auto-detection feature. If you're using Claude and your tokens exceeded the standard limits, please share your experience in [Issue #1](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/issues/1):

**What to share:**
- Your subscription type (Pro, Teams, Enterprise)
- The maximum tokens you reached (custom_max value)
- When the limit was exceeded
- Any patterns you've noticed

This data helps us better understand token allocation across different subscription tiers and improve the monitoring tool for everyone.

### 💡 Ideas for Contributions

- **📊 ML Visualizations**: Design real-time prediction graphs, confidence intervals
- **New Features**: Export usage statistics, GUI version, mobile app
- **Integrations**: Slack notifications, email alerts, webhook support
- **Analytics**: Historical data tracking, usage patterns analysis
- **UI Improvements**: Different themes, compact mode, graph visualizations
- **Platform Support**: Better Windows support, Docker container
- **🔬 Research**: Experiment with different ML algorithms for token prediction

---

## 📝 License

[MIT License](LICENSE) - feel free to use and modify as needed.

---

## 🙏 Acknowledgments

This tool builds upon the excellent [ccusage](https://github.com/ryoppippi/ccusage) by [@ryoppippi](https://github.com/ryoppippi), adding a real-time monitoring interface with visual progress bars, burn rate calculations, and predictive analytics.

- 🏗️ Built for monitoring [Claude Code](https://claude.ai/code) token usage
- 🔧 Uses [ccusage](https://www.npmjs.com/package/ccusage) for data retrieval
- 🧠 Currently implementing machine learning algorithms for intelligent limit detection
- 💾 Will be powered by DuckDB for efficient local data analysis
- 💭 Inspired by the need for better token usage visibility

---

<div align="center">

**⭐ Star this repo if you find it useful! ⭐**

[Report Bug](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/issues) • [Request Feature](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/issues) • [Contribute](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/pulls)

</div>
