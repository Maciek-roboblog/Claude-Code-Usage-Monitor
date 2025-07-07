#!/usr/bin/env python3
"""
Script générique pour mettre à jour et compiler toutes les traductions.
Compatible avec toutes les plateformes (Windows, Linux, macOS).

Usage:
    python update_all_translations.py [--extract] [--compile] [--test]

Options:
    --extract    Extraire les nouvelles chaînes traduisibles
    --compile    Compiler les fichiers .po en .mo
    --test       Tester les traductions
    (par défaut: fait tout)
"""

import argparse
import sys
from pathlib import Path


def log_info(message):
    """Affichage d'information."""
    print(f"ℹ️  {message}")


def log_success(message):
    """Affichage de succès."""
    print(f"✅ {message}")


def log_warning(message):
    """Affichage d'avertissement."""
    print(f"⚠️  {message}")


def log_error(message):
    """Affichage d'erreur."""
    print(f"❌ {message}")


def extract_messages(project_root):
    """Extraire les chaînes traduisibles."""
    log_info("1. Extraction des chaînes traduisibles...")

    try:
        from babel.messages import frontend

        # Sauvegarder les arguments sys.argv
        original_argv = sys.argv[:]

        # Configuration pour l'extraction
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

        # Restaurer sys.argv
        sys.argv = original_argv

        # Compter les messages
        pot_file = project_root / "messages.pot"
        if pot_file.exists():
            with open(pot_file, "r", encoding="utf-8") as f:
                content = f.read()
                msg_count = content.count('msgid "')
            log_success(f"Extraction réussie: {msg_count} messages")
            return True
        else:
            log_error("Fichier .pot non créé")
            return False

    except ImportError:
        log_error("Babel non installé. Installez avec: pip install babel")
        return False
    except Exception as e:
        log_error(f"Erreur lors de l'extraction: {e}")
        return False


def update_translations(project_root, languages):
    """Mettre à jour les fichiers de traduction."""
    log_info("2. Mise à jour des traductions...")

    pot_file = project_root / "messages.pot"
    if not pot_file.exists():
        log_warning("Fichier .pot non trouvé, extraction nécessaire")
        return False

    updated = []

    for lang in languages:
        log_info(f"   Traitement de la langue: {lang}")

        po_file = (
            project_root
            / f"usage_analyzer/locales/{lang}/LC_MESSAGES/claude_monitor.po"
        )

        if po_file.exists():
            # Créer une sauvegarde
            backup_file = po_file.with_suffix(".po.backup")
            po_file.replace(backup_file)
            log_info(f"     Sauvegarde créée: {backup_file}")

            try:
                # Utiliser msgmerge pour mettre à jour
                import subprocess

                result = subprocess.run(
                    ["msgmerge", "-U", str(po_file), str(pot_file)],
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    log_success(f"     Mise à jour réussie pour {lang}")
                    updated.append(lang)
                else:
                    log_warning(
                        f"     Erreur msgmerge pour {lang}, conservation du backup"
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
            log_warning(f"     Fichier {po_file} non trouvé")

    return updated


def compile_translations(project_root, languages):
    """Compiler les traductions .po en .mo."""
    log_info("3. Compilation des traductions...")

    try:
        from babel.messages.mofile import write_mo
        from babel.messages.pofile import read_po
    except ImportError:
        log_error("Babel non installé. Installez avec: pip install babel")
        return []

    compiled = []

    for lang in languages:
        log_info(f"   Compilation de la langue: {lang}")

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
                    f"     Compilation {lang.upper()} réussie: {len(catalog)} messages"
                )
                compiled.append(lang)

            except Exception as e:
                log_error(f"     Erreur compilation {lang.upper()}: {e}")
        else:
            log_warning(f"     Fichier {po_file} non trouvé pour {lang.upper()}")

    return compiled


def test_translations(project_root, languages):
    """Tester les traductions."""
    log_info("4. Test des traductions...")

    # Ajouter le projet au path
    sys.path.insert(0, str(project_root))

    try:
        from usage_analyzer.i18n import init_translations

        # Dictionnaire des langues et titres attendus
        expected_titles = {
            "en": "CLAUDE CODE USAGE MONITOR",
            "fr": "MONITEUR",  # Contient ce mot clé
            "es": "MONITOR DE USO DE CÓDIGO CLAUDE",
            "de": "CLAUDE CODE NUTZUNGS-MONITOR",
        }

        tested = []

        for lang in languages:
            if lang in expected_titles:
                try:
                    # Initialiser les traductions pour cette langue
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

                    # Test des pluriels
                    singular = ngettext_func(
                        "plural.tokens_left", "plural.tokens_left", 1
                    )
                    plural = ngettext_func(
                        "plural.tokens_left", "plural.tokens_left", 2
                    )
                    log_info(f"     Pluriels: '{singular}' / '{plural}'")

                except Exception as e:
                    log_error(f"   Test {lang.upper()}: Erreur - {e}")

        return tested

    except Exception as e:
        log_error(f"Erreur test général: {e}")
        return []


def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument(
        "--extract",
        action="store_true",
        help="Extraire les nouvelles chaînes traduisibles",
    )
    parser.add_argument(
        "--compile", action="store_true", help="Compiler les fichiers .po en .mo"
    )
    parser.add_argument("--test", action="store_true", help="Tester les traductions")

    args = parser.parse_args()

    # Si aucune option, faire tout
    if not any([args.extract, args.compile, args.test]):
        args.extract = args.compile = args.test = True

    # Configuration
    # Correction : pointer vers la racine du projet même si lancé depuis scripts/
    project_root = Path(__file__).resolve().parent.parent
    languages = ["fr", "en", "es", "de"]

    log_info("Mise à jour des traductions Claude Usage Monitor")
    log_info(f"Répertoire projet: {project_root}")
    log_info(f"Langues supportées: {', '.join(languages)}")

    # Vérifier que nous sommes dans le bon répertoire
    if not (project_root / "claude_monitor.py").exists():
        log_error(
            "Erreur: claude_monitor.py non trouvé. Êtes-vous dans le bon répertoire?"
        )
        sys.exit(1)

    success = True

    # Extraction
    if args.extract:
        if not extract_messages(project_root):
            success = False

        # Mise à jour des fichiers .po
        updated = update_translations(project_root, languages)
        if not updated:
            log_warning("Aucune traduction mise à jour")

    # Compilation
    compiled = []
    if args.compile:
        compiled = compile_translations(project_root, languages)
        if not compiled:
            log_error("Aucune traduction compilée")
            success = False

    # Test
    if args.test:
        tested = test_translations(project_root, compiled or languages)
        if not tested:
            log_warning("Aucun test de traduction réussi")

    # Nettoyage
    pot_file = project_root / "messages.pot"
    if pot_file.exists():
        pot_file.unlink()
        log_info("Fichiers temporaires supprimés")

    # Résumé
    print()
    if success:
        log_success("🎉 Mise à jour des traductions terminée avec succès!")
        if compiled:
            log_info(f"Langues compilées: {', '.join(compiled)}")
            print()
            log_info("Pour tester les modifications:")
            for lang in compiled:
                log_info(f"  python claude_monitor.py --language {lang}")
    else:
        log_error("💥 Certaines opérations ont échoué")
        sys.exit(1)


if __name__ == "__main__":
    main()
