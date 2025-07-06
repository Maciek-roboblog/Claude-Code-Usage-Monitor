#!/usr/bin/env python3
"""
Validation script for i18n system.
Checks translation completeness, compilation status, and system integration.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from babel.messages.pofile import read_po

    from usage_analyzer.i18n import _, init_translations
    from usage_analyzer.i18n.message_keys import ALL_MESSAGE_KEYS
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure to install dependencies: pip install babel")
    sys.exit(1)


def check_message_keys():
    """Validate message keys structure."""
    print("🔍 Checking message keys...")

    # Check if ALL_MESSAGE_KEYS exists and is not empty
    if not ALL_MESSAGE_KEYS:
        print("❌ ALL_MESSAGE_KEYS is empty or not defined")
        return False

    print(f"✅ Found {len(ALL_MESSAGE_KEYS)} translation keys")

    # Check key format
    invalid_keys = []
    for key in ALL_MESSAGE_KEYS:
        if not isinstance(key, str) or "." not in key:
            invalid_keys.append(key)

    if invalid_keys:
        print(f"❌ Invalid key format: {invalid_keys}")
        return False

    print("✅ All keys have valid format")
    return True


def check_po_files():
    """Check .po files for all languages."""
    print("\n📄 Checking .po files...")

    locales_dir = project_root / "usage_analyzer" / "locales"
    languages = []

    for lang_dir in locales_dir.iterdir():
        if lang_dir.is_dir():
            po_file = lang_dir / "LC_MESSAGES" / "claude_monitor.po"
            if po_file.exists():
                languages.append(lang_dir.name)

    if not languages:
        print("❌ No .po files found")
        return False

    print(f"✅ Found languages: {', '.join(languages)}")

    # Validate each .po file
    for lang in languages:
        po_file = locales_dir / lang / "LC_MESSAGES" / "claude_monitor.po"
        try:
            with open(po_file, "rb") as f:
                catalog = read_po(f)

            # Count translations
            translated = sum(1 for msg in catalog if msg.string)
            total = len(catalog)
            percentage = (translated / total * 100) if total > 0 else 0
            print(f"  📊 {lang}: {translated}/{total} messages ({percentage:.1f}%)")

        except Exception as e:
            print(f"❌ Error reading {lang}.po: {e}")
            return False

    return True


def check_mo_files():
    """Check .mo files compilation."""
    print("\n⚙️  Checking .mo files...")

    locales_dir = project_root / "usage_analyzer" / "locales"
    compiled_languages = []

    for lang_dir in locales_dir.iterdir():
        if lang_dir.is_dir():
            mo_file = lang_dir / "LC_MESSAGES" / "claude_monitor.mo"
            po_file = lang_dir / "LC_MESSAGES" / "claude_monitor.po"

            if mo_file.exists() and po_file.exists():
                # Check if .mo is newer than .po
                mo_time = mo_file.stat().st_mtime
                po_time = po_file.stat().st_mtime

                if mo_time >= po_time:
                    compiled_languages.append(lang_dir.name)
                    print(f"✅ {lang_dir.name}: .mo file is up to date")
                else:
                    print(
                        f"⚠️  {lang_dir.name}: .mo file is older than .po "
                        f"(needs recompilation)"
                    )
            else:
                if po_file.exists():
                    print(f"❌ {lang_dir.name}: .po exists but .mo missing")

    return len(compiled_languages) > 0


def test_translation_system():
    """Test the translation system integration."""
    print("\n🧪 Testing translation system...")

    # Test English (fallback)
    try:
        init_translations("en_US")
        from usage_analyzer.i18n.message_keys import UI

        result = _(UI.HEADER_TITLE)
        if result and not result.startswith("MISSING"):
            print("✅ English translations working")
        else:
            print(f"❌ English translation failed: {result}")
            return False
    except Exception as e:
        print(f"❌ English translation error: {e}")
        return False

    # Test other languages
    locales_dir = project_root / "usage_analyzer" / "locales"
    for lang_dir in locales_dir.iterdir():
        if lang_dir.is_dir() and lang_dir.name != "en":
            try:
                # Map folder name to locale
                locale_map = {"fr": "fr_FR", "es": "es_ES", "de": "de_DE"}
                locale = locale_map.get(
                    lang_dir.name, f"{lang_dir.name}_{lang_dir.name.upper()}"
                )

                init_translations(locale)
                result = _(UI.HEADER_TITLE)

                # Check if we got a real translation (not fallback to English)
                if lang_dir.name == "fr":
                    # For French, check if we got the French translation
                    if "MONITEUR" in result:
                        print(f"✅ {lang_dir.name} translations working: '{result}'")
                    else:
                        print(
                            f"⚠️  {lang_dir.name} translations not found "
                            f"(falling back to English)"
                        )
                else:
                    # For other languages, check it's not empty and not MISSING
                    if result and not result.startswith("MISSING"):
                        print(f"✅ {lang_dir.name} translations working: '{result}'")
                    else:
                        print(
                            f"⚠️  {lang_dir.name} translations not found "
                            f"(falling back to English)"
                        )

            except Exception as e:
                print(f"❌ {lang_dir.name} translation error: {e}")

    return True


def check_completeness():
    """Check translation completeness for each language."""
    print("\n📊 Checking translation completeness...")

    locales_dir = project_root / "usage_analyzer" / "locales"

    for lang_dir in locales_dir.iterdir():
        if lang_dir.is_dir():
            po_file = lang_dir / "LC_MESSAGES" / "claude_monitor.po"
            if not po_file.exists():
                continue

            try:
                with open(po_file, "rb") as f:
                    catalog = read_po(f)

                # Check coverage of our message keys
                translated_keys = 0
                missing_keys = []

                for key in ALL_MESSAGE_KEYS:
                    message = catalog.get(key)
                    if message and message.string:
                        translated_keys += 1
                    else:
                        missing_keys.append(key)

                total_keys = len(ALL_MESSAGE_KEYS)
                percentage = (
                    (translated_keys / total_keys * 100) if total_keys > 0 else 0
                )

                print(
                    f"  📈 {lang_dir.name}: {translated_keys}/{total_keys} keys ({percentage:.1f}%)"
                )

                if missing_keys and len(missing_keys) <= 5:
                    print(f"    Missing: {', '.join(missing_keys)}")
                elif missing_keys:
                    print(
                        f"    Missing {len(missing_keys)} keys (first 3: {', '.join(missing_keys[:3])}...)"
                    )

            except Exception as e:
                print(f"❌ Error checking {lang_dir.name}: {e}")


def main():
    """Run all validation checks."""
    print("🌍 Claude Code Usage Monitor - i18n System Validation")
    print("=" * 60)

    checks = [
        ("Message Keys", check_message_keys),
        (".po Files", check_po_files),
        (".mo Files", check_mo_files),
        ("Translation System", test_translation_system),
    ]

    all_passed = True

    for check_name, check_func in checks:
        try:
            result = check_func()
            if not result:
                all_passed = False
        except Exception as e:
            print(f"❌ {check_name} check failed with error: {e}")
            all_passed = False

    # Additional detailed check
    check_completeness()

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All i18n system checks passed!")
        print("\n💡 To update translations, run:")
        print("   Windows: .\\scripts\\update_translations.ps1")
        print("   Linux/macOS: ./scripts/update_translations.sh")
    else:
        print("❌ Some checks failed. Please review the output above.")
        print("\n🔧 Common fixes:")
        print("   - Run: pip install babel")
        print("   - Recompile: .\\scripts\\update_translations.ps1")
        print("   - Check .po file syntax")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
