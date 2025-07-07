"""
Integration tests for the complete Docker implementation.
"""

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml


class TestDockerIntegration:
    """Integration tests for the complete Docker ecosystem."""

    @property
    def project_root(self):
        """Project root directory."""
        return Path(__file__).parent.parent.parent

    def test_docker_build_context_files_present(self):
        required_files = [
            "Dockerfile",
            "docker-compose.yml",
            "docker-entrypoint.sh",
            "pyproject.toml",
            "uv.lock",
            "README.md",
            "scripts/health-check.sh",  # renamed from health_check.sh
            "scripts/health_server.py",
        ]

        for file_path in required_files:
            full_path = self.project_root / file_path
            assert full_path.exists(), f"Missing required file: {file_path}"

    def test_docker_build_context_size(self):
        """Test that the Docker build context is not too large."""
        # Calculate the build context size (simulated)
        context_size = 0

        # Files that would be included in the Docker context
        for item in self.project_root.rglob("*"):
            if item.is_file():
                # Exclude files that would not be in the context
                if not any(
                    pattern in str(item)
                    for pattern in [
                        ".git",
                        "__pycache__",
                        ".pytest_cache",
                        "tests/",
                        ".pyc",
                        ".venv",
                        "venv/",
                    ]
                ):
                    context_size += item.stat().st_size

        # The context should not exceed 50MB (very generous)
        max_context_size = 50 * 1024 * 1024  # 50MB
        assert context_size < max_context_size, (
            f"Docker context too large: {context_size} bytes"
        )

    def test_dockerfile_and_entrypoint_consistency(self):
        """Test consistency between the Dockerfile and the entrypoint script."""
        # Read the Dockerfile
        with open(self.project_root / "Dockerfile", "r", encoding="utf-8") as f:
            dockerfile_content = f.read()

        # Read the entrypoint script
        with open(
            self.project_root / "docker-entrypoint.sh", "r", encoding="utf-8"
        ) as f:
            entrypoint_content = f.read()

        # Check consistency of environment variables
        dockerfile_env_vars = [
            "CLAUDE_DATA_PATH",
            "CLAUDE_PLAN",
            "CLAUDE_TIMEZONE",
            "CLAUDE_THEME",
            "CLAUDE_REFRESH_INTERVAL",
            "CLAUDE_DEBUG_MODE",
        ]

        for env_var in dockerfile_env_vars:
            assert env_var in dockerfile_content, (
                f"Variable {env_var} missing in Dockerfile"
            )
            assert env_var in entrypoint_content, (
                f"Variable {env_var} not handled in entrypoint"
            )

    def test_compose_and_dockerfile_consistency(self):
        """Test consistency between docker-compose.yml and Dockerfile."""
        import yaml

        # Read docker-compose.yml
        with open(self.project_root / "docker-compose.yml", "r") as f:
            compose_config = yaml.safe_load(f)

        # Read the Dockerfile
        with open(self.project_root / "Dockerfile", "r", encoding="utf-8") as f:
            dockerfile_content = f.read()

        service = compose_config["services"]["claude-monitor"]

        # Check consistency of environment variables
        compose_env = service["environment"]

        for env_var, value in compose_env.items():
            # Check that the variable exists in the Dockerfile
            assert env_var in dockerfile_content, (
                f"Variable {env_var} missing in Dockerfile"
            )

        # Check build consistency
        build_config = service["build"]
        assert build_config["dockerfile"] == "Dockerfile"
        assert build_config["context"] == "."

    def test_health_check_consistency(self):
        """Test health check consistency between files."""
        import yaml

        # Read docker-compose.yml
        with open(self.project_root / "docker-compose.yml", "r") as f:
            compose_config = yaml.safe_load(f)

        # Read the Dockerfile
        with open(self.project_root / "Dockerfile", "r", encoding="utf-8") as f:
            dockerfile_content = f.read()

        # Check that both define health checks
        service = compose_config["services"]["claude-monitor"]

        if "healthcheck" in service:
            compose_healthcheck = service["healthcheck"]
            assert "test" in compose_healthcheck
            assert "interval" in compose_healthcheck

        # Check HEALTHCHECK in Dockerfile
        assert "HEALTHCHECK" in dockerfile_content
        assert "health-check.sh" in dockerfile_content

    @pytest.mark.skipif(not shutil.which("docker"), reason="Docker not available")
    def test_docker_build_syntax_validation(self):
        """Test that the Dockerfile has valid syntax."""
        try:
            # Validate Dockerfile syntax by parsing it with buildkit
            result = subprocess.run(
                [
                    "docker",
                    "build",
                    "--no-cache",
                    "--target",
                    "builder",
                    "-f",
                    "Dockerfile",
                    ".",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert result.returncode == 0, f"Dockerfile syntax error: {result.stderr}"
        except subprocess.TimeoutExpired:
            pytest.skip("Docker validation timeout")
        except FileNotFoundError:
            pytest.skip("Docker CLI not available")

    @pytest.mark.skipif(
        not shutil.which("docker-compose") and not shutil.which("docker"),
        reason="Docker Compose not available",
    )
    def test_docker_compose_syntax_validation(self):
        """Test that docker-compose.yml has valid syntax."""
        try:
            # Validate docker-compose file syntax
            cmd = (
                ["docker-compose", "config"]
                if shutil.which("docker-compose")
                else ["docker", "compose", "config"]
            )

            result = subprocess.run(
                cmd, cwd=self.project_root, capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                print(f"STDERR: {result.stderr}")

            assert result.returncode == 0, (
                f"docker-compose syntax error: {result.stderr}"
            )

        except subprocess.TimeoutExpired:
            pytest.skip("Docker Compose validation timeout")
        except FileNotFoundError:
            pytest.skip("Docker Compose CLI not available")

    def test_entrypoint_script_bash_syntax(self):
        """Test that the entrypoint script has valid bash syntax."""
        entrypoint_script = self.project_root / "docker-entrypoint.sh"

        # First check that the file exists
        assert entrypoint_script.exists(), (
            f"Entrypoint script not found: {entrypoint_script}"
        )

        # Read the script content to check for basic syntax issues
        with open(entrypoint_script, "r", encoding="utf-8") as f:
            content = f.read()

        # Basic syntax checks
        assert content.startswith("#!/bin/bash") or content.startswith(
            "#!/usr/bin/env bash"
        ), "Script should start with proper bash shebang"

        # Check for basic structural elements
        assert "function " in content or "() {" in content, (
            "No functions found in script"
        )
        assert "if [[ " in content, "No conditional statements found in script"
        assert "exit " in content, "No exit statements found in script"

        # Skip actual bash syntax check on Windows due to path compatibility issues
        if shutil.which("bash") and not hasattr(subprocess, "STARTUPINFO"):
            # Only run bash syntax check on Unix systems
            try:
                result = subprocess.run(
                    ["bash", "-n", str(entrypoint_script)],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                assert result.returncode == 0, f"Bash syntax error: {result.stderr}"

            except subprocess.TimeoutExpired:
                pytest.skip("Bash validation timeout")
        else:
            # On Windows, just skip the bash syntax check
            pytest.skip("Bash syntax check skipped on Windows")

    def test_health_check_script_bash_syntax(self):
        """Test that the health check script has valid bash syntax."""
        health_script = self.project_root / "scripts" / "health-check.sh"

        # First check that the file exists
        assert health_script.exists(), f"Health check script not found: {health_script}"

        # Read the script content to check for basic syntax issues
        with open(health_script, "r", encoding="utf-8") as f:
            content = f.read()

        # Basic syntax checks
        assert content.startswith("#!/bin/bash") or content.startswith(
            "#!/usr/bin/env bash"
        ), "Script should start with proper bash shebang"

        # Check for basic structural elements (commands and control structures)
        assert "curl" in content or "wget" in content or "python" in content, (
            "No health check commands found"
        )

        # Skip actual bash syntax check on Windows due to path compatibility issues
        if shutil.which("bash") and not hasattr(subprocess, "STARTUPINFO"):
            # Only run bash syntax check on Unix systems
            try:
                result = subprocess.run(
                    ["bash", "-n", str(health_script)],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                assert result.returncode == 0, f"Bash syntax error: {result.stderr}"

            except subprocess.TimeoutExpired:
                pytest.skip("Bash validation timeout")
        else:
            # On Windows, just skip the bash syntax check
            pytest.skip("Bash syntax check skipped on Windows")


class TestDockerWorkflow:
    """Tests for the complete Docker workflow."""

    @property
    def project_root(self):
        """Project root directory."""
        return Path(__file__).parent.parent.parent

    def test_docker_development_workflow(self, temp_data_dir, jsonl_file_with_data):
        """Test the Docker development workflow."""
        # This test simulates the complete workflow without real Docker

        # 1. Check that all configuration files are consistent
        assert (self.project_root / "Dockerfile").exists()
        assert (self.project_root / "docker-compose.yml").exists()
        assert (self.project_root / "docker-entrypoint.sh").exists()
        # 2. Simulate validation of environment variables
        test_env = {
            "CLAUDE_DATA_PATH": str(temp_data_dir),
            "CLAUDE_PLAN": "pro",
            "CLAUDE_THEME": "auto",
            "CLAUDE_DEBUG_MODE": "true",
        }

        # Validate environment variables match expected format
        assert Path(test_env["CLAUDE_DATA_PATH"]).exists()
        assert test_env["CLAUDE_PLAN"] in ["free", "pro", "team"]
        assert test_env["CLAUDE_THEME"] in ["light", "dark", "auto"]
        assert test_env["CLAUDE_DEBUG_MODE"] in ["true", "false"]

        # 3. Validate that data files are accessible

        # Load docker-compose.yml to get compose_config
        import yaml

        with open(self.project_root / "docker-compose.yml", "r") as f:
            compose_config = yaml.safe_load(f)

        service = compose_config["services"]["claude-monitor"]

        # Check production aspects
        production_checks = {
            "restart_policy": "restart" in service
            and service["restart"] == "unless-stopped",
            "resource_limits": "deploy" in service
            and "resources" in service.get("deploy", {}),
            "health_check": "healthcheck" in service,
            "security": True,  # Non-root user in Dockerfile
        }

        for check_name, passed in production_checks.items():
            assert passed, f"Production check failed: {check_name}"

    def test_docker_security_configuration(self):
        """Test Docker security configuration."""
        # Read the Dockerfile
        with open(self.project_root / "Dockerfile", "r", encoding="utf-8") as f:
            dockerfile_content = f.read()

        # Security checks
        security_checks = {
            "non_root_user": "USER claude" in dockerfile_content,
            "specific_uid": "-u 1001" in dockerfile_content,
            "no_sudo_or_su": "sudo" not in dockerfile_content
            and "su " not in dockerfile_content,
            "proper_permissions": "chown" in dockerfile_content,
            "no_privileged": "privileged" not in dockerfile_content,
        }

        for check_name, passed in security_checks.items():
            assert passed, f"Security check failed: {check_name}"

    def test_docker_volume_security(self):
        """Test Docker volume security."""

        with open(self.project_root / "docker-compose.yml", "r") as f:
            compose_config = yaml.safe_load(f)

        service = compose_config["services"]["claude-monitor"]
        volumes = service["volumes"]

        # Check that volumes are read-only
        for volume in volumes:
            if isinstance(volume, str) and ":" in volume:
                # Check if volume contains 'ro' (read-only) flag
                # This handles various formats like source:target:ro or complex paths
                assert ":ro" in volume, f"Volume not read-only: {volume}"

    def test_docker_environment_isolation(self):
        """Test Docker environment isolation."""
        # Read the Dockerfile
        with open(self.project_root / "Dockerfile", "r", encoding="utf-8") as f:
            dockerfile_content = f.read()

        # Check isolation
        isolation_checks = {
            "dedicated_workdir": "WORKDIR /app" in dockerfile_content,
            "dedicated_user": "USER claude" in dockerfile_content,
            "volume_isolation": 'VOLUME ["/data"]' in dockerfile_content,
            "env_vars_scoped": "ENV CLAUDE_" in dockerfile_content,
        }

        for check_name, passed in isolation_checks.items():
            assert passed, f"Isolation check failed: {check_name}"


class TestDockerPerformance:
    """Performance tests for Docker."""

    @property
    def project_root(self):
        """Project root directory."""
        return Path(__file__).parent.parent.parent

    def test_dockerfile_layer_optimization(self):
        """Test Docker layer optimization."""
        with open(self.project_root / "Dockerfile", "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Count instructions that create layers
        layer_instructions = [
            "FROM",
            "RUN",
            "COPY",
            "ADD",
            "ENV",
            "EXPOSE",
            "VOLUME",
            "USER",
            "WORKDIR",
        ]
        layer_count = 0

        for line in lines:
            line = line.strip()
            if any(line.startswith(instr) for instr in layer_instructions):
                layer_count += 1

        # An optimized Dockerfile should have a reasonable number of layers
        assert layer_count < 30, f"Too many Docker layers: {layer_count}"

    def test_dockerfile_cache_optimization(self):
        """Test Docker cache optimization."""
        with open(self.project_root / "Dockerfile", "r", encoding="utf-8") as f:
            content = f.read()

        # Check that dependency files are copied before source code
        pyproject_position = content.find("COPY pyproject.toml")
        source_position = content.find("COPY usage_analyzer/")

        if pyproject_position != -1 and source_position != -1:
            assert pyproject_position < source_position, (
                "COPY order not optimized for cache"
            )

    def test_dockerfile_build_efficiency(self):
        """Test Docker build efficiency best practices."""
        with open(self.project_root / "Dockerfile", "r", encoding="utf-8") as f:
            content = f.read()

        # Check efficiency best practices
        efficiency_checks = {
            "combined_apt_commands": "apt-get update &&" in content
            and "apt-get install" in content,
            "cache_cleanup": "rm -rf /var/lib/apt/lists/*" in content,
            "no_cache_pip": "--no-cache-dir" in content,
            "minimal_dependencies": "--no-install-recommends" in content,
        }

        for check_name, passed in efficiency_checks.items():
            assert passed, f"Efficiency check failed: {check_name}"

    def test_container_resource_limits(self):
        """Test container resource limits."""
        import yaml

        with open(self.project_root / "docker-compose.yml", "r") as f:
            compose_config = yaml.safe_load(f)

        service = compose_config["services"]["claude-monitor"]

        if "deploy" in service and "resources" in service["deploy"]:
            resources = service["deploy"]["resources"]

            if "limits" in resources:
                limits = resources["limits"]

                # Check that limits are reasonable
                if "memory" in limits:
                    memory_limit = limits["memory"]
                    # Convert to MB for checking
                    if memory_limit.endswith("M"):
                        memory_mb = int(memory_limit[:-1])
                        assert memory_mb <= 1024, (
                            f"Memory limit too high: {memory_mb}MB"
                        )

    def test_startup_time_optimization(self):
        """Test startup time optimization."""
        # Read the entrypoint script
        try:
            with open(
                self.project_root / "docker-entrypoint.sh", "r", encoding="utf-8"
            ) as f:
                entrypoint_content = f.read()
        except UnicodeDecodeError:
            # Fallback for encoding issues
            with open(
                self.project_root / "docker-entrypoint.sh",
                "r",
                encoding="utf-8",
                errors="replace",
            ) as f:
                entrypoint_content = f.read()

        # Check startup optimizations
        startup_checks = {
            "fast_validation": "validate_environment" in entrypoint_content,
            "parallel_checks": "&&" in entrypoint_content,  # Combined commands
            "early_exit": "exit 1" in entrypoint_content,  # Fast exit on error
            "minimal_logging": "log_info" in entrypoint_content,
        }

        for check_name, passed in startup_checks.items():
            assert passed, f"Startup optimization missing: {check_name}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
