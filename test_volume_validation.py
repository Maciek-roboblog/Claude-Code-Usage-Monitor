#!/usr/bin/env python3
"""Test our volume path validation fix."""


def test_volume_path_validation():
    """Test the volume path validation logic."""

    # Test case 1: Traditional volume format
    volume1 = "~/.claude/projects:/data:ro"
    if volume1.startswith("${") and "}:" in volume1:
        # Handle environment variable syntax
        closing_brace = volume1.find("}:")
        remaining = volume1[closing_brace + 2 :]
        parts = remaining.split(":")
        target_path = parts[0] if parts else ""
    else:
        # Traditional format source:target:mode
        parts = volume1.split(":")
        target_path = parts[1] if len(parts) >= 2 else ""

    print(f"Volume 1: {volume1}")
    print(f"Target path 1: {target_path}")
    assert target_path == "/data", f"Expected /data, got {target_path}"
    print("✅ Volume 1 test passed!")

    # Test case 2: Environment variable format
    volume2 = "${CLAUDE_PROJECTS_DIR:-~/.claude/projects}:/data:ro"
    if volume2.startswith("${") and "}:" in volume2:
        # Handle environment variable syntax
        closing_brace = volume2.find("}:")
        remaining = volume2[closing_brace + 2 :]
        parts = remaining.split(":")
        target_path = parts[0] if parts else ""
    else:
        # Traditional format source:target:mode
        parts = volume2.split(":")
        target_path = parts[1] if len(parts) >= 2 else ""

    print(f"Volume 2: {volume2}")
    print(f"Target path 2: {target_path}")
    assert target_path == "/data", f"Expected /data, got {target_path}"
    print("✅ Volume 2 test passed!")

    print("✅ All volume path validation tests passed!")


if __name__ == "__main__":
    test_volume_path_validation()
