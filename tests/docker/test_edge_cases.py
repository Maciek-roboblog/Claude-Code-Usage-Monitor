"""
Edge case tests and error handling for the Docker implementation.
"""

import json
import socket
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from contextlib import contextmanager


class TestDockerEdgeCases:
    """Tests for edge cases in the Docker implementation."""

    def test_empty_data_directory_handling(self, empty_data_dir, docker_utils):
        """Test handling of an empty data directory via a real HTTP server."""
        from http.client import HTTPConnection

        # Simulate the Docker environment with an empty directory
        original_env = docker_utils.simulate_docker_environment(
            {"CLAUDE_DATA_PATH": str(empty_data_dir)}
        )

        try:
            with patch(
                "scripts.health_server.get_default_data_paths"
            ) as mock_get_paths:
                mock_get_paths.return_value = [str(empty_data_dir)]

                from http.server import HTTPServer

                from scripts.health_server import HealthCheckHandler

                # Find a free port
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("localhost", 0))
                    port = s.getsockname()[1]

                server = HTTPServer(("localhost", port), HealthCheckHandler)
                @contextmanager
                def run_test_server(handler_class, port):
                    server = HTTPServer(("localhost", port), handler_class)
                    thread = threading.Thread(target=server.serve_forever, daemon=True)
                    thread.start()
                    time.sleep(0.2)  # Let the server start
                    try:
                        yield server
                    finally:
                        server.shutdown()
                        thread.join(timeout=2)
                        if thread.is_alive():
                            server.server_close()

                with run_test_server(HealthCheckHandler, port) as server:
                    conn = HTTPConnection("localhost", port)
                    conn.request("GET", "/health")
                    resp = conn.getresponse()
                    data = resp.read()
                    assert resp.status == 503  # unhealthy
                    health_status = json.loads(data)
                    assert health_status["status"] == "unhealthy"
                    assert (
                        health_status["checks"]["data_access"]["status"] == "unhealthy"
                    )

        finally:
            docker_utils.restore_environment(original_env)

    def test_corrupted_jsonl_files_handling(self, temp_data_dir, docker_utils):
        """Test handling of corrupted JSONL files via a real HTTP server."""
        from http.client import HTTPConnection

        # Create a corrupted JSONL file
        corrupted_file = temp_data_dir / "corrupted.jsonl"
        with open(corrupted_file, "w") as f:
            f.write('{"invalid": json syntax}\n')
            f.write("not json at all\n")
            f.write('{"missing": "closing_brace"\n')

        original_env = docker_utils.simulate_docker_environment(
            {"CLAUDE_DATA_PATH": str(temp_data_dir)}
        )

        try:
            with patch(
                "scripts.health_server.get_default_data_paths"
            ) as mock_get_paths, patch(
                "scripts.health_server.analyze_usage"
            ) as mock_analyze:
                mock_get_paths.return_value = [str(temp_data_dir)]
                mock_analyze.side_effect = Exception("JSON parsing error")

                from http.server import HTTPServer

                from scripts.health_server import HealthCheckHandler

                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("localhost", 0))
                    port = s.getsockname()[1]

                server = HTTPServer(("localhost", port), HealthCheckHandler)

                def run_server():
                    server.serve_forever()

                thread = threading.Thread(target=run_server, daemon=True)
                thread.start()
                time.sleep(0.2)

                try:
                    conn = HTTPConnection("localhost", port)
                    conn.request("GET", "/health")
                    resp = conn.getresponse()
                    data = resp.read()
                    assert resp.status == 503  # unhealthy
                    health_status = json.loads(data)
                    assert health_status["status"] == "unhealthy"
                    assert health_status["checks"]["analysis"]["status"] == "unhealthy"
                    assert "error" in health_status["checks"]["analysis"]
                finally:
                    server.shutdown()
                    thread.join(timeout=1)

        finally:
            docker_utils.restore_environment(original_env)

    def test_permission_denied_data_directory(self, temp_data_dir, docker_utils):
        """Test handling of permission errors via a real HTTP server."""
        from http.client import HTTPConnection

        # Create a file with restrictive permissions
        restricted_file = temp_data_dir / "restricted.jsonl"
        with open(restricted_file, "w") as f:
            f.write('{"test": "data"}\n')

        # Simulate a permission error
        original_env = docker_utils.simulate_docker_environment(
            {"CLAUDE_DATA_PATH": str(temp_data_dir)}
        )

        try:
            with patch(
                "scripts.health_server.get_default_data_paths"
            ) as mock_get_paths:
                mock_get_paths.side_effect = PermissionError("Permission denied")

                from http.server import HTTPServer

                from scripts.health_server import HealthCheckHandler

                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("localhost", 0))
                    port = s.getsockname()[1]

                server = HTTPServer(("localhost", port), HealthCheckHandler)

                def run_server():
                    server.serve_forever()

                thread = threading.Thread(target=run_server, daemon=True)
                thread.start()
                time.sleep(0.2)

                try:
                    conn = HTTPConnection("localhost", port)
                    conn.request("GET", "/health")
                    resp = conn.getresponse()
                    data = resp.read()
                    assert resp.status == 503  # unhealthy
                    health_status = json.loads(data)
                    assert health_status["status"] == "unhealthy"
                    assert "error" in health_status["checks"]["data_access"]
                finally:
                    server.shutdown()
                    thread.join(timeout=1)

        finally:
            docker_utils.restore_environment(original_env)

    def test_very_large_jsonl_files(self, temp_data_dir, docker_utils):
        """Test handling of very large JSONL files via a real HTTP server."""
        from http.client import HTTPConnection

        # Create a very large JSONL file
        large_file = temp_data_dir / "very_large.jsonl"
        with open(large_file, "w") as f:
            for i in range(100000):
                entry = {
                    "timestamp": f"2024-01-{(i % 31) + 1:02d}T{(i % 24):02d}:30:00Z",
                    "model": f"claude-3-{'sonnet' if i % 3 == 0 else 'haiku'}-20240229",
                    "usage": {
                        "input_tokens": 500 + (i % 2000),
                        "output_tokens": 200 + (i % 1000),
                    },
                }
                f.write(json.dumps(entry) + "\n")

        original_env = docker_utils.simulate_docker_environment(
            {"CLAUDE_DATA_PATH": str(temp_data_dir)}
        )

        try:
            with patch(
                "scripts.health_server.get_default_data_paths"
            ) as mock_get_paths:
                mock_get_paths.return_value = [str(temp_data_dir)]

                from http.server import HTTPServer

                from scripts.health_server import HealthCheckHandler
                from contextlib import contextmanager

                @contextmanager
                def run_test_server(handler, port):
                    server = HTTPServer(("localhost", port), handler)

                    def run_server():
                        server.serve_forever()

                    thread = threading.Thread(target=run_server, daemon=True)
                    thread.start()
                    time.sleep(0.2)

                    try:
                        yield server
                    finally:
                        server.shutdown()
                        thread.join(timeout=1)

                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("localhost", 0))
                    port = s.getsockname()[1]

                server = HTTPServer(("localhost", port), HealthCheckHandler)

                def run_server():
                    server.serve_forever()

                thread = threading.Thread(target=run_server, daemon=True)
                thread.start()
                time.sleep(0.2)

                try:
                    conn = HTTPConnection("localhost", port)
                    conn.request("GET", "/health")
                    resp = conn.getresponse()
                    data = resp.read()
                    assert resp.status in (200, 503)
                    health_status = json.loads(data)
                    assert health_status["status"] in ("healthy", "unhealthy")
                    assert "data_access" in health_status["checks"]
                finally:
                    server.shutdown()
                    thread.join(timeout=1)

        finally:
            docker_utils.restore_environment(original_env)

    def test_malformed_environment_variables(self, docker_utils):
        """Test handling of malformed environment variables."""
        malformed_env = {
            "CLAUDE_PLAN": "",  # Empty
            "CLAUDE_THEME": "invalid_theme",
            "CLAUDE_REFRESH_INTERVAL": "not_a_number",
            "CLAUDE_DEBUG_MODE": "maybe",  # Not a boolean
            "CLAUDE_TIMEZONE": "Invalid/Timezone",
        }

        errors = docker_utils.validate_env_vars(malformed_env)

        # Should detect multiple errors
        assert len(errors) >= 2, f"Not enough errors detected: {errors}"

    def test_dockerfile_parsing_edge_cases(self):
        """Test edge cases in Dockerfile parsing."""
        dockerfile_path = Path(__file__).parent.parent.parent / "Dockerfile"

        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Test parsing with empty lines and comments
        lines = content.split("\n")

        # Count non-empty, non-comment lines
        instruction_lines = [
            line.strip()
            for line in lines
            if line.strip() and not line.strip().startswith("#")
        ]

        assert len(instruction_lines) > 10, "Dockerfile too simple"

        # Check for malformed syntax
        for line in instruction_lines:
            if line.startswith(("FROM", "RUN", "COPY", "ENV")):
                # Instructions should have content after the keyword
                parts = line.split(" ", 1)
                assert len(parts) >= 2, f"Malformed instruction: {line}"

    def test_docker_compose_parsing_edge_cases(self):
        """Test edge cases in docker-compose.yml parsing."""

        compose_path = Path(__file__).parent.parent.parent / "docker-compose.yml"

        with open(compose_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Test YAML parsing with various encodings
        try:
            compose_config = yaml.safe_load(content)
            assert isinstance(compose_config, dict)

            # Check deep structure
            service = compose_config["services"]["claude-monitor"]

            # Test for missing default values
            env_vars = service["environment"]
            for key, value in env_vars.items():
                assert value is not None, f"None value for {key}"
                assert str(value).strip() != "", f"Empty value for {key}"

        except yaml.YAMLError as e:
            pytest.fail(f"YAML parsing error: {e}")


class TestDockerErrorRecovery:
    """Docker error recovery tests."""

    def test_container_restart_behavior(self):
        """Test container restart behavior."""

        compose_path = Path(__file__).parent.parent.parent / "docker-compose.yml"

        with open(compose_path, "r", encoding="utf-8") as f:
            compose_config = yaml.safe_load(f)

        service = compose_config["services"]["claude-monitor"]

        # Check restart policy
        assert "restart" in service
        restart_policy = service["restart"]

        # Acceptable restart policies
        valid_policies = ["unless-stopped", "always", "on-failure"]
        assert restart_policy in valid_policies

    def test_graceful_shutdown_handling(self):
        """Test graceful shutdown handling."""
        entrypoint_path = Path(__file__).parent.parent.parent / "docker-entrypoint.sh"

        with open(entrypoint_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check signal handling
        assert "cleanup()" in content
        assert "trap cleanup SIGTERM SIGINT SIGQUIT" in content

        # Check that cleanup kills background processes
        assert "jobs -p | xargs" in content


class TestDockerSecurityEdgeCases:
    """Security and edge case tests."""

    def test_container_escape_prevention(self):
        """Test container escape prevention."""
        dockerfile_path = Path(__file__).parent.parent.parent / "Dockerfile"

        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for dangerous configurations
        dangerous_patterns = [
            "--privileged",
            "docker.sock",
            "/proc/",
            "/sys/",
            "CAP_SYS_ADMIN",
            "NET_ADMIN",
        ]

        for pattern in dangerous_patterns:
            assert pattern not in content, (
                f"Dangerous configuration detected: {pattern}"
            )

    def test_secrets_exposure_prevention(self):
        """Test prevention of secrets exposure."""
        # Check configuration files
        config_files = [
            Path(__file__).parent.parent.parent / "Dockerfile",
            Path(__file__).parent.parent.parent / "docker-compose.yml",
            Path(__file__).parent.parent.parent / "docker-entrypoint.sh",
        ]

        sensitive_patterns = ["password", "secret", "api_key", "token", "credential"]

        for config_file in config_files:
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    content = f.read().lower()

                for pattern in sensitive_patterns:
                    # Allow references to environment variables
                    if pattern in content and not any(
                        env_ref in content
                        for env_ref in ["${", "$", "environment", "env_file"]
                    ):
                        pytest.fail(
                            f"Possible secret exposure '{pattern}' in {config_file}"
                        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
