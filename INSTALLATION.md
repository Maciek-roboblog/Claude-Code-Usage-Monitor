# 📦 Installation Guide

Complete installation instructions for Claude Usage Monitor as a Python package.

## 🚀 Quick Installation (Recommended)

### 1. Install from Local Source

```bash
# Clone repository
git clone https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor.git
cd Claude-Code-Usage-Monitor

# Install ccusage dependency first
npm install -g ccusage

# Install the package
pip install .

# Or install in development mode
pip install -e .
```

### 2. Run from Anywhere

After installation, you can run the monitor from any directory:

```bash
# Main command
claude-monitor

# Short aliases  
cmonitor
ccm

# With options
claude-monitor --plan max5 --timezone America/New_York
cmonitor --reset-hour 9
ccm --plan custom_max
```

## 🔧 Development Installation

### 1. Development Setup

```bash
# Clone and enter directory
git clone https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor.git
cd Claude-Code-Usage-Monitor

# Install ccusage dependency
npm install -g ccusage

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install in development mode with dev dependencies
pip install -e ".[dev]"
```

### 2. Verify Installation

```bash
# Check installation
claude-monitor --help
pip show claude-usage-monitor

# Test functionality
ccusage --version
claude-monitor --plan pro
```

## 📋 Build and Distribution

### 1. Build Package

```bash
# Install build tools
pip install build twine

# Build package
python -m build

# Check built files
ls dist/
# Should show: claude_usage_monitor-1.0.0-py3-none-any.whl
#              claude-usage-monitor-1.0.0.tar.gz
```

### 2. Install from Built Package

```bash
# Install from wheel
pip install dist/claude_usage_monitor-1.0.0-py3-none-any.whl

# Or install from source distribution
pip install dist/claude-usage-monitor-1.0.0.tar.gz
```

### 3. Upload to PyPI (Future)

```bash
# Check package
twine check dist/*

# Upload to Test PyPI first
twine upload --repository testpypi dist/*

# Install from Test PyPI
pip install -i https://test.pypi.org/simple/ claude-usage-monitor

# Upload to PyPI (when ready)
twine upload dist/*
```

## 🌍 System-wide Installation

### Linux/Mac

```bash
# Install system-wide (requires sudo)
sudo pip install .

# Or install to user directory
pip install --user .

# Add user bin to PATH if needed
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Windows

```bash
# Install for current user
pip install --user .

# Or system-wide (run as Administrator)
pip install .
```

## 🐳 Docker Installation (Future)

```bash
# When Docker image is available
docker pull maciek/claude-usage-monitor

# Run in container
docker run -it maciek/claude-usage-monitor

# With environment variables
docker run -e PLAN=max5 -e RESET_HOUR=9 maciek/claude-usage-monitor
```

## 🧪 Testing Installation

### 1. Basic Tests

```bash
# Test command availability
which claude-monitor  # Linux/Mac
where claude-monitor  # Windows

# Test help
claude-monitor --help
cmonitor --help
ccm --help

# Test version
python -c "import ccusage_monitor; print(ccusage_monitor.__version__)"
```

### 2. Functional Tests

```bash
# Test ccusage integration
ccusage --version
ccusage blocks --json

# Test monitor (requires active Claude session)
claude-monitor --plan pro
# Press Ctrl+C to exit
```

### 3. Development Tests

```bash
# Run test suite (when available)
pytest

# Code formatting
black ccusage_monitor.py

# Linting
flake8 ccusage_monitor.py
```

## 🔧 Troubleshooting

### Command Not Found

```bash
# Check if package is installed
pip list | grep claude-usage-monitor

# Check PATH
echo $PATH

# Reinstall if needed
pip uninstall claude-usage-monitor
pip install .
```

### ccusage Dependency Issues

```bash
# Verify ccusage is installed
npm list -g ccusage
ccusage --version

# Reinstall ccusage if needed
npm uninstall -g ccusage
npm install -g ccusage
```

### Virtual Environment Issues

```bash
# Deactivate and recreate environment
deactivate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

## 🚀 Quick Commands Reference

```bash
# Installation commands
npm install -g ccusage    # Install ccusage dependency
pip install .             # Install claude-usage-monitor
pip install -e .          # Install in development mode

# Usage commands
claude-monitor            # Default monitoring
cmonitor --plan max5      # With specific plan
ccm --help               # Show help

# Development commands
python -m build          # Build package
twine check dist/*       # Check built package
pytest                   # Run tests (when available)
```

## 📞 Support

If you encounter installation issues:

1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Open an issue on [GitHub](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/issues)
3. Contact: [maciek@roboblog.eu](mailto:maciek@roboblog.eu)