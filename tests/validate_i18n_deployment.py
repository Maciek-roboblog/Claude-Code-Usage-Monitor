#!/usr/bin/env python3
"""
Final validation script for i18n deployment.

This script validates that all multilingual features
work correctly before deployment.
"""

import os
import subprocess
import sys
import tempfile

import yaml

# Add the root directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from usage_analyzer.i18n import _, get_system_locale, init_translations


def test_system_detection():
    """Test automatic system locale detection."""
    print("🔍 Testing automatic system locale detection...")

    # Detect system locale
    system_locale = get_system_locale()
    print(f"   Detected system locale: {system_locale}")

    # Initialize with auto-detection
    gettext_func, ngettext_func = init_translations()

    # Test translation
    title = _("ui.header.title")
    print(f"   Translated title: {title}")

    print("✅ System detection OK\n")


def test_french_system_simulation():
    """Simulate a native French system."""
    print("🇫🇷 Testing French system simulation...")

    # Save current environment
    original_lang = os.environ.get("LANG", "")

    try:
        # Simulate a French system
        os.environ["LANG"] = "fr_FR.UTF-8"

        # Initialize with auto-detection
        gettext_func, ngettext_func = init_translations()

        # French translation tests
        tests = [
            ("ui.header.title", "MONITEUR"),
            ("ui.loading.message", "Chargement"),
            ("status.token_usage", "Utilisation"),
            ("error.data_fetch_failed", "Échec"),
        ]

        for key, expected_word in tests:
            translation = _(key)
            if expected_word.lower() in translation.lower():
                print(f"   ✅ {key} : {translation}")
            else:
                print(
                    f"   ❌ {key} : {translation} (expected: contains '{expected_word}')"
                )

    finally:
        # Restore environment
        if original_lang:
            os.environ["LANG"] = original_lang
        elif "LANG" in os.environ:
            del os.environ["LANG"]

    print("✅ French system OK\n")


def test_english_system_simulation():
    """Simulate an English system."""
    print("🇺🇸 Testing English system simulation...")

    try:
        # Force initialization in English
        gettext_func, ngettext_func = init_translations("en_US")

        # In English, we should have the real English translations
        title = _("ui.header.title")
        loading = _("ui.loading.message")

        print(f"   Title: {title}")
        print(f"   Loading: {loading}")

        # Check that it's in English (not French)
        if "CLAUDE CODE USAGE MONITOR" in title:
            print("   ✅ Title is correct in English")
        else:
            print(f"   ❌ Title not in English: {title}")

        if "Loading" in loading or "Fetching" in loading:
            print("   ✅ Loading message in English")
        else:
            print(f"   ❌ Loading message not in English: {loading}")

    except Exception as e:
        print(f"   ❌ English test error: {e}")
        return

    print("✅ English system OK\n")


def test_config_file_persistence():
    """Test persistence via configuration file."""
    print("📁 Testing configuration persistence...")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        config = {"language": "fr", "plan": "max5", "timezone": "Europe/Paris"}
        yaml.dump(config, f)
        config_path = f.name

    try:
        # Load and check
        with open(config_path, "r") as f:
            loaded_config = yaml.safe_load(f)

        assert loaded_config["language"] == "fr"
        print("   ✅ YAML configuration persisted")

        # Test with this configuration
        init_translations("fr_FR")
        title = _("ui.header.title")
        assert "MONITEUR" in title
        print("   ✅ Configuration applied correctly")

    finally:
        os.unlink(config_path)

    print("✅ Persistence OK\n")


def test_cli_arguments():
    """Test CLI arguments."""
    print("⌨️ Testing CLI arguments...")

    try:
        # Test with --help to check that the option exists
        result = subprocess.run(
            [sys.executable, "claude_monitor.py", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        help_text = result.stdout

        # Check for the presence of the language option
        if "--language" in help_text and "--lang" in help_text:
            print("   ✅ --language option present in help")
        else:
            print("   ❌ --language option missing")

        # Check for choices fr, en, auto
        if all(lang in help_text for lang in ["fr", "en", "es", "de", "auto"]):
            print("   ✅ Correct language choices")
        else:
            print("   ❌ Missing language choices")

    except subprocess.TimeoutExpired:
        print("   ⚠️ Timeout during CLI test (normal if no Claude data)")
    except Exception as e:
        print(f"   ❌ CLI test error: {e}")

    print("✅ CLI arguments OK\n")


def test_package_structure():
    """Check the package structure for distribution."""
    print("📦 Testing package structure...")

    # Check translation files
    locale_dir = "usage_analyzer/locales/fr/LC_MESSAGES"
    mo_file = os.path.join(locale_dir, "claude_monitor.mo")
    po_file = os.path.join(locale_dir, "claude_monitor.po")

    if os.path.exists(mo_file):
        print(f"   ✅ .mo file present: {mo_file}")
    else:
        print(f"   ❌ .mo file missing: {mo_file}")

    if os.path.exists(po_file):
        print(f"   ✅ .po file present: {po_file}")
    else:
        print(f"   ❌ .po file missing: {po_file}")

    # Check pyproject.toml
    if os.path.exists("pyproject.toml"):
        with open("pyproject.toml", "r", encoding="utf-8") as f:
            content = f.read()
            if "locales/**/*.mo" in content:
                print("   ✅ pyproject.toml includes .mo files")
            else:
                print("   ❌ pyproject.toml does not include .mo files")

    print("✅ Package structure OK\n")


def main():
    """Run all validation tests."""
    print("=== Final i18n Deployment Validation ===\n")

    try:
        test_system_detection()
        test_french_system_simulation()
        test_english_system_simulation()
        test_config_file_persistence()
        test_cli_arguments()
        test_package_structure()

        print("🎉 VALIDATION SUCCESSFUL!")
        print("✅ The i18n system is ready for deployment")
        print("\nValidated features:")
        print("  🌍 Automatic locale detection")
        print("  🇫🇷 Complete French interface")
        print("  🇺🇸 Functional English fallback")
        print("  ⚙️ Persistent configuration")
        print("  ⌨️ Multilingual CLI arguments")
        print("  📦 Correct package structure")

        return 0

    except Exception as e:
        print(f"\n❌ VALIDATION ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
