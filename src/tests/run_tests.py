#!/usr/bin/env python3
"""Test runner for Claude Monitor tests."""

import subprocess
import sys
from pathlib import Path


def run_tests():
    """
    Run the Claude Monitor test suite using pytest with coverage reporting.
    
    Sets up the environment to ensure correct module resolution, executes all tests in the test directory with verbose output and coverage measurement for the `claude_monitor/data` directory, and generates both terminal and HTML coverage reports. Returns the pytest exit code or 1 if pytest is not installed.
    """
    test_dir = Path(__file__).parent
    src_dir = test_dir.parent.parent.parent
    import os

    env = os.environ.copy()
    env["PYTHONPATH"] = str(src_dir)
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(test_dir),
        "-v",
        "--tb=short",
        "--color=yes",
        f"--cov={src_dir / 'claude_monitor' / 'data'}",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
    ]

    try:
        subprocess.run(cmd, env=env, check=True)
        print("\n✅ All tests passed!")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Tests failed with exit code: {e.returncode}")
        return e.returncode
    except FileNotFoundError:
        print("❌ pytest not found. Install with: pip install pytest pytest-cov")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
