# Release Process

This document describes the release process for Claude Code Usage Monitor.

## Automated Release (GitHub Actions)

Releases are automatically triggered when changes are pushed to the `main` branch. The GitHub Actions workflow will:

1. Extract the version from `pyproject.toml`
2. Check if a git tag for this version already exists
3. If not, it will:
   - Create a new git tag
   - Extract release notes from `CHANGELOG.md`
   - Create a GitHub release
   - Build and publish the package to PyPI

### Prerequisites for Automated Release

1. **PyPI API Token**: Must be configured as a GitHub secret named `PYPI_API_TOKEN`
   - Generate at: https://pypi.org/manage/account/token/
   - Add to repository secrets: Settings → Secrets and variables → Actions → New repository secret

2. **Publishing Permissions**: Ensure GitHub Actions has permissions to create releases
   - Settings → Actions → General → Workflow permissions → Read and write permissions

## Manual Release Process

If automated release fails or for special cases, follow these steps:

### 1. Prepare Release

```bash
# Ensure you're on main branch with latest changes
git checkout main
git pull origin main

# Run tests and linting
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
```

### 2. Update Version

Edit `pyproject.toml` and update the version:
```toml
version = "1.0.9"  # Update to your new version
```

### 3. Update CHANGELOG.md

Add a new section at the top of `CHANGELOG.md`:
```markdown
## [1.0.9] - 2025-06-21

### Added
- Description of new features

### Changed
- Description of changes

### Fixed
- Description of fixes

[1.0.9]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v1.0.9
```

### 4. Commit Version Changes

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "Bump version to 1.0.9"
git push origin main
```

### 5. Create Git Tag

```bash
# Create annotated tag
git tag -a v1.0.9 -m "Release v1.0.9"

# Push tag to GitHub
git push origin v1.0.9
```

### 6. Build Package

```bash
# Clean previous builds
rm -rf dist/

# Build with uv
uv build

# Verify build artifacts
ls -la dist/
# Should show:
# - claude_monitor-1.0.9-py3-none-any.whl
# - claude_monitor-1.0.9.tar.gz
```

### 7. Create GitHub Release

1. Go to: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/new
2. Choose tag: `v1.0.9`
3. Release title: `Release v1.0.9`
4. Copy the relevant section from CHANGELOG.md to the description
5. Attach the built artifacts from `dist/` (optional)
6. Click "Publish release"

### 8. Publish to PyPI

```bash
# Install twine if needed
uv tool install twine

# Upload to PyPI (will prompt for credentials)
uv tool run twine upload dist/*

# Or with API token
uv tool run twine upload dist/* --username __token__ --password <your-pypi-token>
```

### 9. Verify Release

1. Check PyPI: https://pypi.org/project/claude-monitor/
2. Test installation:
   ```bash
   # In a new environment
   uv tool install claude-monitor
   claude-monitor --version

   # Test all command aliases
   cmonitor --version
   ccm --version
   ```

## Version Numbering

We follow semantic versioning (SemVer):
- **MAJOR.MINOR.PATCH** (e.g., 1.0.9)
- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality in a backward-compatible manner
- **PATCH**: Backward-compatible bug fixes

## Troubleshooting

### GitHub Actions Release Failed

1. Check Actions tab for error logs
2. Common issues:
   - Missing or invalid `PYPI_API_TOKEN`
   - Version already exists on PyPI
   - Malformed CHANGELOG.md

### PyPI Upload Failed

1. **Authentication Error**: Check your PyPI token
2. **Version Exists**: Version numbers cannot be reused on PyPI
3. **Package Name Taken**: The package name might be reserved

### Tag Already Exists

```bash
# Delete local tag
git tag -d v1.0.9

# Delete remote tag
git push --delete origin v1.0.9

# Recreate tag
git tag -a v1.0.9 -m "Release v1.0.9"
git push origin v1.0.9
```

## Release Checklist

- [ ] All tests pass
- [ ] Code is properly formatted (ruff)
- [ ] Version updated in `pyproject.toml`
- [ ] CHANGELOG.md updated with release notes
- [ ] Changes committed and pushed to main
- [ ] Git tag created and pushed
- [ ] GitHub release created
- [ ] Package published to PyPI
- [ ] Installation tested in clean environment
