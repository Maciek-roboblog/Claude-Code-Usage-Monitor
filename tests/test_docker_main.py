"""
Suite de tests principale pour l'implémentation Docker de Claude Code Usage Monitor.

Ce module orchestre tous les tests Docker et fournit des utilitaires de test.
"""

import sys
from pathlib import Path

import pytest

# Ajouter le répertoire du projet au chemin Python
sys.path.insert(0, str(Path(__file__).parent.parent))


def _run_docker_test_suite(test_file=None, extra_args=None):
    """Helper pour exécuter une suite de tests Docker avec options communes."""
    base_path = Path(__file__).parent / "docker"
    if test_file:
        target = str(base_path / test_file)
    else:
        target = str(base_path)
    test_args = [target, "-v", "--tb=short"]
    if extra_args:
        test_args.extend(extra_args)
    return pytest.main(test_args)


def run_all_docker_tests():
    """Exécute tous les tests Docker avec des options spécifiques."""
    extra_args = [
        "--strict-markers",
        "--disable-warnings",
        "-x",
    ]
    return _run_docker_test_suite(extra_args=extra_args)


def run_health_system_tests():
    """Exécute uniquement les tests du système de santé."""
    return _run_docker_test_suite("test_health_system.py")


def run_entrypoint_tests():
    """Exécute uniquement les tests du script d'entrée."""
    return _run_docker_test_suite("test_entrypoint.py")


def run_dockerfile_tests():
    """Exécute uniquement les tests du Dockerfile."""
    return _run_docker_test_suite("test_dockerfile.py")


def run_compose_tests():
    """Exécute uniquement les tests Docker Compose."""
    return _run_docker_test_suite("test_compose.py")


def run_integration_tests():
    """Exécute uniquement les tests d'intégration."""
    return _run_docker_test_suite("test_integration.py")


def run_edge_case_tests():
    """Exécute uniquement les tests de cas limites."""
    return _run_docker_test_suite("test_edge_cases.py")


def run_quick_tests():
    """Exécute uniquement les tests rapides (sans Docker réel)."""
    test_args = [
        str(Path(__file__).parent / "docker"),
        "-v",
        "--tb=short",
        "-m",
        "not slow",  # Exclure les tests marqués comme lents
        "--disable-warnings",
    ]

    return pytest.main(test_args)


def run_docker_tests_with_coverage():
    """Exécute les tests avec couverture de code."""
    import importlib.util

    if importlib.util.find_spec("pytest_cov") is not None:
        test_args = [
            str(Path(__file__).parent / "docker"),
            "-v",
            "--tb=short",
            "--cov=scripts",
            "--cov-report=html",
            "--cov-report=term-missing",
        ]

        return pytest.main(test_args)
    else:
        print(
            "pytest-cov non installé. Installation recommandée : pip install pytest-cov"
        )
        return run_all_docker_tests()


class DockerTestSuite:
    """Classe utilitaire pour gérer la suite de tests Docker."""

    @staticmethod
    def check_docker_availability():
        """Vérifie si Docker est disponible sur le système."""
        import shutil

        docker_available = shutil.which("docker") is not None
        compose_available = (
            shutil.which("docker-compose") is not None
            or shutil.which("docker") is not None  # docker compose
        )

        return {
            "docker": docker_available,
            "compose": compose_available,
            "can_run_integration": docker_available and compose_available,
        }

    @staticmethod
    def print_test_environment_info():
        """Affiche les informations sur l'environnement de test."""
        import platform
        import sys

        availability = DockerTestSuite.check_docker_availability()

        print("=== Environnement de Test Docker ===")
        print(f"Système: {platform.system()} {platform.release()}")
        print(f"Python: {sys.version}")
        print(f"Docker disponible: {'✓' if availability['docker'] else '✗'}")
        print(f"Docker Compose disponible: {'✓' if availability['compose'] else '✗'}")
        print(
            f"Tests d'intégration possibles: {'✓' if availability['can_run_integration'] else '✗'}"
        )
        print("=" * 40)

    @staticmethod
    def run_compatibility_check():
        """Exécute une vérification de compatibilité."""
        import tempfile
        from pathlib import Path

        print("Vérification de compatibilité Docker...")

        # Vérifier les fichiers requis
        project_root = Path(__file__).parent.parent
        required_files = [
            "Dockerfile",
            "docker-compose.yml",
            "docker-entrypoint.sh",
            "scripts/health_check.sh",
            "scripts/health_server.py",
        ]

        missing_files = []
        for file_path in required_files:
            if not (project_root / file_path).exists():
                missing_files.append(file_path)

        if missing_files:
            print(f"❌ Fichiers manquants: {missing_files}")
            return False

        print("✅ Tous les fichiers Docker requis sont présents")

        # Vérifier les dépendances Python
        import importlib.util
        if importlib.util.find_spec("yaml") is not None:
            print("✅ PyYAML disponible")
        else:
            print("⚠️  PyYAML manquant (requis pour les tests Docker Compose)")

        # Vérifier l'environnement de test
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                test_file = Path(temp_dir) / "test.jsonl"
                test_file.write_text('{"test": "data"}\n')
                print("✅ Environnement de test fonctionnel")
        except Exception as e:
            print(f"❌ Problème avec l'environnement de test: {e}")
            return False

        return True


def main():
    """Point d'entrée principal pour exécuter les tests Docker."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Suite de tests Docker pour Claude Code Usage Monitor"
    )
    parser.add_argument(
        "--suite",
        choices=[
            "all",
            "health",
            "entrypoint",
            "dockerfile",
            "compose",
            "integration",
            "edge-cases",
            "quick",
        ],
        default="all",
        help="Suite de tests à exécuter",
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Exécuter avec couverture de code"
    )
    parser.add_argument(
        "--check", action="store_true", help="Vérifier la compatibilité seulement"
    )
    parser.add_argument(
        "--info", action="store_true", help="Afficher les informations d'environnement"
    )

    args = parser.parse_args()

    if args.info:
        DockerTestSuite.print_test_environment_info()
        return 0

    if args.check:
        success = DockerTestSuite.run_compatibility_check()
        return 0 if success else 1

    # Exécuter la suite de tests appropriée
    if args.coverage:
        return run_docker_tests_with_coverage()
    elif args.suite == "all":
        return run_all_docker_tests()
    elif args.suite == "health":
        return run_health_system_tests()
    elif args.suite == "entrypoint":
        return run_entrypoint_tests()
    elif args.suite == "dockerfile":
        return run_dockerfile_tests()
    elif args.suite == "compose":
        return run_compose_tests()
    elif args.suite == "integration":
        return run_integration_tests()
    elif args.suite == "edge-cases":
        return run_edge_case_tests()
    elif args.suite == "quick":
        return run_quick_tests()
    else:
        print(f"Suite de tests inconnue: {args.suite}")
        return 1


if __name__ == "__main__":
    exit(main())
