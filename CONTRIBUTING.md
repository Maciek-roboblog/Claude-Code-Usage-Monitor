# 🤝 Contributing Guide

Welcome to the Claude Code Usage Monitor project! We're excited to have you contribute to making this tool better for everyone.

---

## 🌟 How to Contribute

### 🎯 Types of Contributions

We welcome all kinds of contributions:

- **🐛 Bug Reports**: Found something broken? Let us know!
- **💡 Feature Requests**: Have an idea for improvement?
- **📝 Documentation**: Help improve guides and examples
- **🔧 Code Contributions**: Fix bugs or implement new features
- **🧪 Testing**: Help test on different platforms
- **🎨 UI/UX**: Improve the visual design and user experience
- **🧠 ML Research**: Contribute to machine learning features
- **📦 Packaging**: Help with PyPI, Docker, or distribution

---

## 🚀 Quick Start for Contributors

### 1. Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR-USERNAME/Claude-Code-Usage-Monitor.git
cd Claude-Code-Usage-Monitor
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install project and development dependencies
pip install -e .[dev]

# Run from source
python -m claude_monitor --help
```

### 3. Create a Feature Branch

```bash
# Create and switch to feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description
```

### 4. Make Your Changes

- Follow our coding standards (see below)
- Add tests for new functionality
- Update documentation if needed
- Test your changes thoroughly

### 5. Submit Your Contribution

```bash
# Add and commit your changes
git add .
git commit -m "Add: Brief description of your change"

# Push to your fork
git push origin feature/your-feature-name

# Open a Pull Request on GitHub
```

---

## 📋 Development Guidelines

### 🐍 Python Code Style

We follow **PEP 8** with these specific guidelines:

```python
# Good: Clear variable names
current_token_count = 1500
session_start_time = datetime.now()

# Bad: Unclear abbreviations
curr_tok_cnt = 1500
sess_st_tm = datetime.now()

# Good: Descriptive function names
def calculate_burn_rate(tokens_used, time_elapsed):
    return tokens_used / time_elapsed

# Good: Clear comments for complex logic
def predict_token_depletion(current_usage, burn_rate):
    """
    Predicts when tokens will be depleted based on current burn rate.

    Args:
        current_usage (int): Current token count
        burn_rate (float): Tokens consumed per minute

    Returns:
        datetime: Estimated depletion time
    """
    pass
```

### 🧪 Testing Guidelines

```python
# Test file naming: test_*.py
# src/tests/test_settings.py

from claude_monitor.core.plans import Plans

def test_pro_plan_limit():
    """Test the documented Pro plan token limit."""
    plan = Plans.get_plan_by_name("pro")
    assert plan.token_limit == 19_000

def test_invalid_plan_name():
    """Test invalid plan validation."""
    assert Plans.get_plan_by_name("invalid") is None
```

### 📝 Commit Message Format

Use clear, descriptive commit messages:

```bash
# Good commit messages
git commit -m "Add: ML-powered token prediction algorithm"
git commit -m "Fix: Handle edge case when no sessions are active"
git commit -m "Update: Improve error handling in data discovery"
git commit -m "Docs: Add examples for timezone configuration"

# Prefixes to use:
# Add: New features
# Fix: Bug fixes
# Update: Improvements to existing features
# Docs: Documentation changes
# Test: Test additions or changes
# Refactor: Code refactoring
# Style: Code style changes
```


## 🎯 Contribution Areas (Priority things)

### 📦 PyPI Package Development

**Current Needs**:
- Create proper package structure
- Configure setup.py and requirements
- Implement global configuration system
- Add command-line entry points

**Skills Helpful**:
- Python packaging (setuptools, wheel)
- Configuration management
- Cross-platform compatibility
- Command-line interface design

**Getting Started**:
1. Study existing PyPI packages for examples
2. Create basic package structure
3. Test installation in virtual environments
4. Implement configuration file handling

### 📦 Packaging & Companion Integrations

**Current Needs**:
- Improve packaging and installation paths
- Keep external companion tools on the `--write-state` / `--once --output json` protocol
- Document status bar, tray, and dashboard integrations without bundling them into the core package
- Test cross-platform data discovery and terminal behavior

**Skills Helpful**:
- Docker containerization
- Python packaging
- Cross-platform CLI testing
- Status bar, menu bar, and dashboard integrations

**Getting Started**:
1. Read the state protocol examples in `README.md`
2. Verify the feature against current `claude-monitor --help`
3. Keep companion UI code separate from the core Python package unless discussed first
4. Include docs and tests for any new public option

### 🔧 Core Features & Bug Fixes

**Current Needs**:
- Improve error handling
- Add more configuration options
- Optimize performance
- Fix cross-platform issues

**Skills Helpful**:
- Python development
- Terminal/console applications
- Cross-platform compatibility
- Performance optimization

**Getting Started**:
1. Run the monitor on different platforms
2. Identify and fix platform-specific issues
3. Improve error messages and handling
4. Add new configuration options

---

## 🐛 Bug Reports

### 📋 Before Submitting a Bug Report

1. **Check existing issues**: Search GitHub issues for similar problems
2. **Update to latest version**: Ensure you're using the latest code
3. **Test in clean environment**: Try in fresh virtual environment
4. **Gather information**: Collect system details and error messages

### 📝 Bug Report Template

```markdown
**Bug Description**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Run command '...'
2. Configure with '...'
3. See error

**Expected Behavior**
What you expected to happen.

**Actual Behavior**
What actually happened.

**Environment**
- OS: [e.g. Ubuntu 20.04, Windows 11, macOS 12]
- Python version: [e.g. 3.9.7]
- claude-monitor version: [run: claude-monitor --version]
- Commit hash: [run: git rev-parse --short HEAD]

**Error Output**
```
Paste full error messages here
```

**Additional Context**
Add any other context about the problem here.
```

---

## 💡 Feature Requests

### 🎯 Feature Request Template

```markdown
**Feature Description**
A clear description of the feature you'd like to see.

**Problem Statement**
What problem does this feature solve?

**Proposed Solution**
How do you envision this feature working?

**Alternative Solutions**
Any alternative approaches you've considered.

**Use Cases**
Specific scenarios where this feature would be helpful.

**Implementation Ideas**
Any ideas about how this could be implemented (optional).
```

### 🔍 Feature Evaluation Criteria

We evaluate features based on:

1. **User Value**: How many users would benefit?
2. **Complexity**: Implementation effort required
3. **Maintenance**: Long-term maintenance burden
4. **Compatibility**: Impact on existing functionality
5. **Performance**: Effect on monitor performance
6. **Dependencies**: Additional dependencies required

---

## 🧪 Testing Contributions

### 🔧 Running Tests

```bash
# Run all tests
uv run --extra test pytest

# Run specific test file
uv run --extra test pytest src/tests/test_settings.py

# Run with coverage
uv run --extra test pytest --cov=claude_monitor

# Collect tests without enforcing coverage
uv run --extra test pytest --collect-only -q --no-cov
```

### 📊 Test Coverage

The default pytest configuration enforces a project coverage gate. For focused local work, run the relevant test file first, then run the full suite before opening a PR.

### 🌍 Platform Testing

Help us test on different platforms:

- **Linux**: Ubuntu, Fedora, Arch, Debian
- **macOS**: Intel and Apple Silicon Macs
- **Windows**: Windows 10/11, different Python installations
- **Python versions**: 3.9, 3.10, 3.11, 3.12, 3.13

---

## 📝 Documentation Contributions

### 📚 Documentation Areas

- **README improvements**: Make getting started easier
- **Code comments**: Explain complex algorithms
- **Usage examples**: Real-world scenarios
- **API documentation**: Function and class documentation
- **Troubleshooting guides**: Common problems and solutions

### ✍️ Writing Guidelines

- **Be clear and concise**: Avoid jargon when possible
- **Use examples**: Show don't just tell
- **Consider all users**: From beginners to advanced
- **Keep it updated**: Ensure examples work with current code
- **Use consistent formatting**: Follow existing style

---

## 📊 Data Collection for Improvement

### 🔍 Help Us Improve Token Limit Detection

We're collecting **anonymized data** about token limits to improve auto-detection:

**What to share in a GitHub issue**:
- Your subscription type (Pro, Teams, Enterprise)
- Whether the number came from official statusline data or local estimates
- Any explicit custom token limit you configured
- When the limit was exceeded
- Usage patterns you've noticed

**Privacy**: Only share what you're comfortable with. No personal information needed.

### 📈 Usage Pattern Research

Help us understand usage patterns:
- Peak usage times
- Session duration preferences
- Token consumption patterns
- Feature usage statistics

This helps prioritize development and improve user experience.


## 🏆 Recognition

### 📸 Contributor Spotlight

Outstanding contributors will be featured:
- **README acknowledgments**: Credit for major contributions
- **Release notes**: Mention significant contributions
- **Social media**: Share contributor achievements
- **Reference letters**: Happy to provide references for good contributors

### 🎖️ Contribution Levels

- **🌟 First Contribution**: Welcome to the community!
- **🔧 Regular Contributor**: Multiple merged PRs
- **🚀 Core Contributor**: Significant feature development
- **👑 Maintainer**: Ongoing project stewardship


## ❓ Getting Help

### 💬 Where to Ask Questions

1. **GitHub Issues**: For bug reports and feature requests
2. **GitHub Discussions**: For general questions and ideas
3. **Email**: [maciek@roboblog.eu](mailto:maciek@roboblog.eu) for direct contact
4. **Code Review**: Ask questions in PR comments

### 📚 Resources

- **[DEVELOPMENT.md](DEVELOPMENT.md)**: Development roadmap
- **[README.md](README.md)**: Installation, usage, and features
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)**: Common issues

---

## 📜 Code of Conduct

### 🤝 Our Standards

- **Be respectful**: Treat everyone with respect and kindness
- **Be inclusive**: Welcome contributors of all backgrounds
- **Be constructive**: Provide helpful feedback and suggestions
- **Be patient**: Remember everyone is learning
- **Be professional**: Keep interactions focused on the project

### 🚫 Unacceptable Behavior

- Harassment or discriminatory language
- Personal attacks or trolling
- Spam or off-topic discussions
- Sharing private information without permission

### 📞 Reporting Issues

If you experience unacceptable behavior, contact: [maciek@roboblog.eu](mailto:maciek@roboblog.eu)

---

## 🎉 Thank You!

Thank you for considering contributing to Claude Code Usage Monitor! Every contribution, no matter how small, helps make this tool better for the entire community.

**Ready to get started?**

1. 🍴 Fork the repository
2. 💻 Set up your development environment
3. 🔍 Look at open issues for ideas
4. 🚀 Start coding!

We can't wait to see what you'll contribute! 🚀
