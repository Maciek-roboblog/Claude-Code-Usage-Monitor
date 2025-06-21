# 🐛 Troubleshooting Guide

Common issues and solutions for Claude Code Usage Monitor.

## 🚨 Quick Fixes

### Most Common Issues

| Problem | Quick Fix |
|---------|-----------|
| `command not found: claude-monitor` | Add `~/.local/bin` to PATH or use `python3 -m claude_monitor` |
| `externally-managed-environment` | Use `uv tool install` or `pipx install` instead of pip |
| `ccusage` not found | Should auto-install, or run `npm install -g ccusage` |
| No active session | Start a Claude Code session first |
| Permission denied | Only for source: `chmod +x claude_monitor.py` |
| Display issues | Resize terminal to 80+ characters width |
| Hidden cursor after exit | `printf '\033[?25h'` |


## 🔧 Installation Issues

### "externally-managed-environment" Error (Modern Linux)

**Error Message**:
```
error: externally-managed-environment
× This environment is externally managed
```

**This is common on Ubuntu 23.04+, Debian 12+, Fedora 38+**

**Solutions (in order of preference)**:

1. **Use uv (Recommended)**:
   ```bash
   # Install uv
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Install claude-monitor
   uv tool install claude-monitor
   ```

2. **Use pipx**:
   ```bash
   # Install pipx
   sudo apt install pipx  # Ubuntu/Debian
   # or
   python3 -m pip install --user pipx

   # Install claude-monitor
   pipx install claude-monitor
   ```

3. **Use virtual environment**:
   ```bash
   python3 -m venv myenv
   source myenv/bin/activate
   pip install claude-monitor
   ```

4. **Force installation (NOT recommended)**:
   ```bash
   pip install --user claude-monitor --break-system-packages
   ```
   ⚠️ **Warning**: This bypasses system protection. Use virtual environment instead!

### Command Not Found After pip Install

**Issue**: `claude-monitor` command not found after pip installation

**Solutions**:

1. **Check installation location**:
   ```bash
   pip show -f claude-monitor | grep claude-monitor
   ```

2. **Add to PATH**:
   ```bash
   # Add this to ~/.bashrc or ~/.zshrc
   export PATH="$HOME/.local/bin:$PATH"

   # Reload shell
   source ~/.bashrc
   ```

3. **Run with Python module**:
   ```bash
   python3 -m claude_monitor
   ```

### Python Version Conflicts

**Issue**: Multiple Python versions causing installation issues

**Solutions**:

1. **Check Python version**:
   ```bash
   python3 --version
   pip3 --version
   ```

2. **Use specific Python version**:
   ```bash
   python3.11 -m pip install claude-monitor
   python3.11 -m claude_monitor
   ```

3. **Use uv (handles Python versions automatically)**:
   ```bash
   uv tool install claude-monitor
   ```

### ccusage Not Found

**Error Message**:
```
Failed to get usage data: [Errno 2] No such file or directory: 'ccusage'
```

**Note**: The monitor should automatically install Node.js and ccusage on first run. If this fails:

**Manual Solution**:
```bash
# Install ccusage globally
npm install -g ccusage

# Verify installation
ccusage --version

# Check if it's in PATH
which ccusage  # Linux/Mac
where ccusage  # Windows
```

**Alternative Solutions**:
```bash
# If npm install fails, try:
sudo npm install -g ccusage  # Linux/Mac with sudo

# Or update npm first:
npm update -g npm
npm install -g ccusage

# For Windows, run as Administrator
npm install -g ccusage
```

### Python Dependencies Missing

**Error Message**:
```
ModuleNotFoundError: No module named 'pytz'
```

**Solution**:
```bash
# If installed via pip/pipx/uv, this should be automatic
# If running from source:
pip install pytz

# For virtual environment users:
source venv/bin/activate  # Linux/Mac
pip install pytz
```

**Note**: When installing via `pip install claude-monitor`, `uv tool install claude-monitor`, or `pipx install claude-monitor`, pytz is installed automatically.

### Permission Denied (Linux/Mac)

**Error Message**:
```
Permission denied: ./claude_monitor.py
```

**This only applies when running from source**

**Solution**:
```bash
# Make script executable
chmod +x claude_monitor.py

# Or run with python directly
python claude_monitor.py
python3 claude_monitor.py
```

**Note**: If installed via pip/pipx/uv, use `claude-monitor` command instead.


## 📊 Usage Data Issues

### No Active Session Found

**Error Message**:
```
No active session found. Please start a Claude session first.
```

**Cause**: Monitor only works when you have an active Claude Code session.

**Solution**:
1. Go to [claude.ai/code](https://claude.ai/code)
2. Start a conversation with Claude
3. Send at least one message
4. Run the monitor again

**Verification**:
```bash
# Test if ccusage can detect sessions
ccusage blocks --json
```

### Failed to Get Usage Data

**Error Message**:
```
Failed to get usage data: <various error messages>
```

**Debugging Steps**:

1. **Check ccusage installation**:
   ```bash
   ccusage --version
   ccusage blocks --json
   ```

2. **Verify Claude session**:
   - Ensure you're logged into Claude
   - Send a recent message to Claude Code
   - Check that you're using Claude Code, not regular Claude

3. **Check network connectivity**:
   ```bash
   # Test basic connectivity
   ping claude.ai
   curl -I https://claude.ai
   ```

4. **Clear browser data** (if ccusage uses browser data):
   - Clear Claude cookies
   - Re-login to Claude
   - Start fresh session

### Incorrect Token Counts

**Issue**: Monitor shows unexpected token numbers

**Possible Causes & Solutions**:

1. **Multiple Sessions**:
   - Remember: You can have multiple 5-hour sessions
   - Each session has its own token count
   - Monitor shows aggregate across all active sessions

2. **Session Timing**:
   - Sessions last exactly 5 hours from first message
   - Reset times are reference points, not actual resets
   - Check session start times in monitor output

3. **Plan Detection Issues**:
   ```bash
   # Try different plan settings
   ./claude_monitor.py --plan custom_max
   ./claude_monitor.py --plan max5
   ```


## 🖥️ Display Issues

### Terminal Too Narrow

**Issue**: Overlapping text, garbled display

**Solution**:
```bash
# Check terminal width
tput cols

# Should be 80 or more characters
# Resize terminal window or use:
./claude_monitor.py | less -S  # Scroll horizontally
```

### Missing Colors

**Issue**: No color output, plain text only

**Solutions**:
```bash
# Check terminal color support
echo $TERM

# Force color output (if supported)
export FORCE_COLOR=1
./claude_monitor.py

# Alternative terminals with better color support:
# - Use modern terminal (iTerm2, Windows Terminal, etc.)
# - Check terminal settings for ANSI color support
```

### Screen Flicker

**Issue**: Excessive screen clearing/redrawing

**Cause**: Terminal compatibility issues

**Solutions**:
1. Use a modern terminal emulator
2. Check terminal size (minimum 80 characters)
3. Ensure stable window size during monitoring

### Cursor Remains Hidden After Exit

**Issue**: Terminal cursor invisible after Ctrl+C

**Quick Fix**:
```bash
# Restore cursor visibility
printf '\033[?25h'

# Or reset terminal completely
reset
```

**Prevention**: Always exit with Ctrl+C for graceful shutdown


## ⏰ Time & Timezone Issues

### Incorrect Reset Times

**Issue**: Reset predictions don't match your schedule

**Solution**:
```bash
# Set your timezone explicitly
./claude_monitor.py --timezone America/New_York
./claude_monitor.py --timezone Europe/London
./claude_monitor.py --timezone Asia/Tokyo

# Set custom reset hour
./claude_monitor.py --reset-hour 9  # 9 AM resets
```

**Find Your Timezone**:
```bash
# Linux/Mac - find available timezones
timedatectl list-timezones | grep -i america
timedatectl list-timezones | grep -i europe

# Or use online timezone finder
# https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
```

### Session Expiration Confusion

**Issue**: Don't understand when sessions expire

**Explanation**:
- Sessions last **exactly 5 hours** from your first message
- Default reset times (4:00, 9:00, 14:00, 18:00, 23:00) are reference points
- Your actual session resets 5 hours after YOU start each session

**Example**:
```
10:30 AM - You send first message → Session expires 3:30 PM
02:00 PM - You start new session → Session expires 7:00 PM
```

## 🔧 Platform-Specific Issues

### Windows Issues

**PowerShell Execution Policy**:
```powershell
# If scripts are blocked
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Run with Python directly
python claude_monitor.py
```

**Path Issues**:
```bash
# If ccusage not found, add npm global path
npm config get prefix
# Add result/bin to PATH environment variable
```

**Virtual Environment on Windows**:
```cmd
# Activate virtual environment
venv\Scripts\activate

# Deactivate
deactivate
```

### macOS Issues

**Permission Issues with Homebrew Python**:
```bash
# Use system Python if Homebrew Python has issues
/usr/bin/python3 -m venv venv

# Or reinstall Python via Homebrew
brew reinstall python3
```

**ccusage Installation Issues**:
```bash
# If npm permission issues
sudo chown -R $(whoami) $(npm config get prefix)/{lib/node_modules,bin,share}

# Or use nvm for Node.js management
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install node
```

### Linux Issues

**Missing Python venv Module**:
```bash
# Ubuntu/Debian
sudo apt-get install python3-venv

# Fedora/CentOS
sudo dnf install python3-venv

# Arch Linux
sudo pacman -S python-virtualenv
```

**npm Permission Issues**:
```bash
# Configure npm to use different directory
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.profile
source ~/.profile
```


## 🧠 Performance Issues

### High CPU Usage

**Cause**: Monitor updates every 3 seconds

**Solutions**:
1. **Normal behavior**: 3-second updates are intentional for real-time monitoring
2. **Reduce frequency**: Currently not configurable, but will be in future versions
3. **Close when not needed**: Use Ctrl+C to exit when not actively monitoring

### Memory Usage Growing

**Issue**: Memory usage increases over time

**Debugging**:
```bash
# Monitor memory usage
top -p $(pgrep -f claude_monitor)
htop  # Look for claude_monitor process

# Check for memory leaks
python -m tracemalloc claude_monitor.py
```

**Solutions**:
1. Restart monitor periodically for long sessions
2. Report issue with system details
3. Use virtual environment to isolate dependencies

### Slow Startup

**Cause**: ccusage needs to fetch session data

**Normal**: First run may take 5-10 seconds

**If consistently slow**:
1. Check internet connection
2. Verify Claude session is active
3. Clear browser cache/cookies for Claude


## 🔄 Data Accuracy Issues

### Token Counts Don't Match Claude UI

**Possible Causes**:

1. **Different Counting Methods**:
   - Monitor counts tokens used in current session(s)
   - Claude UI might show different metrics
   - Multiple sessions can cause confusion

2. **Timing Differences**:
   - Monitor updates every 3 seconds
   - Claude UI updates in real-time
   - Brief discrepancies are normal

3. **Session Boundaries**:
   - Monitor tracks 5-hour session windows
   - Verify you're comparing the same time periods

**Debugging**:
```bash
# Check raw ccusage data
ccusage blocks --json | jq .

# Compare with monitor output
./claude_monitor.py --plan custom_max
```

### Burn Rate Calculations Seem Wrong

**Understanding Burn Rate**:
- Calculated from token usage in the last hour
- Includes all active sessions
- May fluctuate based on recent activity

**If still seems incorrect**:
1. Monitor for longer period (10+ minutes)
2. Check if multiple sessions are active
3. Verify recent usage patterns match expectations


## 🆘 Getting Help

### Before Asking for Help

1. **Check this troubleshooting guide**
2. **Search existing GitHub issues**
3. **Try basic debugging steps**
4. **Gather system information**

### What Information to Include

When reporting issues, include:

```bash
# System information
uname -a  # Linux/Mac
systeminfo  # Windows

# Python version
python --version
python3 --version

# Installation method
# Did you use: pip, pipx, uv, or source?

# Check installation
pip show claude-monitor  # If using pip
uv tool list  # If using uv
pipx list  # If using pipx

# Node.js and npm versions
node --version
npm --version

# ccusage version
ccusage --version

# Test ccusage directly
ccusage blocks --json
```

### Where to Get Help

1. **GitHub Issues**: [Create new issue](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/issues/new)
2. **Email**: [maciek@roboblog.eu](mailto:maciek@roboblog.eu)
3. **Documentation**: Check [README.md](README.md) for installation and usage

### Issue Template

```markdown
**[MAIN-PROBLEM]: Your specific problem**

**Problem Description**
Clear description of the issue.

**Installation Method**
- [ ] pip install claude-monitor
- [ ] pipx install claude-monitor
- [ ] uv tool install claude-monitor
- [ ] Running from source

**Steps to Reproduce**
1. Command run: `claude-monitor --plan pro`
2. Expected result: ...
3. Actual result: ...

**Environment**
- OS: [Ubuntu 24.04 / Windows 11 / macOS 14]
- Python: [3.11.0]
- Node.js: [20.0.0]
- ccusage: [latest]
- Installation path: [e.g., /home/user/.local/bin/claude-monitor]

**Error Output**
```
Paste full error messages here
```

**Additional Context**
Any other relevant information.
```


## 🔧 Advanced Debugging

### Enable Debug Mode

```bash
# Run with Python verbose output
python -v claude_monitor.py

# Check ccusage debug output
ccusage blocks --debug

# Monitor system calls (Linux/Mac)
strace -e trace=execve python claude_monitor.py
```

### Network Debugging

```bash
# Check if ccusage makes network requests
netstat -p | grep ccusage  # Linux
lsof -i | grep ccusage     # Mac

# Monitor network traffic
tcpdump -i any host claude.ai  # Requires sudo
```

### File System Debugging

```bash
# Check if ccusage accesses browser data
strace -e trace=file python claude_monitor.py  # Linux
dtruss python claude_monitor.py               # Mac

# Look for browser profile directories
ls ~/.config/google-chrome/Default/  # Linux Chrome
ls ~/Library/Application\ Support/Google/Chrome/Default/  # Mac Chrome
```


## 🔄 Reset Solutions

### Complete Reset

If all else fails, complete reset:

```bash
# 1. Uninstall everything
npm uninstall -g ccusage
pip uninstall claude-monitor  # If installed via pip
pipx uninstall claude-monitor  # If installed via pipx
uv tool uninstall claude-monitor  # If installed via uv

# 2. Clear caches
find ~/.cache -name "*claude*" -delete 2>/dev/null
find . -name "*.pyc" -delete
find . -name "__pycache__" -delete

# 3. Fresh installation (choose one method)
# Method 1: uv (Recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc  # or restart terminal
uv tool install claude-monitor

# Method 2: pipx
pipx install claude-monitor

# Method 3: pip with venv
python3 -m venv myenv
source myenv/bin/activate
pip install claude-monitor

# 4. Install ccusage if needed
npm install -g ccusage

# 5. Test basic functionality
ccusage --version
claude-monitor --help
```

### Browser Reset for Claude

```bash
# Clear Claude-specific data
# 1. Logout from Claude
# 2. Clear cookies for claude.ai
# 3. Clear browser cache
# 4. Login again and start fresh session
# 5. Test ccusage functionality
```

---

**Still having issues?** Don't hesitate to [create an issue](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/issues/new) or [contact us directly](mailto:maciek@roboblog.eu)!
