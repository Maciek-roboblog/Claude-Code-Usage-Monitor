"""
Main test suite for the Docker implementation of Claude Code Usage Monitor.

This module orchestrates all Docker tests and provides test utilities.
"""

import sys
from pathlib import Path

import pytest

# Add the project directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


def _run_docker_test_suite(test_file=None, extra_args=None):
    """Helper to run a Docker test suite with common options."""
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
    """Run all Docker tests with specific options."""
    extra_args = [
        "--strict-markers",
        "--disable-warnings",
        "-x",
    ]
    return _run_docker_test_suite(extra_args=extra_args)


def run_health_system_tests():
    """Run only the health system tests."""
    return _run_docker_test_suite("test_health_system.py")


def run_entrypoint_tests():
    """Run only the entrypoint script tests."""
    return _run_docker_test_suite("test_entrypoint.py")


def run_dockerfile_tests():
    """Run only the Dockerfile tests."""
    return _run_docker_test_suite("test_dockerfile.py")


def run_compose_tests():
    """Run only the Docker Compose tests."""
    return _run_docker_test_suite("test_compose.py")


def run_integration_tests():
    """Run only the integration tests."""
    return _run_docker_test_suite("test_integration.py")


def run_edge_case_tests():
    """Run only the edge case tests."""
    return _run_docker_test_suite("test_edge_cases.py")


def run_quick_tests():
    """Run only the quick tests (without real Docker)."""
    test_args = [
        str(Path(__file__).parent / "docker"),
        "-v",
        "--tb=short",
        "-m",
        "not slow",  # Exclude tests marked as slow
        "--disable-warnings",
    ]

    return pytest.main(test_args)


def run_docker_tests_with_coverage():
    """Run tests with code coverage."""
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
            "pytest-cov not installed. Recommended installation: pip install pytest-cov"
        )
        return run_all_docker_tests()


class DockerTestSuite:
    """Utility class to manage the Docker test suite."""

    @staticmethod
    def check_docker_availability():
        """Check if Docker is available on the system."""
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
        """Display information about the test environment."""
        import platform
        import sys

        availability = DockerTestSuite.check_docker_availability()

        print("=== Docker Test Environment ===")
        print(f"System: {platform.system()} {platform.release()}")
        print(f"Python: {sys.version}")
        print(f"Docker available: {'✓' if availability['docker'] else '✗'}")
        print(f"Docker Compose available: {'✓' if availability['compose'] else '✗'}")
        print(
            f"Integration tests possible: {'✓' if availability['can_run_integration'] else '✗'}"
        )
        print("=" * 40)

    @staticmethod
    def run_compatibility_check():
        """Run a compatibility check."""
        import tempfile
        from pathlib import Path

        print("Checking Docker compatibility...")

        # Check required files
        project_root = Path(__file__).parent.parent
        required_files = [
            "Dockerfile",
            "docker-compose.yml",
            "docker-entrypoint.sh",
            "scripts/health-check.sh",
            "scripts/health_server.py",
        ]

        missing_files = []
        for file_path in required_files:
            if not (project_root / file_path).exists():
                missing_files.append(file_path)

        if missing_files:
            print(f"❌ Missing files: {missing_files}")
            return False

        print("✅ All required Docker files are present")

        # Check Python dependencies
        import importlib.util

        if importlib.util.find_spec("yaml") is not None:
            print("✅ PyYAML available")
        else:
            print("⚠️  PyYAML missing (required for Docker Compose tests)")

        # Check test environment
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                test_file = Path(temp_dir) / "test.jsonl"
                test_file.write_text('{"test": "data"}\n')
                print("✅ Test environment functional")
        except Exception as e:
            print(f"❌ Problem with test environment: {e}")
            return False

        return True


def main():
    """Main entry point to run Docker tests."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Docker test suite for Claude Code Usage Monitor"
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
        help="Test suite to run",
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Run with code coverage"
    )
    parser.add_argument("--check", action="store_true", help="Only check compatibility")
    parser.add_argument(
        "--info", action="store_true", help="Show environment information"
    )

    args = parser.parse_args()

    if args.info:
        DockerTestSuite.print_test_environment_info()
        return 0

    if args.check:
        success = DockerTestSuite.run_compatibility_check()
        return 0 if success else 1

    # Run the appropriate test suite
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
        print(f"Unknown test suite: {args.suite}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
