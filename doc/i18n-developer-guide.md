# 🌍 Internationalization (i18n) Developer Guide

This comprehensive guide explains how to work with translations in Claude Code Usage Monitor, add new text, and contribute support for additional languages.

## 📋 Table of Contents

- [🎯 Overview](#-overview)
- [🏗️ Architecture](#️-architecture)
- [➕ Adding New Text](#-adding-new-text)
- [🌐 Adding New Languages](#-adding-new-languages)
- [🔧 Development Workflow](#-development-workflow)
- [🧪 Testing Translations](#-testing-translations)
- [🛠️ Tools and Scripts](#️-tools-and-scripts)
- [❗ Troubleshooting](#-troubleshooting)
- [🤝 Contributing](#-contributing)

---

## 🎯 Overview

The Claude Code Usage Monitor uses a modern, key-based internationalization system that:

- **✅ Avoids hardcoded strings** - All user-facing text uses translation keys
- **🔄 Supports automatic locale detection** - Adapts to user's system language
- **🎨 Maintains consistency** - Centralized message management
- **🚀 Easy to extend** - Simple workflow for adding new languages

### Current Language Support

| Language | Code | Status | Coverage |
|----------|------|--------|----------|
| **English** | `en_US` | ✅ Complete | 100% (Default) |
| **French** | `fr_FR` | ✅ Complete | 100% |

---

## 🏗️ Architecture

### Directory Structure

```text
usage_analyzer/
├── i18n/
│   ├── __init__.py              # Translation system core
│   └── message_keys.py          # Centralized translation keys
├── locales/
│   ├── en/
│   │   └── LC_MESSAGES/
│   │       ├── claude_monitor.po # English translations (source)
│   │       └── claude_monitor.mo # Compiled translations
│   └── fr/
│       └── LC_MESSAGES/
│           ├── claude_monitor.po # French translations
│           └── claude_monitor.mo # Compiled translations
```

### Key Components

#### 1. Message Keys (`message_keys.py`)
Central registry for all translation keys organized by functionality:

```python
class UI:
    """Main user interface messages."""
    HEADER_TITLE = "ui.header.title"
    LOADING_MESSAGE = "ui.loading.message"
    # ... more keys

class STATUS:
    """Status messages and performance indicators."""
    TOKEN_USAGE = "status.token_usage"
    BURN_RATE = "status.burn_rate"
    # ... more keys

class ERROR:
    """Error messages and technical issues."""
    DATA_FETCH_FAILED = "error.data_fetch_failed"
    NOT_LOGGED_IN = "error.not_logged_in"
    # ... more keys
```

#### 2. Translation System (`__init__.py`)
Handles locale detection, translation loading, and fallbacks:

```python
from usage_analyzer.i18n import _, init_translations

# Initialize translations (auto-detects or uses specified locale)
init_translations()  # Auto-detect
init_translations("fr_FR")  # Force French

# Use translations in code
from usage_analyzer.i18n.message_keys import UI
print(_(UI.HEADER_TITLE))  # Outputs translated text
```

#### 3. Locale Files (`.po` and `.mo`)
- **`.po` files**: Human-readable translation files (edited by translators)
- **`.mo` files**: Compiled binary files (used by the application)

---

## ➕ Adding New Text

When you need to add new user-facing text to the application:

### Step 1: Add Translation Key

Add your new key to the appropriate class in `message_keys.py`:

```python
class UI:
    """Main user interface messages."""
    HEADER_TITLE = "ui.header.title"
    LOADING_MESSAGE = "ui.loading.message"
    # 👇 ADD YOUR NEW KEY HERE
    NEW_FEATURE_BUTTON = "ui.new_feature.button"
    NEW_FEATURE_TOOLTIP = "ui.new_feature.tooltip"
```

**Key Naming Convention:**
- Use descriptive, hierarchical names: `category.subcategory.element`
- Use snake_case for Python constants
- Use dot notation for the actual key strings
- Examples:
  - `UI.SAVE_BUTTON = "ui.save.button"`
  - `ERROR.NETWORK_TIMEOUT = "error.network.timeout"`
  - `STATUS.PROGRESS_COMPLETE = "status.progress.complete"`

### Step 2: Update ALL_MESSAGE_KEYS

At the end of `message_keys.py`, add your new keys to the registry:

```python
# Export all message keys for extraction
ALL_MESSAGE_KEYS = {
    # UI Messages
    UI.HEADER_TITLE,
    UI.LOADING_MESSAGE,
    UI.NEW_FEATURE_BUTTON,        # 👈 Add here
    UI.NEW_FEATURE_TOOLTIP,       # 👈 Add here
    
    # Status Messages
    STATUS.TOKEN_USAGE,
    # ... existing keys
    
    # Error Messages
    ERROR.DATA_FETCH_FAILED,
    # ... existing keys
}
```

### Step 3: Use in Your Code

Import and use the translation function:

```python
from usage_analyzer.i18n import _
from usage_analyzer.i18n.message_keys import UI

# In your code:
button_text = _(UI.NEW_FEATURE_BUTTON)
tooltip_text = _(UI.NEW_FEATURE_TOOLTIP)

# Or directly in console output:
console.print(_(UI.NEW_FEATURE_BUTTON), style="bold blue")
```

### Step 4: Update Translation Files

Run the update script to extract new keys:

```bash
# PowerShell (Windows)
.\scripts\update_translations.ps1

# Bash (Linux/macOS)
./scripts/update_translations.sh
```

### Step 5: Add Translations

Edit the `.po` files to add translations for your new keys:

**English (`locales/en/LC_MESSAGES/claude_monitor.po`):**
```po
msgid "ui.new_feature.button"
msgstr "New Feature"

msgid "ui.new_feature.tooltip"
msgstr "Click to access the new feature"
```

**French (`locales/fr/LC_MESSAGES/claude_monitor.po`):**
```po
msgid "ui.new_feature.button"
msgstr "Nouvelle Fonctionnalité"

msgid "ui.new_feature.tooltip"
msgstr "Cliquez pour accéder à la nouvelle fonctionnalité"
```

### Step 6: Compile and Test

```bash
# Compile translations
.\scripts\update_translations.ps1

# Test in different languages
python claude_monitor.py --language en
python claude_monitor.py --language fr
```

---

## 🌐 Adding New Languages

Want to add support for a new language? Here's the complete workflow:

### Step 1: Create Locale Directory

```bash
# Example: Adding Spanish (es_ES)
mkdir -p usage_analyzer/locales/es/LC_MESSAGES
```

### Step 2: Generate Translation Template

Create the `.po` file for your new language:

```bash
# Copy English as template
cp usage_analyzer/locales/en/LC_MESSAGES/claude_monitor.po \
   usage_analyzer/locales/es/LC_MESSAGES/claude_monitor.po
```

### Step 3: Update Locale Detection

Add your language to the detection system in `i18n/__init__.py`:

```python
# Language mapping for locale detection
LANGUAGE_MAPPING = {
    'fr': 'fr_FR',    # French
    'fr_FR': 'fr_FR',
    'fr_CA': 'fr_FR', # French Canadian → French
    'en': 'en_US',    # English
    'en_US': 'en_US',
    'en_GB': 'en_US', # British English → US English
    # 👇 ADD YOUR NEW LANGUAGE
    'es': 'es_ES',    # Spanish
    'es_ES': 'es_ES',
    'es_MX': 'es_ES', # Mexican Spanish → Spanish
}
```

### Step 4: Translate Messages

Edit `usage_analyzer/locales/es/LC_MESSAGES/claude_monitor.po`:

```po
# Spanish translations
msgid "ui.header.title"
msgstr "MONITOR DE USO DE CLAUDE"

msgid "ui.loading.message"
msgstr "Obteniendo datos de uso de Claude..."

msgid "status.token_usage"
msgstr "Uso de Tokens"

msgid "status.burn_rate"
msgstr "Velocidad de Consumo"

# ... continue with all messages
```

**Translation Guidelines:**
- Keep the technical meaning intact
- Adapt to local conventions (date/time formats, etc.)
- Maintain consistent terminology throughout
- Consider text length (some languages are longer/shorter)
- Test with actual native speakers when possible

### Step 5: Add CLI Support

Update the argument parser in `claude_monitor.py`:

```python
parser.add_argument(
    "--language",
    type=str,
    choices=["en", "fr", "es", "auto"],  # 👈 Add "es"
    help="Language for the interface (auto-detects if not specified)"
)
```

### Step 6: Update Documentation

Add your language to the documentation:

**README.md:**
```markdown
#### Language Configuration

Configure your preferred language for the interface:

```bash
# English interface  
claude-monitor --language en

# French interface
claude-monitor --language fr

# Spanish interface
claude-monitor --language es

# Auto-detect from system (default)
claude-monitor --language auto
```
```

**This guide (`i18n-developer-guide.md`):**
```markdown
| Language | Code | Status | Coverage |
|----------|------|--------|----------|
| **English** | `en_US` | ✅ Complete | 100% (Default) |
| **French** | `fr_FR` | ✅ Complete | 100% |
| **Spanish** | `es_ES` | ✅ Complete | 100% |
| **German**  | `de_DE` | ✅ Complete | 100% |
```

### Step 7: Compile and Test

```bash
# Compile new translations
.\scripts\update_translations.ps1

# Test the new language
python claude_monitor.py --language es

# Test auto-detection (set system locale to Spanish)
export LANG=es_ES.UTF-8  # Linux/macOS
$env:LANG = "es_ES.UTF-8"  # PowerShell
python claude_monitor.py --language auto
```

### Step 8: Update Scripts

Modify `scripts/update_translations.ps1` to handle your new language:

```powershell
# Add compilation for your language
Write-Info "2. Compilation des traductions..."

$Languages = @("fr", "es")  # 👈 Add "es"

foreach ($Language in $Languages) {
    $CompileScript = @"
from babel.messages.pofile import read_po
from babel.messages.mofile import write_mo
import os

po_file = r'$LocaleDir\$Language\LC_MESSAGES\claude_monitor.po'
mo_file = r'$LocaleDir\$Language\LC_MESSAGES\claude_monitor.mo'

if os.path.exists(po_file):
    try:
        with open(po_file, 'rb') as f:
            catalog = read_po(f)
        
        with open(mo_file, 'wb') as f:
            write_mo(f, catalog)
        
        print(f'$Language: {len(catalog)} messages compiled')
    except Exception as e:
        print(f'Error compiling $Language: {e}')
        exit(1)
else:
    print(f'File {po_file} not found')
    exit(1)
"@

    try {
        $CompileOutput = python -c $CompileScript
        Write-Success $CompileOutput
    }
    catch {
        Write-Error "Error compiling $Language: $_"
        exit 1
    }
}
```

---

## 🔧 Development Workflow

### Daily Development

When working on features that involve user-facing text:

1. **Plan your messages**: Think about what text you'll need before coding
2. **Add keys first**: Define translation keys in `message_keys.py`
3. **Code with keys**: Use `_(KEY)` instead of hardcoded strings
4. **Update translations**: Run update script regularly
5. **Test both languages**: Always test EN and FR (minimum)

### Example Workflow

```bash
# 1. Start development
git checkout -b feature/new-dashboard

# 2. Add your translation keys to message_keys.py
# (Edit the file, add your keys)

# 3. Code your feature using translation keys
# Instead of: print("Dashboard loaded")
# Use: print(_(UI.DASHBOARD_LOADED))

# 4. Update translations
.\scripts\update_translations.ps1

# 5. Add translations for new keys
# Edit .po files to add translations

# 6. Recompile
.\scripts\update_translations.ps1

# 7. Test
python claude_monitor.py --language en
python claude_monitor.py --language fr

# 8. Commit changes
git add .
git commit -m "Add: Dashboard feature with i18n support"
```

### Branch Strategy for i18n

**For new features:**
- Include translation keys in the feature branch
- Add at least English translations
- Leave TODO comments for missing translations

**For translation updates:**
- Create separate branches for new language support
- Focus on translation quality and completeness
- Include native speaker reviews when possible

---

## 🧪 Testing Translations

### Automated Testing

The project includes automated translation tests:

```bash
# Run i18n-specific tests
python -m pytest test_i18n_simple.py
python -m pytest test_i18n_system.py
python -m pytest test_integration_i18n.py

# Run all tests
python -m pytest
```

### Manual Testing

#### Test All Languages

```bash
# Test each supported language
python claude_monitor.py --language en
python claude_monitor.py --language fr
python claude_monitor.py --language es  # If you added Spanish

# Test auto-detection
python claude_monitor.py --language auto
```

#### Test Edge Cases

```bash
# Test with invalid language (should fallback to English)
python claude_monitor.py --language xx

# Test with partial translations (some keys missing)
# This helps identify missing translations

# Test with different system locales
export LANG=fr_FR.UTF-8
python claude_monitor.py --language auto

export LANG=en_US.UTF-8
python claude_monitor.py --language auto
```

#### Visual Testing Checklist

When testing translations:

- [ ] **All text is translated** (no English mixed with other languages)
- [ ] **Layout isn't broken** (longer/shorter text doesn't break UI)
- [ ] **Characters display correctly** (accents, special characters)
- [ ] **Consistency** (same terms used throughout)
- [ ] **Context makes sense** (translations fit the situation)
- [ ] **Error messages work** (technical errors are understandable)

### Translation Quality Checklist

For each new translation:

- [ ] **Accuracy**: Technical meaning preserved
- [ ] **Clarity**: Easy to understand for target audience
- [ ] **Consistency**: Same terms used throughout
- [ ] **Cultural adaptation**: Follows local conventions
- [ ] **Length consideration**: Text fits UI layouts
- [ ] **Tone**: Matches application's tone (professional but friendly)

---

## 🛠️ Tools and Scripts

### Available Scripts

#### `scripts/update_translations.ps1` (PowerShell)

**Purpose**: Complete translation workflow automation

**What it does**:
1. Extracts all translation keys from `message_keys.py`
2. Compiles `.po` files to `.mo` files for all languages
3. Tests that translations load correctly
4. Provides status feedback

**Usage**:
```powershell
# Run from project root
.\scripts\update_translations.ps1
```

**Output example**:
```text
ℹ️  Mise à jour des traductions Claude Usage Monitor
ℹ️  1. Extraction des chaînes traduisibles...
✅ Extraction réussie: 45 messages
ℹ️  2. Compilation des traductions françaises...
✅ Compilation réussie: 45 messages
ℹ️  3. Test rapide du système...
✅ Test français: ✅ OK
✅ Test anglais: ✅ Claude Code Usage Monitor
🎉 Mise à jour des traductions terminée avec succès!
```

#### `scripts/update_translations.sh` (Bash)

**Purpose**: Same as PowerShell version but for Linux/macOS

**Usage**:
```bash
# Make executable first time
chmod +x scripts/update_translations.sh

# Run from project root
./scripts/update_translations.sh
```

### Manual Tools

#### Extracting Keys
```bash
# Extract all translation keys programmatically
python -c "
from usage_analyzer.i18n.message_keys import ALL_MESSAGE_KEYS
for key in sorted(ALL_MESSAGE_KEYS):
    print(f'msgid \"{key}\"')
    print('msgstr \"\"')
    print()
"
```

#### Compiling Translations
```python
# Compile .po to .mo manually
from babel.messages.pofile import read_po
from babel.messages.mofile import write_mo

# For each language
with open('usage_analyzer/locales/fr/LC_MESSAGES/claude_monitor.po', 'rb') as f:
    catalog = read_po(f)

with open('usage_analyzer/locales/fr/LC_MESSAGES/claude_monitor.mo', 'wb') as f:
    write_mo(f, catalog)
```

#### Testing Translation Loading
```python
# Test translation system manually
from usage_analyzer.i18n import init_translations, _
from usage_analyzer.i18n.message_keys import UI

# Test French
init_translations('fr_FR')
print(f"French: {_(UI.HEADER_TITLE)}")

# Test English
init_translations('en_US')
print(f"English: {_(UI.HEADER_TITLE)}")
```

### External Tools

For professional translation projects, consider:

- **Poedit**: GUI editor for `.po` files
- **Weblate**: Web-based translation platform
- **GNU gettext**: Command-line tools (`msgfmt`, `msgmerge`, etc.)
- **Babel**: Python internationalization library

---

## ❗ Troubleshooting

### Common Issues and Solutions

#### 1. Translation Not Showing

**Symptoms**: Interface shows English despite setting different language

**Possible Causes**:
- `.mo` file not compiled or corrupted
- Translation key missing from `.po` file
- Locale not properly detected

**Solutions**:
```bash
# Recompile translations
.\scripts\update_translations.ps1

# Check if .mo file exists and is recent
ls -la usage_analyzer/locales/fr/LC_MESSAGES/

# Test specific translation
python -c "
from usage_analyzer.i18n import init_translations, _
init_translations('fr_FR')
print(_('ui.header.title'))
"

# Enable debug mode
python claude_monitor.py --language fr --verbose
```

#### 2. Character Encoding Issues

**Symptoms**: Accented characters show as `�` or weird symbols

**Solutions**:
```bash
# Ensure UTF-8 encoding
export LC_ALL=fr_FR.UTF-8

# Windows: Set code page to UTF-8
chcp 65001

# Check .po file encoding (should start with)
head -5 usage_analyzer/locales/fr/LC_MESSAGES/claude_monitor.po
# Should show: "Content-Type: text/plain; charset=UTF-8\n"
```

#### 3. New Keys Not Extracted

**Symptoms**: Added new keys, but they don't appear in translations

**Solutions**:
```bash
# Check that key is in ALL_MESSAGE_KEYS
python -c "
from usage_analyzer.i18n.message_keys import ALL_MESSAGE_KEYS
print('ui.your.new.key' in ALL_MESSAGE_KEYS)
"

# Re-run extraction
.\scripts\update_translations.ps1

# Manually check .po file
grep "ui.your.new.key" usage_analyzer/locales/*/LC_MESSAGES/claude_monitor.po
```

#### 4. Compilation Errors

**Symptoms**: Script fails during `.mo` file compilation

**Common Issues**:
- Syntax errors in `.po` file
- Missing dependencies (`babel` package)
- File permissions

**Solutions**:
```bash
# Install babel if missing
pip install babel

# Check .po file syntax
python -c "
from babel.messages.pofile import read_po
with open('usage_analyzer/locales/fr/LC_MESSAGES/claude_monitor.po', 'rb') as f:
    catalog = read_po(f)
print('File is valid')
"

# Check permissions
ls -la usage_analyzer/locales/fr/LC_MESSAGES/
```

#### 5. Auto-Detection Not Working

**Symptoms**: `--language auto` always defaults to English

**Debug Steps**:
```bash
# Check system locale
echo $LANG
locale

# Test detection manually
python -c "
from usage_analyzer.i18n import get_system_locale
print(f'Detected: {get_system_locale()}')
"

# Force locale temporarily
export LANG=fr_FR.UTF-8
python claude_monitor.py --language auto
```

### Debug Mode

Enable verbose logging to troubleshoot translation issues:

```python
# Add to your development code
import logging
logging.basicConfig(level=logging.DEBUG)

from usage_analyzer.i18n import init_translations
init_translations()  # Will show debug info
```

### Validation Scripts

Create validation scripts for translation quality:

```python
#!/usr/bin/env python3
"""Validate translation completeness."""

from usage_analyzer.i18n.message_keys import ALL_MESSAGE_KEYS
from babel.messages.pofile import read_po

def validate_language(lang_code):
    po_file = f'usage_analyzer/locales/{lang_code}/LC_MESSAGES/claude_monitor.po'
    
    try:
        with open(po_file, 'rb') as f:
            catalog = read_po(f)
        
        translated = 0
        missing = []
        
        for key in ALL_MESSAGE_KEYS:
            message = catalog.get(key)
            if message and message.string:
                translated += 1
            else:
                missing.append(key)
        
        total = len(ALL_MESSAGE_KEYS)
        percentage = (translated / total) * 100
        
        print(f"Language: {lang_code}")
        print(f"Translated: {translated}/{total} ({percentage:.1f}%)")
        
        if missing:
            print("Missing translations:")
            for key in missing:
                print(f"  - {key}")
        
        return missing
        
    except Exception as e:
        print(f"Error validating {lang_code}: {e}")
        return None

# Run validation
for lang in ['en', 'fr']:
    validate_language(lang)
    print()
```

---

## 🤝 Contributing

### For Developers

When contributing code changes:

1. **Always use translation keys** for user-facing text
2. **Update `message_keys.py`** before writing code
3. **Test in multiple languages** before submitting PR
4. **Document new keys** in commit messages
5. **Follow naming conventions** for translation keys

### For Translators

When contributing translations:

1. **Fork the repository** and create a language branch
2. **Follow the workflow** described in "Adding New Languages"
3. **Test translations** thoroughly in the actual application
4. **Consider cultural context** not just literal translation
5. **Provide context** if certain terms need explanation

### Translation Review Process

For new languages or major translation updates:

1. **Initial translation** by contributor
2. **Technical review** by maintainer (compilation, integration)
3. **Native speaker review** (if different from contributor)
4. **User testing** with actual users
5. **Feedback incorporation** and finalization

### Pull Request Checklist

For i18n-related contributions:

- [ ] Translation keys added to `message_keys.py`
- [ ] All new keys added to `ALL_MESSAGE_KEYS`
- [ ] Translation files updated (`.po` files)
- [ ] Compilation successful (`.mo` files generated)
- [ ] Manual testing in relevant languages
- [ ] Automated tests pass
- [ ] Documentation updated if needed
- [ ] No hardcoded strings in code

### Getting Help

- **Questions about i18n system**: Create GitHub issue with `i18n` label
- **Translation help needed**: Contact current translators in issues
- **Technical integration**: See main [CONTRIBUTING.md](../CONTRIBUTING.md)

---

## 📚 Additional Resources

### Related Documentation

- **[Locale Detection Guide](locale-detection.md)**: Detailed info on automatic language detection
- **[CONTRIBUTING.md](../CONTRIBUTING.md)**: General contribution guidelines
- **[TROUBLESHOOTING.md](../TROUBLESHOOTING.md)**: General troubleshooting

### External Resources

- **[GNU gettext manual](https://www.gnu.org/software/gettext/manual/gettext.html)**: Comprehensive gettext guide
- **[Babel documentation](https://babel.pocoo.org/)**: Python internationalization library
- **[Unicode normalization](https://unicode.org/reports/tr15/)**: Character encoding best practices
- **[Locale codes (ISO 639)](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)**: Standard language codes

### Tools Documentation

- **[Poedit](https://poedit.net/)**: Popular .po file editor
- **[Weblate](https://weblate.org/)**: Collaborative translation platform
- **[OmegaT](https://omegat.org/)**: Free translation memory tool

---

## Happy translating! 🌍✨

> This guide is a living document. Please contribute improvements and updates as the i18n system evolves!
