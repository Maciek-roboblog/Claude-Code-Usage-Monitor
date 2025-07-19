# 🐛 Troubleshooting Guide - Claude Monitor v3.0.0

**⚠️ This guide is specifically for Claude Monitor v3.0.0** - If you're using an older version, please upgrade first.

## 🚨 Quick Fixes

### Most Common v3.0.0 Issues

| Problem | Quick Fix |
|---------|-----------|
| `command not found: claude-monitor` | Add `~/.local/bin` to PATH or use `python -m claude_monitor` |
| `externally-managed-environment` | Use `uv tool install claude-monitor` instead of pip |
| No Claude data found | Ensure you have active Claude Code sessions with recent messages |
| Validation errors | Check configuration with `claude-monitor --help` |
| Display issues | Terminal width must be 80+ characters |
| Theme detection problems | Use `--theme dark` or `--theme light` explicitly |

## 🔧 Installation Issues (v3.0.0)

### Package Name Change

**v3.0.0 Breaking Change**: Package name changed from `claude-usage-monitor` to `claude-monitor`

```bash
# OLD (deprecated)
pip install claude-usage-monitor

# NEW (v3.0.0)
pip install claude-monitor
uv tool install claude-monitor
```

### "externally-managed-environment" Error

**Common on Ubuntu 23.04+, Debian 12+, Fedora 38+**

**Solutions (in order of preference)**:

1. **Use uv (Recommended)**:
   ```bash
   # Install uv
   curl -LsSf https://astral.sh/uv/install.sh | sh
   source ~/.bashrc

   # Install claude-monitor
   uv tool install claude-monitor
   claude-monitor
   ```

2. **Use pipx**:
   ```bash
   # Install pipx
   sudo apt install pipx  # Ubuntu/Debian
   pipx install claude-monitor
   claude-monitor
   ```

3. **Use virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install claude-monitor
   claude-monitor
   ```

### Command Not Found After Installation

**Issue**: `claude-monitor` command not found

**Solutions**:

1. **Check PATH**:
   ```bash
   # Add to ~/.bashrc or ~/.zshrc
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
   source ~/.bashrc
   ```

2. **Use Python module**:
   ```bash
   python -m claude_monitor
   ```

3. **Check installation**:
   ```bash
   pip show claude-monitor
   which claude-monitor
   ```

### Python Version Requirements

**v3.0.0 requires Python 3.9+**

```bash
# Check Python version
python3 --version

# If too old, upgrade Python or use specific version
python3.11 -m pip install claude-monitor
python3.11 -m claude_monitor
```

### Dependency Installation Issues

**Missing dependencies error**:
```bash
# Manual installation of core dependencies
pip install pytz>=2023.3 rich>=13.7.0 pydantic>=2.0.0
pip install pydantic-settings>=2.0.0 numpy>=1.21.0
```

## 💾 Data and Configuration Issues

### No Claude Data Directory Found

**Error**: `No Claude data directory found`

**Causes and Solutions**:

1. **Default data path doesn't exist**:
   ```bash
   # Check if directory exists
   ls ~/.claude/projects

   # Start Claude Code session first
   # Go to claude.ai/code and send messages
   ```

2. **Permission issues**:
   ```bash
   # Check permissions
   ls -la ~/.claude/

   # Fix permissions if needed
   chmod 755 ~/.claude/projects
   ```

3. **Custom data path**:
   ```bash
   # If Claude uses different path, set environment variable
   export CLAUDE_CONFIG_DIR=/path/to/your/claude/config
   claude-monitor
   ```

### JSONL File Processing Errors

**Error**: `Failed to parse JSON line in {file}: {error}`

**Solutions**:
1. **Corrupted files**: Let monitor skip malformed lines (automatic)
2. **Check file integrity**:
   ```bash
   # Validate JSONL files
   find ~/.claude/projects -name "*.jsonl" -exec python -c "
   import json
   with open('{}') as f:
       for i, line in enumerate(f, 1):
           try: json.loads(line)
           except: print(f'Error in {}: line {i}')
   " \;
   ```

### Session Detection Issues

**Error**: `No active session found`

**Debugging steps**:

1. **Verify Claude Code usage**:
   - Must use claude.ai/code (not regular Claude)
   - Send at least 2-3 messages
   - Wait 30 seconds after last message

2. **Check data freshness**:
   ```bash
   # Check recent files
   find ~/.claude/projects -name "*.jsonl" -mtime -1 -ls
   ```

3. **Manual data verification**:
   ```bash
   # Enable debug logging
   claude-monitor --debug --log-file /tmp/claude-debug.log

   # Check logs
   tail -f /tmp/claude-debug.log
   ```

## ⚙️ Configuration Validation Errors

### Invalid Plan Configuration

**Error**: `Invalid plan: {value}. Must be one of: pro, max5, max20, custom`

**Valid options**:
```bash
# Correct plan names (case-insensitive)
claude-monitor --plan pro      # 44k tokens
claude-monitor --plan max5     # 88k tokens
claude-monitor --plan max20    # 220k tokens
claude-monitor --plan custom   # P90 auto-detection
```

### Invalid Theme Settings

**Error**: `Invalid theme: {value}. Must be one of: light, dark, classic, auto`

**Solutions**:
```bash
# Force specific theme
claude-monitor --theme dark
claude-monitor --theme light

# Debug theme detection
claude-monitor --debug
```

### Timezone Validation Errors

**Error**: `Invalid timezone: {value}`

**Solutions**:
```bash
# Use auto-detection (default)
claude-monitor --timezone auto

# Valid timezone examples
claude-monitor --timezone UTC
claude-monitor --timezone America/New_York
claude-monitor --timezone Europe/London
claude-monitor --timezone Asia/Tokyo

# List available timezones
python -c "import pytz; print('\n'.join(sorted(pytz.all_timezones)))" | grep America
```

### Numeric Range Validation Errors

**Common validation failures**:

```bash
# Refresh rate: must be 1-60 seconds
claude-monitor --refresh-rate 5    # Valid
claude-monitor --refresh-rate 0    # Invalid: below minimum

# Display refresh rate: must be 0.1-20 Hz
claude-monitor --refresh-per-second 1.0   # Valid
claude-monitor --refresh-per-second 25    # Invalid: above maximum

# Reset hour: must be 0-23
claude-monitor --reset-hour 9      # Valid
claude-monitor --reset-hour 24     # Invalid: out of range

# Custom token limit: must be positive
claude-monitor --plan custom --custom-limit-tokens 50000  # Valid
claude-monitor --plan custom --custom-limit-tokens 0      # Invalid
```

## 🖥️ Display and Terminal Issues

### Terminal Width Too Narrow

**Issue**: Overlapping text, garbled display

**Solutions**:
```bash
# Check terminal width
tput cols  # Should be 80+

# Resize terminal window or use scrolling
claude-monitor | less -S
```

### Theme Detection Problems

**Issue**: Wrong colors, poor contrast

**Debug theme detection**:
```bash
# Check environment variables
echo $COLORFGBG
echo $TERM
echo $COLORTERM

# Force theme explicitly
claude-monitor --theme dark   # For dark terminals
claude-monitor --theme light  # For light terminals
```

**SSH/Remote sessions**:
```bash
# Theme detection may fail over SSH
claude-monitor --theme dark  # Usually safer for SSH
```

### Missing Colors or Emojis

**Issue**: Plain text output, no colors

**Solutions**:
```bash
# Check terminal capabilities
echo $TERM
echo $COLORTERM

# Force color output
export FORCE_COLOR=1
claude-monitor

# Try different terminal
# iTerm2, Windows Terminal, or modern Linux terminals work best
```

### Cursor Remains Hidden After Exit

**Issue**: Terminal cursor invisible after Ctrl+C

**Quick fix**:
```bash
# Restore cursor
printf '\033[?25h'

# Or reset terminal completely
reset
```

## 🔄 Runtime and Performance Issues

### Monitor Startup Timeout

**Error**: `Timeout waiting for initial data`

**Causes and solutions**:

1. **Slow data loading**:
   ```bash
   # Use custom timeout
   # (Note: Not directly configurable, but data loads faster on subsequent runs)

   # Check if Claude data exists
   ls -la ~/.claude/projects/*.jsonl
   ```

2. **Large data files**:
   ```bash
   # Monitor memory usage
   top -p $(pgrep -f claude_monitor)

   # Use quick start mode (automatically enabled)
   claude-monitor  # Loads only last 24 hours initially
   ```

### High CPU or Memory Usage

**Issue**: Monitor consuming too many resources

**Solutions**:
```bash
# Reduce refresh rate
claude-monitor --refresh-rate 30          # Data refresh every 30s
claude-monitor --refresh-per-second 0.5   # Display refresh at 0.5 Hz

# Monitor resource usage
htop | grep claude-monitor
```

### Thread and Callback Errors

**Error**: `Callback error: {error}` or `Session callback error: {error}`

**Debug approach**:
```bash
# Enable detailed logging
claude-monitor --debug --log-file /tmp/debug.log

# Check thread status
ps -T -p $(pgrep -f claude_monitor)
```

## 🔍 Advanced Debugging

### Enable Debug Mode

```bash
# Full debug output
claude-monitor --debug

# Debug with file logging
claude-monitor --debug --log-file ~/.claude-monitor/logs/debug.log

# Check logs
tail -f ~/.claude-monitor/logs/debug.log
```

### Validate Configuration

```bash
# Test configuration without starting monitor
python -c "
from claude_monitor.core.settings import Settings
try:
    settings = Settings.load_with_last_used(['--plan', 'custom'])
    print('Configuration valid')
    print(f'Plan: {settings.plan}')
    print(f'Theme: {settings.theme}')
    print(f'Timezone: {settings.timezone}')
except Exception as e:
    print(f'Configuration error: {e}')
"
```

### Check Data Path Discovery

```bash
# Test data path discovery
python -c "
from claude_monitor.cli.main import discover_claude_data_paths
paths = discover_claude_data_paths()
print(f'Found paths: {paths}')
for path in paths:
    print(f'  {path}: {len(list(path.glob(\"*.jsonl\")))} JSONL files')
"
```

### Validate JSONL Data Structure

```bash
# Check data structure
python -c "
from claude_monitor.data.reader import load_usage_entries
try:
    entries, raw = load_usage_entries(include_raw=True)
    print(f'Loaded {len(entries)} entries')
    if entries:
        print(f'Latest entry: {entries[-1].timestamp}')
        print(f'Total tokens: {entries[-1].input_tokens + entries[-1].output_tokens}')
except Exception as e:
    print(f'Data loading error: {e}')
"
```

### Test Pydantic Settings

```bash
# Test settings validation
python -c "
from claude_monitor.core.settings import Settings
from pydantic import ValidationError

test_cases = [
    ['--plan', 'invalid'],
    ['--theme', 'invalid'],
    ['--timezone', 'Invalid/Zone'],
    ['--refresh-rate', '0'],
    ['--refresh-per-second', '25'],
    ['--reset-hour', '24']
]

for case in test_cases:
    try:
        Settings.load_with_last_used(case)
        print(f'{case}: Valid')
    except ValidationError as e:
        print(f'{case}: {e.errors()[0][\"msg\"]}')
    except Exception as e:
        print(f'{case}: {e}')
"
```

## 🆘 Getting Help

### Before Reporting Issues

1. **Check this guide first**
2. **Try with debug mode**: `claude-monitor --debug`
3. **Verify installation**: `pip show claude-monitor`
4. **Test with minimal config**: `claude-monitor --clear`

### Information to Include in Bug Reports

```bash
# System information
uname -a  # Linux/Mac
systeminfo  # Windows

# Python and package versions
python --version
pip show claude-monitor

# Installation method
which claude-monitor
echo $PATH

# Configuration test
claude-monitor --help

# Debug output (if possible)
claude-monitor --debug | head -20
```

### Issue Template

```markdown
**Problem**: Brief description

**Environment**:
- OS: [Ubuntu 24.04 / Windows 11 / macOS 14]
- Python: [3.11.0]
- Installation: [uv/pip/pipx/source]
- Version: [3.0.0]

**Steps to Reproduce**:
1. Command: `claude-monitor --plan custom`
2. Expected: ...
3. Actual: ...

**Error Output**:
```
Paste error messages here
```

**Debug Information**:
```
Output from: claude-monitor --debug | head -20
```
```

### Where to Get Help

1. **GitHub Issues**: [Create new issue](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/issues/new)
2. **Email**: [maciek@roboblog.eu](mailto:maciek@roboblog.eu)
3. **Documentation**: [README.md](README.md)

## 🔄 Complete Reset

If all else fails:

```bash
# 1. Uninstall completely
pip uninstall claude-monitor
uv tool uninstall claude-monitor  # if using uv
pipx uninstall claude-monitor     # if using pipx

# 2. Clear all configuration
rm -rf ~/.claude-monitor/

# 3. Clear Python cache
find . -name "*.pyc" -delete 2>/dev/null
find . -name "__pycache__" -delete 2>/dev/null

# 4. Fresh installation (choose one)
uv tool install claude-monitor     # Recommended
# OR
pipx install claude-monitor       # Alternative
# OR
python -m venv venv && source venv/bin/activate && pip install claude-monitor

# 5. Test installation
claude-monitor --help
claude-monitor --version
```

---

**Still having issues?** Don't hesitate to [create an issue](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/issues/new) with the **[v3.0.0]** tag in the title!
