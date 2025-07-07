#!/usr/bin/env python3
"""
Simple test to verify that restore_environment works correctly after fix.
"""

import os
import sys

sys.path.append("tests")

from conftest import DockerTestUtils


def test_restore_environment():
    """Test the corrected restore_environment method."""
    # Save original values
    original_val1 = os.environ.get("TEST_VAR_1")
    original_val2 = os.environ.get("TEST_VAR_2")

    try:
        # Set test values
        os.environ["TEST_VAR_1"] = "test_value_1"
        os.environ["TEST_VAR_2"] = "test_value_2"

        # Create environment to restore
        restore_env = {
            "TEST_VAR_1": original_val1,  # Could be None
            "TEST_VAR_2": "restored_value_2",
        }

        # Use the corrected restore_environment method
        DockerTestUtils.restore_environment(restore_env)

        # Verify results
        if original_val1 is None:
            assert "TEST_VAR_1" not in os.environ, (
                "TEST_VAR_1 should be removed when original was None"
            )
        else:
            assert os.environ.get("TEST_VAR_1") == original_val1, (
                f"TEST_VAR_1 should be restored to {original_val1}"
            )

        assert os.environ.get("TEST_VAR_2") == "restored_value_2", (
            "TEST_VAR_2 should be set to restored_value_2"
        )

        print("✅ restore_environment test passed!")

    finally:
        # Clean up
        if original_val1 is None:
            os.environ.pop("TEST_VAR_1", None)
        else:
            os.environ["TEST_VAR_1"] = original_val1

        if original_val2 is None:
            os.environ.pop("TEST_VAR_2", None)
        else:
            os.environ["TEST_VAR_2"] = original_val2


if __name__ == "__main__":
    test_restore_environment()
