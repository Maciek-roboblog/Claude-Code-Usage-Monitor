#!/usr/bin/env python3
"""
Generic script to update and compile all translations.
Compatible with all platforms (Windows, Linux, macOS).

Usage:
    python update_all_translations.py [--extract] [--compile] [--test]

Options:
    --extract    Extract new translatable strings
    --compile    Compile .po files to .mo
    --test       Test translations
    (default: does everything)
"""

import argparse
import sys
from pathlib import Path


def log_info(message):
    """Info display."""
    print(f"ℹ️  {message}")


def log_success(message):
    """Success display."""
    print(f"✅ {message}")


def log_warning(message):
    """Warning display."""
    print(f"⚠️  {message}")


def log_error(message):
    """Error display."""
    print(f"❌ {message}")


def extract_messages(project_root):
    """Extract translatable strings."""
    log_info("1. Extracting translatable strings...")

    try:
        from babel.messages import frontend

        # Save sys.argv arguments
        original_argv = sys.argv[:]

        # Extraction configuration
        sys.argv = [
            "pybabel",
            "extract",
            "-F",
            str(project_root / "babel.cfg"),
            "-o",
            str(project_root / "messages.pot"),
            str(project_root),
        ]

        frontend.main()

        # Restore sys.argv
        sys.argv = original_argv

        # Count messages
        pot_file = project_root / "messages.pot"
        if pot_file.exists():
            with open(pot_file, "r", encoding="utf-8") as f:
                content = f.read()
                msg_count = content.count('msgid "')
            log_success(f"Extraction successful: {msg_count} messages")
            return True
        else:
            log_error(".pot file not created")
            return False

    except ImportError:
        log_error("Babel not installed. Install with: pip install babel")
        return False
    except Exception as e:
        log_error(f"Error during extraction: {e}")
        return False


def update_translations(project_root, languages):
    """Update translation files."""
    log_info("2. Updating translations...")

    pot_file = project_root / "messages.pot"
    if not pot_file.exists():
        log_warning(".pot file not found, extraction needed")
        return False

    updated = []

    for lang in languages:
        log_info(f"   Processing language: {lang}")

        po_file = (
            project_root
            / f"usage_analyzer/locales/{lang}/LC_MESSAGES/claude_monitor.po"
        )

        if po_file.exists():
            # Create a backup
            backup_file = po_file.with_suffix(".po.backup")
            po_file.replace(backup_file)
            log_info(f"     Backup created: {backup_file}")

            try:
                # Use msgmerge to update
                import subprocess

                result = subprocess.run(
                    ["msgmerge", "-U", str(po_file), str(pot_file)],
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    log_success(f"     Update successful for {lang}")
                    updated.append(lang)
                else:
                    log_warning(
                        f"     msgmerge error for {lang}, keeping backup"
                    )
                    backup_file.replace(po_file)

            except FileNotFoundError:
                log_warning(
                    f"     msgmerge not available for {lang}. "
                    "Install gettext tools: "
                    "Ubuntu/Debian: sudo apt-get install gettext, "
                    "macOS: brew install gettext, "
                    "Windows: download from https://www.gnu.org/software/gettext/"
                )
                backup_file.replace(po_file)
                updated.append(lang)
        else:
            log_warning(f"     File {po_file} not found")

    return updated


def compile_translations(project_root, languages):
    """Compile .po translations to .mo."""
    log_info("3. Compiling translations...")

    try:
        from babel.messages.mofile import write_mo
        from babel.messages.pofile import read_po
    except ImportError:
        log_error("Babel not installed. Install with: pip install babel")
        return []

    compiled = []

    for lang in languages:
        log_info(f"   Compiling language: {lang}")

        po_file = (
            project_root
            / f"usage_analyzer/locales/{lang}/LC_MESSAGES/claude_monitor.po"
        )
        mo_file = (
            project_root
            / f"usage_analyzer/locales/{lang}/LC_MESSAGES/claude_monitor.mo"
        )

        if po_file.exists():
            try:
                with open(po_file, "rb") as f:
                    catalog = read_po(f)

                with open(mo_file, "wb") as f:
                    write_mo(f, catalog)

                log_success(
                    f"     Compilation {lang.upper()} successful: {len(catalog)} messages"
                )
                compiled.append(lang)

            except Exception as e:
                log_error(f"     Compilation error {lang.upper()}: {e}")
        else:
            log_warning(f"     File {po_file} not found for {lang.upper()}")

    return compiled


def test_translations(project_root, languages):
    """Test translations."""
    log_info("4. Testing translations...")

    # Add project to path
    sys.path.insert(0, str(project_root))

    try:
        from usage_analyzer.i18n import init_translations

        # Language dictionary and expected titles
        expected_titles = {
            "en": "CLAUDE CODE USAGE MONITOR",
            "fr": "MONITEUR",  # Contains this keyword
            "es": "MONITOR DE USO DE CÓDIGO CLAUDE",
            "de": "CLAUDE CODE NUTZUNGS-MONITOR",
        }

        tested = []

        for lang in languages:
            if lang in expected_titles:
                try:
                    # Initialize translations for this language
                    gettext_func, ngettext_func = init_translations(lang)
                    result = gettext_func("ui.header.title")

                    expected = expected_titles[lang]
                    if expected in result or result == expected:
                        log_success(f"   Test {lang.upper()}: OK - {result[:40]}...")
                        tested.append(lang)
                    else:
                        log_warning(
                            f"   Test {lang.upper()}: Fallback - {result[:40]}..."
                        )

                    # Test plurals
                    singular = ngettext_func(
                        "plural.tokens_left", "plural.tokens_left", 1
                    )
                    plural = ngettext_func(
                        "plural.tokens_left", "plural.tokens_left", 2
                    )
                    log_info(f"     Plurals: '{singular}' / '{plural}'")

                except Exception as e:
                    log_error(f"   Test {lang.upper()}: Error - {e}")

        return tested

    except Exception as e:
        log_error(f"General test error: {e}")
        return []


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument(
        "--extract",
        action="store_true",
        help="Extract new translatable strings",
    )
    parser.add_argument(
        "--compile", action="store_true", help="Compile .po files to .mo"
    )
    parser.add_argument("--test", action="store_true", help="Test translations")

    args = parser.parse_args()

    # If no option, do everything
    if not any([args.extract, args.compile, args.test]):
        args.extract = args.compile = args.test = True

    # Configuration
    # Correction: point to project root even if run from scripts/
    project_root = Path(__file__).resolve().parent.parent
    languages = ["fr", "en", "es", "de"]

    log_info("Updating Claude Usage Monitor translations")
    log_info(f"Project directory: {project_root}")
    log_info(f"Supported languages: {', '.join(languages)}")

    # Check we are in the right directory
    if not (project_root / "claude_monitor.py").exists():
        log_error(
            "Error: claude_monitor.py not found. Are you in the right directory?"
        )
        sys.exit(1)

    success = True

    # Extraction
    if args.extract:
        if not extract_messages(project_root):
            success = False

        # Update .po files
        updated = update_translations(project_root, languages)
        if not updated:
            log_warning("No translation updated")

    # Compilation
    compiled = []
    if args.compile:
        compiled = compile_translations(project_root, languages)
        if not compiled:
            log_error("No translation compiled")
            success = False

    # Test
    if args.test:
        tested = test_translations(project_root, compiled or languages)
        if not tested:
            log_warning("No translation test succeeded")

    # Cleanup
    pot_file = project_root / "messages.pot"
    if pot_file.exists():
        try:
            pot_file.unlink()
            log_info("Temporary files deleted")
        except PermissionError:
            log_warning(f"Could not delete temporary file: {pot_file}")

    # Summary
    print()
    if success:
        log_success("🎉 Translation update completed successfully!")
        if compiled:
            log_info(f"Compiled languages: {', '.join(compiled)}")
            print()
            log_info("To test the changes:")
            for lang in compiled:
                log_info(f"  python claude_monitor.py --language {lang}")
    else:
        log_error("💥 Some operations failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
