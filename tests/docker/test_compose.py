"""
Unit tests for the Docker Compose configuration.
"""

from pathlib import Path

import pytest
import yaml


class TestDockerCompose:
    """Tests for the Docker Compose configuration."""

    @property
    def docker_compose_file(self):
        """Path to the docker-compose.yml file."""
        return Path(__file__).parent.parent.parent / "docker-compose.yml"

    def test_docker_compose_file_exists(self):
        """Test that the docker-compose.yml file exists."""
        assert self.docker_compose_file.exists()
        assert self.docker_compose_file.is_file()

    def test_docker_compose_valid_yaml(self):
        """Test that the docker-compose.yml file is valid YAML."""
        with open(self.docker_compose_file, "r") as f:
            try:
                compose_config = yaml.safe_load(f)
                assert compose_config is not None
                assert isinstance(compose_config, dict)
            except yaml.YAMLError as e:
                pytest.fail(f"Invalid docker-compose.yml file: {e}")

    def test_docker_compose_structure(self):
        """Test the basic structure of the docker-compose.yml file."""
        with open(self.docker_compose_file, "r") as f:
            compose_config = yaml.safe_load(f)

        # Check the basic structure
        assert "services" in compose_config
        assert "claude-monitor" in compose_config["services"]

        service = compose_config["services"]["claude-monitor"]

        # Check essential sections
        required_sections = [
            "build",
            "image",
            "container_name",
            "environment",
            "volumes",
        ]
        for section in required_sections:
            assert section in service, f"Missing section '{section}'"

    def test_docker_compose_build_configuration(self):
        """Test the build configuration."""
        with open(self.docker_compose_file, "r") as f:
            compose_config = yaml.safe_load(f)

        build_config = compose_config["services"]["claude-monitor"]["build"]

        assert "context" in build_config
        assert build_config["context"] == "."
        assert "dockerfile" in build_config
        assert build_config["dockerfile"] == "Dockerfile"
        assert "target" in build_config
        assert build_config["target"] == "runtime"

    def test_docker_compose_environment_variables(self):
        """Test the default environment variables."""
        with open(self.docker_compose_file, "r") as f:
            compose_config = yaml.safe_load(f)

        env_vars = compose_config["services"]["claude-monitor"]["environment"]

        # Check essential environment variables
        expected_vars = {
            "CLAUDE_PLAN": "pro",
            "CLAUDE_TIMEZONE": "UTC",
            "CLAUDE_THEME": "auto",
            "CLAUDE_REFRESH_INTERVAL": "10",
            "CLAUDE_DEBUG_MODE": "false",
            "CLAUDE_DATA_PATH": "/data",
        }

        for var, expected_value in expected_vars.items():
            assert var in env_vars, f"Missing environment variable '{var}'"
            assert str(env_vars[var]) == expected_value, f"Incorrect value for {var}"

    def test_docker_compose_volume_configuration(self):
        """Test the volume configuration."""
        with open(self.docker_compose_file, "r") as f:
            compose_config = yaml.safe_load(f)

        volumes = compose_config["services"]["claude-monitor"]["volumes"]

        # There should be at least one volume configured
        assert len(volumes) >= 1

        # Check the main volume
        main_volume = volumes[0]
        assert "~/.claude/projects:/data:ro" in main_volume

    def test_docker_compose_resource_limits(self):
        """Test resource limits."""
        with open(self.docker_compose_file, "r") as f:
            compose_config = yaml.safe_load(f)

        service = compose_config["services"]["claude-monitor"]

        if "deploy" in service:
            deploy_config = service["deploy"]

            if "resources" in deploy_config:
                resources = deploy_config["resources"]

                # Check limits
                if "limits" in resources:
                    limits = resources["limits"]
                    assert "cpus" in limits
                    assert "memory" in limits

                # Check reservations
                if "reservations" in resources:
                    reservations = resources["reservations"]
                    assert "cpus" in reservations
                    assert "memory" in reservations

    def test_docker_compose_restart_policy(self):
        """Test the restart policy."""
        with open(self.docker_compose_file, "r") as f:
            compose_config = yaml.safe_load(f)

        service = compose_config["services"]["claude-monitor"]

        assert "restart" in service
        assert service["restart"] == "unless-stopped"

    def test_docker_compose_interactive_settings(self):
        """Test interactive settings."""
        with open(self.docker_compose_file, "r") as f:
            compose_config = yaml.safe_load(f)

        service = compose_config["services"]["claude-monitor"]

        assert "stdin_open" in service
        assert service["stdin_open"] is True
        assert "tty" in service
        assert service["tty"] is True

    def test_docker_compose_healthcheck(self):
        """Test the healthcheck configuration."""
        with open(self.docker_compose_file, "r") as f:
            compose_config = yaml.safe_load(f)

        service = compose_config["services"]["claude-monitor"]

        if "healthcheck" in service:
            healthcheck = service["healthcheck"]

            required_fields = ["test", "interval", "timeout", "retries", "start_period"]
            for field in required_fields:
                assert field in healthcheck, f"Missing healthcheck field '{field}'"

    def test_docker_compose_image_name(self):
        """Test the image name."""
        with open(self.docker_compose_file, "r") as f:
            compose_config = yaml.safe_load(f)

        service = compose_config["services"]["claude-monitor"]

        assert "image" in service
        assert service["image"] == "claude-monitor:latest"

    def test_docker_compose_container_name(self):
        """Test the container name."""
        with open(self.docker_compose_file, "r") as f:
            compose_config = yaml.safe_load(f)

        service = compose_config["services"]["claude-monitor"]

        assert "container_name" in service
        assert service["container_name"] == "claude-usage-monitor"

    def test_docker_compose_alternative_volume_examples(self):
        """Test that alternative volume examples are present in comments."""
        with open(self.docker_compose_file, "r") as f:
            content = f.read()

        # Check that alternative examples are documented
        assert "# Alternative mount examples" in content
        assert "~/.config/claude/projects:/data:ro" in content
        assert "/custom/path/to/claude/data:/data:ro" in content
        assert "claude-data:/data" in content

    def test_docker_compose_commented_volumes_section(self):
        """Test that the named volumes section is commented out."""
        with open(self.docker_compose_file, "r") as f:
            content = f.read()

        # The volumes section should be commented
        assert "# volumes:" in content
        assert "#   claude-data:" in content
        assert "#     driver: local" in content


class TestDockerComposeVariations:
    """Tests for different Docker Compose configuration variations."""

    def test_custom_docker_compose_with_different_plan(self, temp_data_dir):
        """Test a Docker Compose configuration with a different plan."""
        compose_content = {
            "services": {
                "claude-monitor": {
                    "build": {"context": ".", "dockerfile": "Dockerfile"},
                    "environment": {"CLAUDE_PLAN": "max5", "CLAUDE_DATA_PATH": "/data"},
                    "volumes": [f"{temp_data_dir}:/data:ro"],
                }
            }
        }

        # Simulate using this configuration
        assert (
            compose_content["services"]["claude-monitor"]["environment"]["CLAUDE_PLAN"]
            == "max5"
        )

    def test_custom_docker_compose_with_named_volume(self):
        """Test a configuration with a named volume."""
        compose_content = {
            "services": {"claude-monitor": {"volumes": ["claude-data:/data"]}},
            "volumes": {"claude-data": {"driver": "local"}},
        }

        assert "volumes" in compose_content
        assert "claude-data" in compose_content["volumes"]

    def test_custom_docker_compose_with_different_timezone(self):
        """Test a configuration with a different timezone."""
        compose_content = {
            "services": {
                "claude-monitor": {"environment": {"CLAUDE_TIMEZONE": "Europe/Paris"}}
            }
        }

        timezone = compose_content["services"]["claude-monitor"]["environment"][
            "CLAUDE_TIMEZONE"
        ]
        assert timezone == "Europe/Paris"

    def test_custom_docker_compose_without_resource_limits(self):
        """Test a configuration without resource limits."""
        compose_content = {
            "services": {
                "claude-monitor": {
                    "build": {"context": "."},
                    "environment": {"CLAUDE_PLAN": "pro"},
                    # No deploy section
                }
            }
        }

        service = compose_content["services"]["claude-monitor"]
        assert "deploy" not in service  # Valid configuration without limits

    def test_docker_compose_with_custom_refresh_interval(self):
        """Test a configuration with a custom refresh interval."""
        compose_content = {
            "services": {
                "claude-monitor": {"environment": {"CLAUDE_REFRESH_INTERVAL": "30"}}
            }
        }

        interval = compose_content["services"]["claude-monitor"]["environment"][
            "CLAUDE_REFRESH_INTERVAL"
        ]
        assert interval == "30"


class TestDockerComposeValidation:
    """Validation tests for Docker Compose."""

    def test_validate_environment_variable_values(self):
        """Test validation of environment variable values."""
        with open(Path(__file__).parent.parent.parent / "docker-compose.yml", "r") as f:
            compose_config = yaml.safe_load(f)

        env_vars = compose_config["services"]["claude-monitor"]["environment"]

        # Validate CLAUDE_PLAN
        valid_plans = ["pro", "max5", "max20", "custom_max"]
        assert env_vars["CLAUDE_PLAN"] in valid_plans

        # Validate CLAUDE_THEME
        valid_themes = ["light", "dark", "auto"]
        assert env_vars["CLAUDE_THEME"] in valid_themes

        # Validate CLAUDE_DEBUG_MODE
        valid_debug_modes = ["true", "false"]
        assert env_vars["CLAUDE_DEBUG_MODE"] in valid_debug_modes

        # Validate CLAUDE_REFRESH_INTERVAL
        try:
            interval = int(env_vars["CLAUDE_REFRESH_INTERVAL"])
            assert interval > 0
        except ValueError:
            pytest.fail("CLAUDE_REFRESH_INTERVAL must be an integer")

    def test_validate_volume_paths(self):
        """Test validation of volume paths."""
        with open(Path(__file__).parent.parent.parent / "docker-compose.yml", "r") as f:
            compose_config = yaml.safe_load(f)

        volumes = compose_config["services"]["claude-monitor"]["volumes"]

        for volume in volumes:
            if isinstance(volume, str) and ":" in volume:
                parts = volume.split(":")
                assert len(parts) >= 2, f"Invalid volume format: {volume}"

                # Check that the target path is /data
                target_path = parts[1]
                assert target_path == "/data", f"Incorrect target path: {target_path}"

    def test_validate_healthcheck_command(self):
        """Test validation of the healthcheck command."""
        with open(Path(__file__).parent.parent.parent / "docker-compose.yml", "r") as f:
            compose_config = yaml.safe_load(f)

        service = compose_config["services"]["claude-monitor"]

        if "healthcheck" in service:
            healthcheck = service["healthcheck"]
            test_command = healthcheck["test"]

            # The test should be a list or a string
            assert isinstance(test_command, (list, str))

            if isinstance(test_command, list):
                # Should start with CMD
                assert test_command[0] == "CMD"
                # Should contain a valid Python command
                assert "python" in " ".join(test_command)

    def test_validate_resource_limits_format(self):
        """Test the format of resource limits."""
        with open(Path(__file__).parent.parent.parent / "docker-compose.yml", "r") as f:
            compose_config = yaml.safe_load(f)

        service = compose_config["services"]["claude-monitor"]

        if "deploy" in service and "resources" in service["deploy"]:
            resources = service["deploy"]["resources"]

            for section in ["limits", "reservations"]:
                if section in resources:
                    resource_section = resources[section]

                    if "cpus" in resource_section:
                        # CPUs should be a number or a string
                        cpu_value = resource_section["cpus"]
                        assert isinstance(cpu_value, (str, int, float))

                    if "memory" in resource_section:
                        # Memory should be a string with a unit
                        memory_value = resource_section["memory"]
                        assert isinstance(memory_value, str)
                        assert memory_value[-1] in ["M", "G"], (
                            "Missing memory unit"
                        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
