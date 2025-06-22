#!/usr/bin/env python3
import shutil
import subprocess
import sys

# Minimum Node.js version that includes npx by default
MIN_NODE_MAJOR = 8
MIN_NODE_MINOR = 2


def test_node():
    """
    Ensure 'node' is on PATH and at least version MIN_NODE_MAJOR.MIN_NODE_MINOR.
    On failure, prints an error and exits with code 1.
    """
    node_path = shutil.which("node")
    if not node_path:
        print("✗ node not found on PATH")
        sys.exit(1)
    try:
        out = subprocess.run(
            [node_path, "--version"], capture_output=True, text=True, check=True
        )
        version = out.stdout.strip().lstrip("v")
        parts = version.split(".")
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        if major < MIN_NODE_MAJOR or (
            major == MIN_NODE_MAJOR and minor < MIN_NODE_MINOR
        ):
            print(
                f"✗ node v{version} is too old (requires ≥ v{MIN_NODE_MAJOR}.{MIN_NODE_MINOR})"
            )
            sys.exit(1)
    except subprocess.CalledProcessError as e:
        err = (e.stderr or e.stdout or "").strip()
        print("✗ node exists but failed to run '--version':")
        print(err)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error invoking node: {e}")
        sys.exit(1)


def test_npx():
    """
    Ensure 'npx' is on PATH and runnable.
    On failure, prints an error and exits with code 1.
    """
    npx_path = shutil.which("npx")
    if not npx_path:
        print("✗ npx not found on PATH")
        sys.exit(1)
    try:
        subprocess.run(
            [npx_path, "--version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        err = e.stderr.strip() or e.stdout.strip()
        print(f"✗ npx test failed: {err}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Failed to invoke npx: {e}")
        sys.exit(1)
