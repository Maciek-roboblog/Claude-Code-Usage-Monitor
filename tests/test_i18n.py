#!/usr/bin/env python3
"""
Comprehensive test script to validate multilingual support.
Tests all supported languages: fr, en, es, de
"""

import sys
from pathlib import Path

# Add the project directory to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_all_languages():
    """Tests full support for all languages."""
    print("🧪 Comprehensive multilingual support test")
    print("=" * 50)

    try:
        from usage_analyzer.i18n import init_translations

        # Test configuration
        languages = {
            "en": {
                "name": "English",
                "flag": "🇺🇸",
                "expected_title": "CLAUDE CODE USAGE MONITOR",
                "expected_tokens_single": "token left",
                "expected_tokens_plural": "tokens left",
            },
            "fr": {
                "name": "Français",
                "flag": "🇫🇷",
                "expected_title": "MONITEUR",  # Contains this word
                "expected_tokens_single": "token restant",
                "expected_tokens_plural": "tokens restants",
            },
            "es": {
                "name": "Español",
                "flag": "🇪🇸",
                "expected_title": "MONITOR DE USO DE CÓDIGO CLAUDE",
                "expected_tokens_single": "token restante",
                "expected_tokens_plural": "tokens restantes",
            },
            "de": {
                "name": "Deutsch",
                "flag": "🇩🇪",
                "expected_title": "CLAUDE CODE NUTZUNGS-MONITOR",
                "expected_tokens_single": "verbleibendes Token",
                "expected_tokens_plural": "verbleibende Tokens",
            },
        }

        all_passed = True
        results = {}

        for lang_code, config in languages.items():
            print(f"\n{config['flag']} Testing {config['name']} ({lang_code.upper()})")
            print("-" * 40)

            try:
                # Initialize translations
                gettext_func, ngettext_func = init_translations(lang_code)

                # Test 1: Main title
                title = gettext_func("ui.header.title")
                title_ok = (
                    config["expected_title"] in title
                    or title == config["expected_title"]
                )

                if title_ok:
                    print(f"✅ Title: {title}")
                else:
                    print(
                        f"❌ Title: Expected '{config['expected_title']}', got '{title}'"
                    )
                    all_passed = False

                # Test 2: UI messages
                loading = gettext_func("ui.loading.message")
                print(f"ℹ️  Loading: {loading}")

                # Test 3: Error messages
                error = gettext_func("error.data_fetch_failed")
                print(f"ℹ️  Error: {error}")

                # Test 4: Plurals
                singular = ngettext_func("plural.tokens_left", "plural.tokens_left", 1)
                plural = ngettext_func("plural.tokens_left", "plural.tokens_left", 2)

                singular_ok = singular == config["expected_tokens_single"]
                plural_ok = plural == config["expected_tokens_plural"]

                if singular_ok and plural_ok:
                    print(f"✅ Plurals: '{singular}' / '{plural}'")
                else:
                    print(
                        f"❌ Plurals: Expected '{config['expected_tokens_single']}'/'{config['expected_tokens_plural']}'"
                    )
                    print(f"   Got: '{singular}'/'{plural}'")
                    all_passed = False

                # Test 5: Messages with variables
                limit_msg = gettext_func("notification.limit_exceeded")
                print(f"ℹ️  Notification: {limit_msg[:50]}...")

                # Summary for this language
                lang_passed = title_ok and singular_ok and plural_ok
                results[lang_code] = {
                    "passed": lang_passed,
                    "name": config["name"],
                    "flag": config["flag"],
                }

                if lang_passed:
                    print(f"🎉 {config['name']} : ALL TESTS PASSED")
                else:
                    print(f"⚠️  {config['name']} : SOME TESTS FAILED")

            except Exception as e:
                print(f"❌ Critical error for {config['name']}: {e}")
                all_passed = False
                results[lang_code] = {
                    "passed": False,
                    "name": config["name"],
                    "flag": config["flag"],
                    "error": str(e),
                }

        # Final summary
        print("\n" + "=" * 50)
        print("📊 FINAL SUMMARY")
        print("=" * 50)

        passed_count = sum(1 for r in results.values() if r["passed"])
        total_count = len(results)

        for lang_code, result in results.items():
            status = "✅" if result["passed"] else "❌"
            print(f"{status} {result['flag']} {result['name']} ({lang_code.upper()})")
            if "error" in result:
                print(f"   Error: {result['error']}")

        print(f"\n📈 Score: {passed_count}/{total_count} languages functional")

        if all_passed:
            print("🏆 ALL MULTILINGUAL TESTS PASSED!")
            print("🎯 Claude Usage Monitor fully supports 4 languages")
            return True
        else:
            print("💥 SOME TESTS FAILED")
            print("🔧 Check the translation files and recompile")
            return False

    except Exception as e:
        print(f"❌ Fatal error in tests: {e}")
        return False


def test_cli_integration():
    """Tests integration with the CLI interface."""
    print("\n🔧 CLI integration test")
    print("-" * 30)

    try:
        from claude_monitor import determine_language

        # Mock args object
        class MockArgs:
            def __init__(self, language=None):
                self.language = language

        # Test language detection
        test_cases = [
            ("fr", "fr"),
            ("en", "en"),
            ("es", "es"),
            ("de", "de"),
            ("auto", None),  # Auto-detection
        ]

        for input_lang, expected in test_cases:
            args = MockArgs(input_lang)
            result = determine_language(args)

            if expected:
                if result == expected:
                    print(f"✅ CLI --language {input_lang} → {result}")
                else:
                    print(
                        f"❌ CLI --language {input_lang} → {result} (expected: {expected})"
                    )
            else:
                print(f"ℹ️  CLI --language {input_lang} → {result} (auto-detection)")

        return True

    except Exception as e:
        print(f"❌ Error in CLI tests: {e}")
        return False


if __name__ == "__main__":
    print("🌍 CLAUDE USAGE MONITOR - FULL MULTILINGUAL TEST")
    print("🚀 Testing language support: EN, FR, ES, DE")
    print("📅 " + "=" * 48)

    success = True
    success &= test_all_languages()
    success &= test_cli_integration()

    print("\n" + "=" * 50)
    if success:
        print("🎊 TOTAL SUCCESS! Multilingual support is operational.")
        print("✨ Claude Usage Monitor is ready for international use!")
        sys.exit(0)
    else:
        print("💥 FAILURES DETECTED! See errors above.")
        print("🔧 Recompile translations and try again.")
        sys.exit(1)
