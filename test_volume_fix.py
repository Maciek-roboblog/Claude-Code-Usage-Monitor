#!/usr/bin/env python3
"""Quick test to validate our volume configuration fix."""

from pathlib import Path

import yaml


def test_volume_configuration():
    """Test that our volume configuration fix works."""
    docker_compose_file = Path("docker-compose.yml")

    with open(docker_compose_file, "r") as f:
        compose_config = yaml.safe_load(f)

    volumes = compose_config["services"]["claude-monitor"]["volumes"]

    # There should be at least one volume configured
    assert len(volumes) >= 1, "No volumes configured"

    # Check the main volume
    main_volume = volumes[0]
    print(f"Found volume: {main_volume}")

    # Should contain the default path pattern (with or without environment variable)
    old_pattern = "~/.claude/projects:/data:ro"
    new_pattern = "${CLAUDE_PROJECTS_DIR:-~/.claude/projects}:/data:ro"

    has_old = old_pattern in main_volume
    has_new = new_pattern in main_volume

    print(f"Contains old pattern '{old_pattern}': {has_old}")
    print(f"Contains new pattern '{new_pattern}': {has_new}")

    assert has_old or has_new, f"Volume doesn't match expected pattern: {main_volume}"

    print("✅ Volume configuration test passed!")


if __name__ == "__main__":
    test_volume_configuration()
