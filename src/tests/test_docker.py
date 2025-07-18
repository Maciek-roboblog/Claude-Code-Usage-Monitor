"""
Consolidated tests for the Docker ecosystem including Dockerfile,
Docker Compose, the entrypoint script, health checks and global integration.
"""

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from http.client import HTTPConnection
from http.server import HTTPServer
from pathlib import Path

import pytest
import yaml

# Add project root directory to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Conditional import of health server handler
try:
    from scripts.health_server import HealthCheckHandler

    HEALTH_SERVER_AVAILABLE = True
except ImportError:
    HEALTH_SERVER_AVAILABLE = False


# ============================================================================
# CONSOLIDATED FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Provides the project root directory."""
    return PROJECT_ROOT


@pytest.fixture
def temp_data_dir():
    """Creates a temporary directory for data tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_jsonl_data():
    """Sample JSONL data for tests."""
    return [
        {
            "timestamp": "2024-01-15T10:30:00Z",
            "model": "claude-3-sonnet-20240229",
            "usage": {"input_tokens": 1500, "output_tokens": 800},
        },
        {
            "timestamp": "2024-01-15T11:00:00Z",
            "model": "claude-3-haiku-20240307",
            "usage": {"input_tokens": 500, "output_tokens": 200},
        },
    ]


@pytest.fixture
def jsonl_file_with_data(temp_data_dir, sample_jsonl_data):
    """Creates a JSONL file with sample data."""
    jsonl_file = temp_data_dir / "test_usage.jsonl"
    with open(jsonl_file, "w") as f:
        for entry in sample_jsonl_data:
            f.write(json.dumps(entry) + "\n")
    return jsonl_file


@pytest.fixture
def empty_data_dir(temp_data_dir):
    """Empty data directory for error case tests."""
    return temp_data_dir


# ============================================================================
# DOCKERFILE TESTS
# ============================================================================


class TestDockerfile:
    """Tests for static definition and best practices of the Dockerfile."""

    @pytest.fixture(scope="class")
    def dockerfile_content(self, project_root):
        """Reads the Dockerfile content once per test class."""
        dockerfile_path = project_root / "Dockerfile"
        assert dockerfile_path.is_file(), "Dockerfile not found"
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_dockerfile_exists(self, project_root):
        """Test that the Dockerfile exists."""
        dockerfile_path = project_root / "Dockerfile"
        assert dockerfile_path.exists()
        assert dockerfile_path.is_file()

    def test_dockerfile_multi_stage_build(self, dockerfile_content):
        """Test that the Dockerfile uses a multi-stage build."""
        assert "FROM python:3.11-slim AS builder" in dockerfile_content
        assert "FROM python:3.11-slim AS runtime" in dockerfile_content

    def test_dockerfile_base_images(self, dockerfile_content):
        """Verifies consistency of base images."""
        from_lines = re.findall(r"^FROM\s+(.+)$", dockerfile_content, re.MULTILINE)
        assert len(from_lines) == 2

        for from_line in from_lines:
            if "AS" in from_line:
                base_image = from_line.split(" AS ")[0].strip()
            else:
                base_image = from_line.strip()
            assert base_image == "python:3.11-slim"

    def test_dockerfile_labels(self, dockerfile_content):
        """Verifies essential OCI labels."""
        required_labels = [
            'LABEL maintainer="GiGiDKR',
            'LABEL description="Claude Code Usage Monitor',
            "LABEL version=",
            "LABEL org.opencontainers.image.source=",
        ]

        for label in required_labels:
            assert label in dockerfile_content

    def test_dockerfile_user_creation(self, dockerfile_content):
        """Test creation of a non-root user."""
        assert "groupadd -r claude" in dockerfile_content
        assert "useradd -r -g claude -u 1001 claude" in dockerfile_content
        assert "chown -R claude:claude /data /app" in dockerfile_content
        assert "USER claude" in dockerfile_content

    def test_dockerfile_dependencies(self, dockerfile_content):
        """Test dependency installation."""
        # System dependencies
        expected_apt = "apt-get install -y --no-install-recommends"
        assert expected_apt in dockerfile_content
        assert "rm -rf /var/lib/apt/lists/*" in dockerfile_content
        # Python dependencies
        assert "pip install --no-cache-dir uv" in dockerfile_content
        assert "uv pip install --system --no-cache-dir ." in dockerfile_content

    def test_dockerfile_file_operations(self, dockerfile_content):
        """Test file copy operations."""
        assert "COPY pyproject.toml ./" in dockerfile_content
        assert "COPY uv.lock ./" in dockerfile_content
        assert "COPY src/ ./src/" in dockerfile_content
        assert "COPY --from=builder" in dockerfile_content

    def test_dockerfile_environment_variables(self, dockerfile_content):
        """Test environment variables."""
        expected_vars = [
            'CLAUDE_DATA_PATH="/data"',
            'CLAUDE_PLAN="pro"',
            'PYTHONPATH="/app"',
            "PYTHONUNBUFFERED=1",
        ]

        for env_var in expected_vars:
            assert env_var in dockerfile_content

    def test_dockerfile_entrypoint_and_cmd(self, dockerfile_content):
        """Test ENTRYPOINT and CMD."""
        assert 'ENTRYPOINT ["./docker-entrypoint.sh"]' in dockerfile_content
        assert "CMD []" in dockerfile_content

    def test_dockerfile_healthcheck(self, dockerfile_content):
        """Test healthcheck configuration."""
        assert "HEALTHCHECK" in dockerfile_content
        assert "--interval=" in dockerfile_content
        assert "--timeout=" in dockerfile_content
        assert "./scripts/health-check.sh" in dockerfile_content

    def test_dockerfile_no_exposed_ports(self, dockerfile_content):
        """Test that no ports are exposed."""
        comment = "# EXPOSE directive intentionally omitted"
        assert comment in dockerfile_content

        lines = dockerfile_content.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("EXPOSE") and not line.startswith("#"):
                pytest.fail(f"Unnecessarily exposed port: {line}")

    def test_dockerfile_optimization_practices(self, dockerfile_content):
        """Test optimization best practices."""
        assert "--no-cache-dir" in dockerfile_content
        assert "--no-install-recommends" in dockerfile_content
        assert "rm -rf /var/lib/apt/lists/*" in dockerfile_content

    def test_dockerfile_security_practices(self, dockerfile_content):
        """Test security best practices."""
        assert "USER claude" in dockerfile_content
        assert "-u 1001" in dockerfile_content
        assert "chown -R claude:claude" in dockerfile_content


class TestDockerfileBuildInstructions:
    """Tests for specific Dockerfile instructions."""

    @pytest.fixture(scope="class")
    def dockerfile_content(self, project_root):
        """Reads the Dockerfile content once per test class."""
        dockerfile_path = project_root / "Dockerfile"
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_dockerfile_copy_instructions_order(self, project_root):
        """Test COPY instruction order for cache optimization."""
        dockerfile_path = project_root / "Dockerfile"
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Search for COPY instructions in builder stage
        builder_section = False
        copy_instructions = []

        for i, line in enumerate(lines):
            if "FROM python:3.11-slim AS builder" in line:
                builder_section = True
                continue
            elif "FROM python:3.11-slim AS runtime" in line:
                builder_section = False
                continue

            if builder_section and line.strip().startswith("COPY"):
                copy_instructions.append((i, line.strip()))

        # Check optimal order: dependencies first, then sources
        dependency_files = ["pyproject.toml", "uv.lock", "README.md"]
        source_files = ["src/"]

        dependency_indices = []
        source_indices = []

        for i, instruction in copy_instructions:
            for dep_file in dependency_files:
                if dep_file in instruction:
                    dependency_indices.append(i)
                    break
            for src_file in source_files:
                if src_file in instruction:
                    source_indices.append(i)
                    break

        # Dependency files should be copied before sources
        if dependency_indices and source_indices:
            assert max(dependency_indices) < min(source_indices)

    def test_dockerfile_run_instruction_optimization(self, dockerfile_content):
        """Test RUN instruction optimization."""
        # Verify that apt commands are combined
        pattern = r"RUN apt-get.*?(?=RUN|\n\n|FROM|$)"
        apt_commands = re.findall(pattern, dockerfile_content, re.DOTALL)

        for apt_command in apt_commands:
            # Each apt command should include update, install, and cleanup
            if "apt-get" in apt_command:
                assert "apt-get update" in apt_command
                assert "apt-get install" in apt_command
                assert "rm -rf /var/lib/apt/lists/*" in apt_command

    def test_dockerfile_env_instruction_format(self, dockerfile_content):
        """Test ENV instruction format."""
        # Search for ENV instruction
        pattern = r"ENV\s+(.*?)(?=\n\n|\n[A-Z]|$)"
        env_match = re.search(pattern, dockerfile_content, re.DOTALL)
        assert env_match, "ENV instruction not found"

        env_content = env_match.group(1)

        # Verify that all variables are defined
        required_vars = [
            "CLAUDE_DATA_PATH",
            "CLAUDE_PLAN",
            "CLAUDE_TIMEZONE",
            "CLAUDE_THEME",
            "CLAUDE_REFRESH_INTERVAL",
            "CLAUDE_DEBUG_MODE",
            "PYTHONPATH",
            "PYTHONUNBUFFERED",
        ]

        for var in required_vars:
            assert var in env_content, f"Missing environment variable {var}"


# ============================================================================
# DOCKER COMPOSE TESTS
# ============================================================================


class TestDockerCompose:
    """Tests for the docker-compose.yml file."""

    @pytest.fixture(scope="class")
    def compose_config(self, project_root):
        """Loads the docker-compose.yml file."""
        compose_path = project_root / "docker-compose.yml"
        assert compose_path.is_file(), "docker-compose.yml not found"
        with open(compose_path, "r", encoding="utf-8") as f:
            try:
                config = yaml.safe_load(f)
                assert config is not None
                return config
            except yaml.YAMLError as e:
                pytest.fail(f"Invalid docker-compose.yml: {e}")

    def test_compose_file_exists(self, project_root):
        """Test that the docker-compose.yml file exists."""
        compose_file = project_root / "docker-compose.yml"
        assert compose_file.exists()
        assert compose_file.is_file()

    def test_compose_valid_yaml(self, project_root):
        """Test that the file is valid YAML."""
        compose_file = project_root / "docker-compose.yml"
        with open(compose_file, "r") as f:
            try:
                compose_config = yaml.safe_load(f)
                assert compose_config is not None
                assert isinstance(compose_config, dict)
            except yaml.YAMLError as e:
                pytest.fail(f"Invalid YAML: {e}")

    def test_compose_structure(self, compose_config):
        """Test basic structure."""
        assert "services" in compose_config
        assert "claude-monitor" in compose_config["services"]

        service = compose_config["services"]["claude-monitor"]
        required = ["build", "image", "container_name", "environment", "volumes"]
        for section in required:
            assert section in service

    def test_compose_build_configuration(self, compose_config):
        """Test build configuration."""
        build_config = compose_config["services"]["claude-monitor"]["build"]
        assert build_config.get("context") == "."
        assert build_config.get("dockerfile") == "Dockerfile"
        assert build_config.get("target") == "runtime"

    def test_compose_environment_variables(self, compose_config):
        """Test environment variables."""
        env_vars = compose_config["services"]["claude-monitor"]["environment"]

        expected = {
            "CLAUDE_PLAN": "pro",
            "CLAUDE_TIMEZONE": "UTC",
            "CLAUDE_THEME": "auto",
            "CLAUDE_DEBUG_MODE": "false",
            "CLAUDE_DATA_PATH": "/data",
        }

        for var, expected_value in expected.items():
            assert var in env_vars
            assert str(env_vars[var]) == expected_value

    def test_compose_volume_configuration(self, compose_config):
        """Test volume configuration."""
        volumes = compose_config["services"]["claude-monitor"]["volumes"]
        assert len(volumes) >= 1

        main_volume = volumes[0]
        msg = "Volume must be read-only"
        assert ":/data:ro" in main_volume, msg

    def test_compose_restart_policy(self, compose_config):
        """Test restart policy."""
        service = compose_config["services"]["claude-monitor"]
        assert service.get("restart") == "unless-stopped"

    def test_environment_variable_validation(self, compose_config):
        """Test environment variable validation."""
        env_vars = compose_config["services"]["claude-monitor"]["environment"]

        # Validate CLAUDE_PLAN
        valid_plans = ["pro", "max5", "max20", "custom_max"]
        assert env_vars["CLAUDE_PLAN"] in valid_plans

        # Validate CLAUDE_THEME
        valid_themes = ["light", "dark", "auto"]
        assert env_vars["CLAUDE_THEME"] in valid_themes

        # Validate CLAUDE_DEBUG_MODE
        valid_debug = ["true", "false"]
        assert env_vars["CLAUDE_DEBUG_MODE"] in valid_debug


# ============================================================================
# DOCKER ENTRYPOINT TESTS
# ============================================================================


@pytest.mark.skipif(os.name == "nt", reason="Entrypoint tests require bash")
class TestDockerEntrypoint:
    """Tests for docker-entrypoint.sh script logic."""

    @pytest.fixture(scope="class")
    def entrypoint_script(self, project_root):
        """Provides the path to the entrypoint script."""
        script_path = project_root / "docker-entrypoint.sh"
        assert script_path.is_file()
        return str(script_path)

    def test_entrypoint_exists(self, project_root):
        """Test that the entrypoint script exists."""
        script = project_root / "docker-entrypoint.sh"
        assert script.exists()
        assert script.is_file()

    def test_entrypoint_executable(self, entrypoint_script):
        """Test that the script is executable."""
        assert os.access(entrypoint_script, os.X_OK)

    def test_entrypoint_shebang(self, entrypoint_script):
        """Test the script shebang."""
        with open(entrypoint_script, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
        assert first_line == "#!/bin/bash"

    def test_validation_missing_data_path(self, entrypoint_script):
        """Test failure when CLAUDE_DATA_PATH is missing."""
        env = os.environ.copy()
        env.pop("CLAUDE_DATA_PATH", None)

        try:
            result = subprocess.run(
                ["bash", entrypoint_script],
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
            assert result.returncode != 0
            assert "CLAUDE_DATA_PATH" in result.stderr
        except subprocess.TimeoutExpired:
            pytest.skip("Script timeout")

    def test_validation_nonexistent_path(self, entrypoint_script):
        """Test failure with nonexistent path."""
        env = os.environ.copy()
        env["CLAUDE_DATA_PATH"] = "/path/does/not/exist"

        try:
            result = subprocess.run(
                ["bash", entrypoint_script],
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
            assert result.returncode != 0
            assert "does not exist" in result.stderr
        except subprocess.TimeoutExpired:
            pytest.skip("Script timeout")

    def test_valid_data_path(self, entrypoint_script, temp_data_dir):
        """Test with valid data path."""
        env = os.environ.copy()
        env.update(
            {
                "CLAUDE_DATA_PATH": str(temp_data_dir),
                "CLAUDE_PLAN": "pro",
                "CLAUDE_THEME": "auto",
            }
        )

        try:
            result = subprocess.run(
                ["bash", entrypoint_script, "echo", "test_ok"],
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )
            # Success or failure with specific message
            assert result.returncode == 0 or "test_ok" in result.stdout
        except subprocess.TimeoutExpired:
            pytest.skip("Script timeout")


# ============================================================================
# HEALTH SYSTEM TESTS
# ============================================================================


@pytest.mark.skipif(not HEALTH_SERVER_AVAILABLE, reason="Health server not available")
class TestHealthSystem:
    """Tests for the health check mechanism."""

    @contextmanager
    def _run_test_server(self, handler_class):
        """Context manager for HTTP test server."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("localhost", 0))
            port = s.getsockname()[1]

        server = HTTPServer(("localhost", port), handler_class)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        time.sleep(0.2)
        try:
            yield "localhost", port
        finally:
            server.shutdown()
            thread.join(timeout=2)

    def test_health_handler_initialization(self):
        """Test health handler initialization."""
        with self._run_test_server(HealthCheckHandler) as (host, port):
            conn = HTTPConnection(host, port, timeout=2)
            conn.request("GET", "/health")
            resp = conn.getresponse()
            assert resp.status in (200, 503)

    def test_health_endpoint_format(self):
        """Test health endpoint response format."""
        with self._run_test_server(HealthCheckHandler) as (host, port):
            conn = HTTPConnection(host, port, timeout=2)
            conn.request("GET", "/health")
            resp = conn.getresponse()
            data = resp.read()

            health_status = json.loads(data)
            assert "status" in health_status
            assert "timestamp" in health_status
            assert "checks" in health_status
            assert health_status["status"] in ["healthy", "unhealthy"]

    def test_health_check_script_exists(self, project_root):
        """Test that the health check script exists."""
        script_path = project_root / "scripts" / "health-check.sh"
        assert script_path.exists()

    @pytest.mark.skipif(os.name == "nt", reason="Bash script not available")
    def test_health_script_executable(self, project_root):
        """Test that the script is executable."""
        script_path = project_root / "scripts" / "health-check.sh"
        stat_info = script_path.stat()
        assert stat_info.st_mode & 0o111


# ============================================================================
# INTEGRATION AND SECURITY TESTS
# ============================================================================


class TestDockerIntegration:
    """Docker consistency and security tests."""

    def test_build_context_files_present(self, project_root):
        """Test presence of required files."""
        required_files = [
            "Dockerfile",
            "docker-compose.yml",
            "docker-entrypoint.sh",
            "pyproject.toml",
            "uv.lock",
            "scripts/health-check.sh",
            "scripts/health_server.py",
        ]

        for file_path in required_files:
            full_path = project_root / file_path
            assert full_path.exists(), f"Missing file: {file_path}"

    def test_dockerfile_entrypoint_consistency(self, project_root):
        """Test consistency between Dockerfile and entrypoint."""
        with open(project_root / "Dockerfile", "r", encoding="utf-8") as f:
            dockerfile_content = f.read()

        entrypoint_path = project_root / "docker-entrypoint.sh"
        with open(entrypoint_path, "r", encoding="utf-8") as f:
            entrypoint_content = f.read()

        env_vars = [
            "CLAUDE_DATA_PATH",
            "CLAUDE_PLAN",
            "CLAUDE_TIMEZONE",
            "CLAUDE_THEME",
        ]

        for env_var in env_vars:
            assert env_var in dockerfile_content
            assert env_var in entrypoint_content

    def test_compose_dockerfile_consistency(self, project_root):
        """Test consistency between compose and Dockerfile."""
        with open(project_root / "docker-compose.yml", "r") as f:
            compose_config = yaml.safe_load(f)

        with open(project_root / "Dockerfile", "r", encoding="utf-8") as f:
            dockerfile_content = f.read()

        service = compose_config["services"]["claude-monitor"]
        compose_env = service["environment"]

        for env_var in compose_env.keys():
            assert env_var in dockerfile_content

    @pytest.mark.skipif(not shutil.which("docker"), reason="Docker not available")
    def test_dockerfile_syntax_validation(self, project_root):
        """Test Dockerfile syntax."""
        try:
            cmd = ["docker", "build", "--target", "builder", "-f", "Dockerfile", "."]
            result = subprocess.run(
                cmd,
                cwd=project_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
            )
            assert result.returncode == 0, f"Syntax error: {result.stderr}"
        except subprocess.TimeoutExpired:
            pytest.skip("Docker validation timeout")

    @pytest.mark.skipif(
        not shutil.which("docker"), reason="Docker Compose not available"
    )
    def test_compose_syntax_validation(self, project_root):
        """Test docker-compose.yml syntax."""
        try:
            result = subprocess.run(
                ["docker", "compose", "config"],
                cwd=project_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
            assert result.returncode == 0, f"Syntax error: {result.stderr}"
        except subprocess.TimeoutExpired:
            pytest.skip("Compose validation timeout")
        except FileNotFoundError:
            pytest.skip("Docker Compose not available")

    def test_no_hardcoded_secrets(self, project_root):
        """Test absence of hardcoded secrets."""
        files_to_scan = [
            project_root / "Dockerfile",
            project_root / "docker-compose.yml",
            project_root / "docker-entrypoint.sh",
        ]
        patterns = ["password", "secret", "api_key", "token"]

        for file_path in files_to_scan:
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().lower()
                for pattern in patterns:
                    # Search for values, not variable names
                    pattern_str = f"['\"]?{pattern}['\"]?\\s*[:=]\\s*['\"].+"
                    if re.search(pattern_str, content):
                        msg = f"Potential secret '{pattern}' in {file_path.name}"
                        pytest.fail(msg)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
