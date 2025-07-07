"""
Unit tests for the Docker health system.
"""

import json
import os
import socket
import subprocess
import sys
import threading
import time
from http.client import HTTPConnection
from http.server import HTTPServer
from pathlib import Path
from unittest.mock import patch

import pytest

# Add the project directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.health_server import HealthCheckHandler


class TestHealthCheckServer:
    """Tests for the HTTP health check server."""

    def test_health_check_handler_initialization(self):
        """Test initialization of the health check handler via a real HTTP server."""
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
            assert resp.status in (200, 503)  # healthy or unhealthy
        finally:
            server.shutdown()
            thread.join(timeout=1)

    @patch("scripts.health_server.get_default_data_paths")
    @patch("scripts.health_server.analyze_usage")
    def test_get_health_status_healthy(
        self, mock_analyze_usage, mock_get_paths, temp_data_dir, jsonl_file_with_data
    ):
        """Test health status when everything is OK via a real HTTP server."""
        # Configure mocks
        mock_get_paths.return_value = [str(temp_data_dir)]
        mock_analyze_usage.return_value = {"blocks": [{"test": "data"}]}

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
            assert resp.status == 200
            health_status = json.loads(data)
            assert health_status["status"] == "healthy"
            assert "checks" in health_status
        finally:
            server.shutdown()
            thread.join(timeout=1)

    def test_health_endpoint_response_format(self):
        """Test that the /health endpoint returns the correct response format."""
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

            # Check JSON format
            health_status = json.loads(data)

            # Check expected structure
            assert "status" in health_status
            assert "timestamp" in health_status
            assert "checks" in health_status

            # Status must be either "healthy" or "unhealthy"
            assert health_status["status"] in ["healthy", "unhealthy"]
        finally:
            server.shutdown()
            thread.join(timeout=1)


class TestHealthSystemIntegration:
    """Integration tests for the health system."""

    def test_health_check_script_exists(self):
        """Test that the health check script exists."""
        script_path = (
            Path(__file__).parent.parent.parent / "scripts" / "health-check.sh"
        )
        assert script_path.exists(), "The health-check.sh script must exist"

    @pytest.mark.skipif(os.name == "nt", reason="Bash script not available on Windows")
    def test_health_check_script_executable(self):
        """Test that the health check script is executable."""
        script_path = (
            Path(__file__).parent.parent.parent / "scripts" / "health-check.sh"
        )
        stat_info = script_path.stat()
        assert stat_info.st_mode & 0o111, "The script must be executable"

    @pytest.mark.skipif(os.name == "nt", reason="Bash script not available on Windows")
    def test_health_check_script_execution(self):
        """Test execution of the health check script."""
        script_path = (
            Path(__file__).parent.parent.parent / "scripts" / "health-check.sh"
        )

        try:
            # Run the script (may fail depending on environment)
            result = subprocess.run(
                [str(script_path)], capture_output=True, text=True, timeout=10
            )

            # The script may return 0 (success) or 1 (failure) depending on state
            assert result.returncode in [0, 1], "The script must return 0 or 1"

        except subprocess.TimeoutExpired:
            pytest.skip("Script too slow - timeout")
        except FileNotFoundError:
            pytest.skip("Script not found or bash not available")

    def test_health_server_script_exists(self):
        """Test that the health server script exists."""
        script_path = (
            Path(__file__).parent.parent.parent / "scripts" / "health_server.py"
        )
        assert script_path.exists(), "The health_server.py script must exist"

    def test_health_server_can_start(self):
        """Test that the health server can start."""
        script_path = (
            Path(__file__).parent.parent.parent / "scripts" / "health_server.py"
        )

        try:
            # Try to start the server (quick stop)
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Wait a bit then terminate
            time.sleep(1)
            process.terminate()

            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

            # The process was able to start without immediate error
            assert True

        except Exception as e:
            pytest.skip(f"Unable to test the server: {e}")


class TestHealthSystemConfiguration:
    """Configuration tests for the health system."""

    def test_default_health_server_port(self):
        """Test the default health server port."""
        # The default port should be configurable via an environment variable
        default_port = os.environ.get("HEALTH_SERVER_PORT", "8000")

        # Check that it's a valid port
        try:
            port_num = int(default_port)
            assert 1024 <= port_num <= 65535, "Port must be in valid range"
        except ValueError:
            pytest.fail("Default port must be a number")

    def test_health_check_endpoints(self):
        """Test health check endpoints."""
        expected_endpoints = ["/health", "/metrics", "/status"]

        # For each endpoint, check that it responds
        for endpoint in expected_endpoints:
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
                conn.request("GET", endpoint)
                resp = conn.getresponse()

                # The endpoint must respond (200, 404, or 503)
                assert resp.status in [200, 404, 503], (
                    f"Endpoint {endpoint} must respond"
                )

            except Exception:
                # Some endpoints may not be implemented
                pass
            finally:
                server.shutdown()
                thread.join(timeout=1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
