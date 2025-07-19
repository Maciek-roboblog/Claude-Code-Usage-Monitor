#!/usr/bin/env python3
"""Translation maintenance script for claude-monitor using polib."""

import argparse  # nosec B404
import subprocess  # nosec B404
import sys
from pathlib import Path

try:
    import polib
except ImportError:
    print("✕ polib not found. Install it with: pip install polib")
    sys.exit(1)


def extract_strings():
    """Extract translatable strings from the source code."""
    print("\n⌁ Extracting translatable strings")

    locales_dir = Path("src/claude_monitor/locales")
    if not locales_dir.exists():
        locales_dir.mkdir(parents=True)

    # Configuration for pybabel extract
    cmd = [
        "pybabel",
        "extract",
        "-F",
        "babel.cfg",
        "-k",
        "_",
        "-k",
        "ngettext:1,2",
        "-k",
        "lazy_gettext",
        "--ignore-dirs=tests",
        "-o",
        "src/claude_monitor/locales/messages.pot",
        "src/claude_monitor/",  # Only scan claude_monitor package, not tests
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)  # nosec B603
        print("✓ Extraction successful")

        # Count extracted strings
        pot_file = Path("src/claude_monitor/locales/messages.pot")
        if pot_file.exists():
            pot = polib.pofile(str(pot_file))
            print(f"⁎ {len(pot)} translatable strings extracted")

        return True
    except subprocess.CalledProcessError as e:
        print(f"✕ Error during extraction: {e}")

        if e.stderr:
            print(f"   stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        print("✕ pybabel not found. Install babel: pip install babel")

        return False


def update_translations():
    """Update existing .po files."""
    print("\n⌁ Updating translation files")

    languages = ["en", "es", "de", "fr"]
    pot_file = Path("src/claude_monitor/locales/messages.pot")

    if not pot_file.exists():
        print("✕ messages.pot file not found. Run 'extract' first")

        return False

    success_count = 0
    for lang in languages:
        lang_dir = Path(f"src/claude_monitor/locales/{lang}/LC_MESSAGES")
        lang_dir.mkdir(parents=True, exist_ok=True)
        po_file = lang_dir / "messages.po"

        if po_file.exists():
            cmd = [
                "pybabel",
                "update",
                "-i",
                "src/claude_monitor/locales/messages.pot",
                "-d",
                "src/claude_monitor/locales",
                "-l",
                lang,
            ]
        else:
            cmd = [
                "pybabel",
                "init",
                "-i",
                "src/claude_monitor/locales/messages.pot",
                "-d",
                "src/claude_monitor/locales",
                "-l",
                lang,
            ]

        try:
            subprocess.run(  # nosec B603
                cmd, check=True, capture_output=True, text=True
            )
            print(f"✓ {lang} updated/initialized")
            success_count += 1
        except subprocess.CalledProcessError as e:
            print(f"✕ Error updating {lang}: {e}")

    print(f"⁎ {success_count}/{len(languages)} languages processed")

    return success_count == len(languages)


def compile_translations():
    """Compile .po files into .mo files using polib."""
    print("\n⌁ Compiling translations")

    languages = ["en", "es", "de", "fr"]
    success_count = 0

    for lang in languages:
        po_file = Path(f"src/claude_monitor/locales/{lang}/LC_MESSAGES/messages.po")
        mo_file = Path(f"src/claude_monitor/locales/{lang}/LC_MESSAGES/messages.mo")

        if not po_file.exists():
            print(f"!  {lang}: .po file not found, skipping")

            continue

        try:
            # Load .po file with polib
            po = polib.pofile(str(po_file))

            # Save as .mo file
            po.save_as_mofile(str(mo_file))

            # Count statistics
            total = len(po)
            translated = len([e for e in po if e.translated()])

            print(f"✓ {lang}: compiled ({translated}/{total} translated)")
            success_count += 1

        except Exception as e:
            print(f"✕ Error compiling {lang}: {e}")

    print(f"⁎ {success_count}/{len(languages)} compilations successful")

    return success_count > 0


def init_language(language_code):
    """Initialize a new language."""
    print(f"⌁ Initializing language {language_code}...")

    pot_file = Path("src/claude_monitor/locales/messages.pot")
    if not pot_file.exists():
        print("✕ messages.pot file not found. Run 'extract' first")

        return False

    lang_dir = Path(f"src/claude_monitor/locales/{language_code}/LC_MESSAGES")
    lang_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "pybabel",
        "init",
        "-i",
        "src/claude_monitor/locales/messages.pot",
        "-d",
        "src/claude_monitor/locales",
        "-l",
        language_code,
    ]

    try:
        subprocess.run(  # nosec B603
            cmd, check=True, capture_output=True, text=True
        )
        print(f"✓ Language {language_code} initialized")

        return True
    except subprocess.CalledProcessError as e:
        print(f"✕ Error initializing {language_code}: {e}")

        return False


def show_stats():
    """Show translation statistics using polib."""
    print("\n⁎ Translation statistics:")

    languages = ["en", "es", "de", "fr"]
    for lang in languages:
        po_file = Path(f"src/claude_monitor/locales/{lang}/LC_MESSAGES/messages.po")
        if not po_file.exists():
            print(f"  {lang}: file not found")
            continue
        try:
            po = polib.pofile(str(po_file))
            # Ignore header and obsolete entries
            entries = [e for e in po if e.msgid.strip() != "" and not e.obsolete]
            total = len(entries)
            translated = len([e for e in entries if e.translated()])
            untranslated = total - translated
            if lang == "en":
                print(f"  ¡ en: {total} messages to translate")
            else:
                if translated == total:
                    if total == 1:
                        print(f"  ✓ {lang}: 1 message translated")
                    else:
                        print(f"  ✓ {lang}: {translated} messages translated")
                else:
                    if translated == 1:
                        print(
                            f"  ✓ {lang}: 1 message translated, ✕ {untranslated} messages not translated"
                        )
                    else:
                        print(
                            f"  ✓ {lang}: {translated} messages translated, ✕ {untranslated} messages not translated"
                        )
        except Exception as e:
            print(f"  ✕ {lang}: error reading file - {e}")


def full_workflow():
    """Full workflow: extract -> update -> compile."""
    print("⌁ Full translation workflow")

    success = True
    success &= extract_strings()
    success &= update_translations()
    success &= compile_translations()

    if success:
        print("\n✓ Full workflow completed successfully")

        show_stats()
    else:
        print("\n✕ Some steps failed in the workflow")

    return success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Translation maintenance for claude-monitor"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # extract command
    subparsers.add_parser("extract", help="Extract translatable strings")

    # update command
    subparsers.add_parser("update", help="Update existing .po files")

    # compile command
    subparsers.add_parser("compile", help="Compile .po files to .mo files")

    # init command
    init_parser = subparsers.add_parser("init", help="Initialize new language")
    init_parser.add_argument("language", help="Language code (e.g., 'it', 'pt')")

    # stats command
    subparsers.add_parser("stats", help="Show translation statistics")

    # full command
    subparsers.add_parser("full", help="Full workflow: extract -> update -> compile")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    success = False
    if args.command == "extract":
        success = extract_strings()
    elif args.command == "update":
        success = update_translations()
    elif args.command == "compile":
        success = compile_translations()
    elif args.command == "init":
        success = init_language(args.language)
    elif args.command == "stats":
        show_stats()
        success = True
    elif args.command == "full":
        success = full_workflow()
    else:
        parser.print_help()
        return 1

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
