#!/usr/bin/env python3
"""Test script pour vérifier le problème d'encodage."""

from pathlib import Path

project_root = Path(__file__).parent

print("Testing docker-entrypoint.sh encoding...")

try:
    with open(project_root / "docker-entrypoint.sh", "r", encoding="utf-8") as f:
        content = f.read()
    print(f"✅ Successfully read docker-entrypoint.sh ({len(content)} characters)")

    # Check specific optimizations
    startup_checks = {
        "fast_validation": "validate_environment" in content,
        "parallel_checks": "&&" in content,
        "early_exit": "exit 1" in content,
        "minimal_logging": "log_info" in content,
    }

    print("Startup checks:")
    for check, passed in startup_checks.items():
        print(f"  {check}: {'✅' if passed else '❌'}")

except UnicodeDecodeError as e:
    print(f"❌ UnicodeDecodeError: {e}")
except Exception as e:
    print(f"❌ Other error: {e}")
