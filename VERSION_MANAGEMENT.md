# Version Management System

## Overview

The Claude Code Usage Monitor uses a centralized version management system that eliminates version duplication and ensures consistency across the entire codebase.

## Single Source of Truth

**`pyproject.toml`** is the **only** place where the version number is defined:

```toml
[project]
version = "3.0.0"
```

## How It Works

### 1. Version Detection (`src/claude_monitor/_version.py`)

The version is retrieved using a two-tier fallback system:

1. **Primary**: Read from package metadata (when installed)
   ```python
   importlib.metadata.version("claude-monitor")
   ```

2. **Fallback**: Read directly from `pyproject.toml` (development mode)
   ```python
   # Uses tomllib (Python 3.11+) or tomli (Python < 3.11)
   ```

### 2. Module Import (`src/claude_monitor/__init__.py`)

```python
from claude_monitor._version import __version__
```

### 3. Usage Throughout Codebase

All modules import version from the main package:

```python
from claude_monitor import __version__
```

## Benefits

✅ **Single Source of Truth**: Version defined only in `pyproject.toml`
✅ **No Duplication**: Eliminates hardcoded versions in `__init__.py` files
✅ **Automatic Sync**: Version updates automatically propagate everywhere
✅ **Development Support**: Works both in installed and development environments
✅ **Build Integration**: Seamlessly integrates with build and release processes

## Dependencies

- **Python 3.11+**: Uses built-in `tomllib`
- **Python < 3.11**: Uses `tomli>=1.2.0` (automatically installed)

## Testing

Comprehensive test suite in `src/tests/test_version.py`:

- Version import consistency
- Fallback mechanism testing
- Integration with `pyproject.toml`
- Format validation

## Migration

### Before (Problems)
```python
# Multiple version definitions - sync issues!
# src/claude_monitor/__init__.py
__version__ = "2.5.0"

# pyproject.toml
version = "3.0.0"  # Different version!
```

### After (Solution)
```python
# src/claude_monitor/__init__.py
from claude_monitor._version import __version__  # Always in sync!

# pyproject.toml
version = "3.0.0"  # Single source of truth
```

## Release Process

1. **Update version in `pyproject.toml`** only
2. **All other files automatically reflect the new version**
3. **No manual updates needed anywhere else**

## Best Practices

- ✅ Update version only in `pyproject.toml`
- ✅ Use `from claude_monitor import __version__` in all modules
- ❌ Never hardcode version strings in source code
- ❌ Never define `__version__` in `__init__.py` files

This system ensures version consistency and eliminates the maintenance burden of keeping multiple version definitions synchronized.
