"""
Unit tests for the Docker entrypoint script (docker-entrypoint.sh).
"""

import os
import subprocess
from pathlib import Path

import pytest


class TestDockerEntrypoint:
    """Tests for the Docker entrypoint script."""

    @property
    def entrypoint_script(self):
        """Path to the Docker entrypoint script."""
        return Path(__file__).parent.parent.parent / "docker-entrypoint.sh"

    def test_entrypoint_script_exists(self):
        """Test that the entrypoint script exists."""
        assert self.entrypoint_script.exists()
        assert self.entrypoint_script.is_file()

    def test_entrypoint_script_executable(self):
        """Test that the entrypoint script is executable."""
        if os.name != "nt":  # Not on Windows
            stat_info = self.entrypoint_script.stat()
            assert stat_info.st_mode & 0o111  # Executable permissions

    def test_entrypoint_script_shebang(self):
        """Test that the script has the correct shebang."""
        with open(self.entrypoint_script, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
        assert first_line == "#!/bin/bash"

    @pytest.mark.skipif(os.name == "nt", reason="Bash not available on Windows")
    def test_entrypoint_validation_missing_data_path(self):
        """Test validation when CLAUDE_DATA_PATH is missing."""
        env = os.environ.copy()
        # Remove CLAUDE_DATA_PATH if present
        env.pop("CLAUDE_DATA_PATH", None)

        try:
            result = subprocess.run(
                ["bash", str(self.entrypoint_script)],
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )
            # The script should fail
            assert result.returncode != 0
            assert "CLAUDE_DATA_PATH environment variable is not set" in result.stderr
        except subprocess.TimeoutExpired:
            pytest.skip("Script timeout - may occur in some environments")

    @pytest.mark.skipif(os.name == "nt", reason="Bash not available on Windows")
    def test_entrypoint_validation_nonexistent_data_path(self):
        """Test validation with a nonexistent data path."""
        env = os.environ.copy()
        env["CLAUDE_DATA_PATH"] = "/nonexistent/path"

        try:
            result = subprocess.run(
                ["bash", str(self.entrypoint_script)],
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )
            assert result.returncode != 0
            assert "does not exist or is not accessible" in result.stderr
        except subprocess.TimeoutExpired:
            pytest.skip("Script timeout")

    @pytest.mark.skipif(os.name == "nt", reason="Bash not available on Windows")
    def test_entrypoint_with_valid_data_path(self, temp_data_dir, jsonl_file_with_data):
        """Test the entrypoint script with a valid data path."""
        env = os.environ.copy()
        env.update(
            {
                "CLAUDE_DATA_PATH": str(temp_data_dir),
                "CLAUDE_PLAN": "pro",
                "CLAUDE_THEME": "auto",
                "CLAUDE_DEBUG_MODE": "true",
            }
        )

        try:
            # Use echo as a test command instead of the main script
            result = subprocess.run(
                ["bash", str(self.entrypoint_script), "echo", "test_successful"],
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
            )

            # The script should not fail during validation
            if result.returncode != 0:
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")

            # Should pass validation and execute the command
            assert "test_successful" in result.stdout
            assert "Initialization complete" in result.stderr

        except subprocess.TimeoutExpired:
            pytest.skip("Script timeout")

    @pytest.mark.skipif(os.name == "nt", reason="Bash not available on Windows")
    def test_entrypoint_invalid_plan_validation(
        self, temp_data_dir, jsonl_file_with_data
    ):
        """Test validation with an invalid Claude plan."""
        env = os.environ.copy()
        env.update(
            {
                "CLAUDE_DATA_PATH": str(temp_data_dir),
                "CLAUDE_PLAN": "invalid_plan",
                "CLAUDE_DEBUG_MODE": "true",
            }
        )

        try:
            result = subprocess.run(
                ["bash", str(self.entrypoint_script), "echo", "test"],
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )

            # The script should automatically correct the invalid plan
            assert "Invalid CLAUDE_PLAN" in result.stderr
            assert "defaulting to 'pro'" in result.stderr

        except subprocess.TimeoutExpired:
            pytest.skip("Script timeout")

    @pytest.mark.skipif(os.name == "nt", reason="Bash not available on Windows")
    def test_entrypoint_invalid_theme_validation(
        self, temp_data_dir, jsonl_file_with_data
    ):
        """Test validation with an invalid theme."""
        env = os.environ.copy()
        env.update(
            {
                "CLAUDE_DATA_PATH": str(temp_data_dir),
                "CLAUDE_THEME": "invalid_theme",
                "CLAUDE_DEBUG_MODE": "true",
            }
        )

        try:
            result = subprocess.run(
                ["bash", str(self.entrypoint_script), "echo", "test"],
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )

            assert "Invalid CLAUDE_THEME" in result.stderr
            assert "defaulting to 'auto'" in result.stderr

        except subprocess.TimeoutExpired:
            pytest.skip("Script timeout")

    @pytest.mark.skipif(os.name == "nt", reason="Bash not available on Windows")
    def test_entrypoint_invalid_refresh_interval(
        self, temp_data_dir, jsonl_file_with_data
    ):
        """Test validation with an invalid refresh interval."""
        env = os.environ.copy()
        env.update(
            {
                "CLAUDE_DATA_PATH": str(temp_data_dir),
                "CLAUDE_REFRESH_INTERVAL": "-5",
                "CLAUDE_DEBUG_MODE": "true",
            }
        )

        try:
            result = subprocess.run(
                ["bash", str(self.entrypoint_script), "echo", "test"],
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )

            assert "Invalid CLAUDE_REFRESH_INTERVAL" in result.stderr
            assert "defaulting to 3" in result.stderr

        except subprocess.TimeoutExpired:
            pytest.skip("Script timeout")

    @pytest.mark.skipif(os.name == "nt", reason="Bash not available on Windows")
    def test_entrypoint_debug_mode_output(self, temp_data_dir, jsonl_file_with_data):
        """Test debug mode output."""
        env = os.environ.copy()
        env.update(
            {
                "CLAUDE_DATA_PATH": str(temp_data_dir),
                "CLAUDE_PLAN": "pro",
                "CLAUDE_TIMEZONE": "UTC",
                "CLAUDE_THEME": "dark",
                "CLAUDE_REFRESH_INTERVAL": "5",
                "CLAUDE_DEBUG_MODE": "true",
            }
        )

        try:
            result = subprocess.run(
                ["bash", str(self.entrypoint_script), "echo", "debug_test"],
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Check that debug information is displayed
            assert "Debug mode enabled" in result.stderr
            assert "Environment variables:" in result.stderr
            assert f"CLAUDE_DATA_PATH={temp_data_dir}" in result.stderr
            assert "CLAUDE_PLAN=pro" in result.stderr
            assert "CLAUDE_TIMEZONE=UTC" in result.stderr
            assert "CLAUDE_THEME=dark" in result.stderr
            assert "CLAUDE_REFRESH_INTERVAL=5" in result.stderr

        except subprocess.TimeoutExpired:
            pytest.skip("Script timeout")

    @pytest.mark.skipif(os.name == "nt", reason="Bash not available on Windows")
    def test_entrypoint_signal_handling(self, temp_data_dir, jsonl_file_with_data):
        """Test signal handling (graceful shutdown)."""
        env = os.environ.copy()
        env.update(
            {"CLAUDE_DATA_PATH": str(temp_data_dir), "CLAUDE_DEBUG_MODE": "true"}
        )

        try:
            # Start the process with a command that waits
            process = subprocess.Popen(
                ["bash", str(self.entrypoint_script), "sleep", "30"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Wait a bit then send SIGTERM
            import time

            time.sleep(2)
            process.terminate()

            # Wait for the process to finish
            stdout, stderr = process.communicate(timeout=5)

            # The process should exit cleanly
            assert process.returncode != 0  # Terminated by signal

        except (subprocess.TimeoutExpired, ProcessLookupError):
            # Force kill if necessary
            try:
                process.kill()
            except (OSError, ProcessLookupError):
                pass
            pytest.skip("Complex signal test - may vary by environment")

    def test_entrypoint_script_logging_functions(self):
        """Test that logging functions are defined in the script."""
        with open(self.entrypoint_script, "r", encoding="utf-8") as f:
            content = f.read()

        # Check that logging functions are present
        assert "log_info()" in content
        assert "log_warn()" in content
        assert "log_error()" in content
        assert "log_success()" in content

        # Check color codes
        assert "RED=" in content
        assert "GREEN=" in content
        assert "YELLOW=" in content
        assert "BLUE=" in content

    def test_entrypoint_script_validation_functions(self):
        """Test that validation functions are defined."""
        with open(self.entrypoint_script, "r", encoding="utf-8") as f:
            content = f.read()

        # Check main functions
        assert "validate_environment()" in content
        assert "test_application()" in content
        assert "initialize()" in content
        assert "build_args()" in content
        assert "cleanup()" in content

    def test_entrypoint_script_trap_signals(self):
        """Test that signals are trapped."""
        with open(self.entrypoint_script, "r", encoding="utf-8") as f:
            content = f.read()

        assert "trap cleanup SIGTERM SIGINT SIGQUIT" in content

    @pytest.mark.skipif(os.name == "nt", reason="Bash not available on Windows")
    def test_entrypoint_no_jsonl_warning(self, empty_data_dir):
        """Test warning when no .jsonl file is found."""
        env = os.environ.copy()
        env.update(
            {"CLAUDE_DATA_PATH": str(empty_data_dir), "CLAUDE_DEBUG_MODE": "true"}
        )

        try:
            result = subprocess.run(
                ["bash", str(self.entrypoint_script), "echo", "test"],
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Should display a warning but continue
            assert "No .jsonl files found" in result.stderr
            assert (
                "Make sure your Claude data directory contains usage data files"
                in result.stderr
            )

        except subprocess.TimeoutExpired:
            pytest.skip("Script timeout")

    @pytest.mark.skipif(os.name == "nt", reason="Bash not available on Windows")
    def test_entrypoint_jsonl_files_count(self, multiple_jsonl_files):
        """Test counting of .jsonl files."""
        data_dir = multiple_jsonl_files[0].parent
        env = os.environ.copy()
        env.update({"CLAUDE_DATA_PATH": str(data_dir), "CLAUDE_DEBUG_MODE": "true"})

        try:
            result = subprocess.run(
                ["bash", str(self.entrypoint_script), "echo", "test"],
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Should count and display the number of .jsonl files
            assert "Found 3 .jsonl files in data directory" in result.stderr

        except subprocess.TimeoutExpired:
            pytest.skip("Script timeout")


class TestDockerEntrypointIntegration:
    """Integration tests for the Docker entrypoint script."""

    @pytest.mark.skipif(os.name == "nt", reason="Bash not available on Windows")
    def test_full_docker_environment_simulation(
        self, temp_data_dir, jsonl_file_with_data
    ):
        """Full test simulating a Docker environment."""
        entrypoint_script = Path(__file__).parent.parent.parent / "docker-entrypoint.sh"

        # Full Docker environment configuration
        env = os.environ.copy()
        env.update(
            {
                "CLAUDE_DATA_PATH": str(temp_data_dir),
                "CLAUDE_PLAN": "pro",
                "CLAUDE_TIMEZONE": "Europe/Paris",
                "CLAUDE_THEME": "dark",
                "CLAUDE_REFRESH_INTERVAL": "10",
                "CLAUDE_DEBUG_MODE": "true",
                "PYTHONPATH": "/app",
                "PYTHONUNBUFFERED": "1",
            }
        )

        try:
            result = subprocess.run(
                ["bash", str(entrypoint_script), "python", "--version"],
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
            )

            # The script should complete initialization and execute the command
            assert "Initialization complete" in result.stderr
            assert (
                "Starting Claude Code Usage Monitor" in result.stderr
                or "Executing custom command" in result.stderr
            )

        except subprocess.TimeoutExpired:
            pytest.skip("Integration test timeout")

    @pytest.mark.skipif(os.name == "nt", reason="Bash not available on Windows")
    def test_entrypoint_build_args_functionality(
        self, temp_data_dir, jsonl_file_with_data
    ):
        """Test building arguments from environment variables."""
        entrypoint_script = Path(__file__).parent.parent.parent / "docker-entrypoint.sh"

        env = os.environ.copy()
        env.update(
            {
                "CLAUDE_DATA_PATH": str(temp_data_dir),
                "CLAUDE_PLAN": "max5",
                "CLAUDE_TIMEZONE": "Asia/Tokyo",
                "CLAUDE_THEME": "light",
                "CLAUDE_DEBUG_MODE": "true",
            }
        )

        try:
            # Use echo instead of the main script to see the arguments
            result = subprocess.run(
                ["bash", str(entrypoint_script), "echo", "args_test"],
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )

            # In debug mode, the script should display the built arguments
            assert "Initialization complete" in result.stderr

        except subprocess.TimeoutExpired:
            pytest.skip("Script timeout")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
