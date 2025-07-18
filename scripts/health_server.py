#!/usr/bin/env python3
"""
Simple HTTP health check endpoint for Claude        except Exception as e:
            # Always return JSON and 503 code on error, with 'checks' key
            self.send_response(503)de Usage Monitor.
Provides a lightweight web endpoint for container orchestration health checks.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from claude_monitor.cli.main import discover_claude_data_paths
    from claude_monitor.data.analysis import analyze_usage
except ImportError as e:
    print(f"Error importing modules: {e}", file=sys.stderr)
    sys.exit(1)


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP handler for health check endpoints."""

    def log_message(self, format, *args):
        """Override to reduce noise in logs."""
        if os.getenv("HEALTH_CHECK_VERBOSE", "false").lower() == "true":
            super().log_message(format, *args)

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/health":
            self.handle_health_check()
        elif self.path == "/health/live":
            self.handle_liveness_check()
        elif self.path == "/health/ready":
            self.handle_readiness_check()
        elif self.path == "/metrics":
            self.handle_metrics()
        else:
            self.send_error(404, "Not Found")

    def handle_health_check(self):
        """Handle comprehensive health check."""
        try:
            health_status = HealthCheckHandlerExtension.get_health_status()
            # Mock mode: if variable is enabled, force status to healthy
            allow_empty_data = (
                os.getenv("HEALTH_CHECK_ALLOW_EMPTY_DATA", "false").lower() == "true"
            )
            if (
                allow_empty_data
                and health_status["checks"]["data_access"]["status"] == "unhealthy"
            ):
                health_status["status"] = "healthy"
                health_status["checks"]["data_access"]["status"] = "mocked"
                health_status["checks"]["data_access"]["mock_mode"] = True
                health_status["mock_mode"] = True
            status_code = 200 if health_status["status"] == "healthy" else 503

            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            response = json.dumps(health_status, indent=2)
            self.wfile.write(response.encode())
        except Exception as e:
            # On retourne toujours un JSON et un code 503 en cas d’erreur, avec la clé 'checks'
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            error_response = json.dumps(
                {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "checks": {
                        "data_access": {"status": "unhealthy", "error": str(e)},
                        "analysis": {"status": "unhealthy", "error": str(e)},
                    },
                },
                indent=2,
            )
            self.wfile.write(error_response.encode())

    def handle_liveness_check(self):
        """Handle simple liveness check (is the service running?)."""
        try:
            # Simple check - can we import and basic functionality works?

            response = {
                "status": "alive",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": "claude-usage-monitor",
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        except Exception as e:
            self.send_error(500, f"Liveness check failed: {e}")

    def handle_readiness_check(self):
        """Handle readiness check (is the service ready to serve?)."""
        try:
            # Check if we can access data and perform analysis
            data_paths = discover_claude_data_paths()
            has_data = False

            for path in data_paths:
                if Path(path).exists():
                    jsonl_files = list(Path(path).glob("*.jsonl"))
                    if jsonl_files:
                        has_data = True
                        break

            if not has_data:
                self.send_response(503)
                response = {
                    "status": "not_ready",
                    "reason": "No data available",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            else:
                # Try to perform a quick analysis
                result = HealthCheckHandlerExtension.get_cached_analysis()
                self.send_response(200)
                response = {
                    "status": "ready",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "data_available": True,
                    "blocks_found": len(result.get("blocks", [])),
                }

            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        except Exception as e:
            self.send_error(500, f"Readiness check failed: {e}")

    def handle_metrics(self):
        """Handle basic metrics endpoint."""
        try:
            metrics = HealthCheckHandlerExtension.get_basic_metrics()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(metrics, indent=2).encode())
        except Exception as e:
            self.send_error(500, f"Metrics collection failed: {e}")


def get_default_data_paths():
    """Wrapper pour patcher les chemins de données par défaut dans les tests."""
    return discover_claude_data_paths()


# Remove duplicate class declaration - methods will be added to the existing class above


class HealthCheckHandlerExtension:
    @staticmethod
    def get_health_status() -> Dict[str, Any]:
        """Get comprehensive health status."""
        checks: Dict[str, Any] = {}
        overall_status = "healthy"

        # Check data access
        try:
            data_paths = get_default_data_paths()
            data_accessible = False
            jsonl_count = 0

            # Convert Path objects to strings to avoid JSON serialization
            data_paths_str = [str(path) for path in data_paths]

            for path in data_paths:
                try:
                    if Path(path).exists() and Path(path).is_dir():
                        jsonl_files = list(Path(path).glob("*.jsonl"))
                        if jsonl_files:
                            data_accessible = True
                            jsonl_count += len(jsonl_files)
                except Exception as inner_e:
                    # Ignore errors on each path, but log them
                    error_list = checks.setdefault("data_access_errors", [])
                    error_list.append(str(inner_e))

            checks["data_access"] = {
                "status": "healthy" if data_accessible else "unhealthy",
                "paths_checked": data_paths_str,
                "jsonl_files_found": jsonl_count,
            }

            if not data_accessible:
                overall_status = "unhealthy"
        except Exception as e:
            checks["data_access"] = {"status": "unhealthy", "error": str(e)}
            overall_status = "unhealthy"

        # Check analysis functionality
        try:
            start_time = time.time()
            try:
                result = analyze_usage()
                analysis_time = time.time() - start_time
                checks["analysis"] = {
                    "status": "healthy",
                    "response_time_seconds": round(analysis_time, 3),
                    "blocks_analyzed": len(result.get("blocks", [])),
                }
            except Exception as analysis_e:
                analysis_error = {"status": "unhealthy", "error": str(analysis_e)}
                checks["analysis"] = analysis_error
                overall_status = "unhealthy"
        except Exception as e:
            checks["analysis"] = {"status": "unhealthy", "error": str(e)}
            overall_status = "unhealthy"

        # Check environment
        env_vars = [
            "CLAUDE_DATA_PATH",
            "CLAUDE_PLAN",
            "CLAUDE_TIMEZONE",
            "CLAUDE_THEME",
        ]

        env_status = {}
        for var in env_vars:
            value = os.getenv(var)
            env_status[var] = value if value else "not_set"

        checks["environment"] = {"status": "healthy", "variables": env_status}

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": "claude-usage-monitor",
            "version": "1.0.19",
            "checks": checks,
        }

    @staticmethod
    def get_basic_metrics() -> Dict[str, Any]:
        """Get basic metrics for monitoring."""
        try:
            # Get data statistics
            data_paths = get_default_data_paths()
            total_files = 0
            total_size_bytes = 0

            for path in data_paths:
                if Path(path).exists():
                    for file in Path(path).glob("*.jsonl"):
                        if file.is_file():
                            total_files += 1
                            total_size_bytes += file.stat().st_size

            # Get analysis metrics
            start_time = time.time()
            result = analyze_usage()
            analysis_time = time.time() - start_time

            return {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "data_files": {
                    "total_jsonl_files": total_files,
                    "total_size_bytes": total_size_bytes,
                    "total_size_mb": round(total_size_bytes / (1024 * 1024), 2),
                },
                "analysis": {
                    "blocks_processed": len(result.get("blocks", [])),
                    "last_analysis_time_seconds": round(analysis_time, 3),
                },
                "environment": {
                    "data_path": os.getenv("CLAUDE_DATA_PATH", "/data"),
                    "plan": os.getenv("CLAUDE_PLAN", "pro"),
                    "timezone": os.getenv("CLAUDE_TIMEZONE", "Europe/Warsaw"),
                    "theme": os.getenv("CLAUDE_THEME", "auto"),
                },
            }
        except Exception as e:
            return {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error": str(e),
                "status": "metrics_collection_failed",
            }

    @staticmethod
    def cached_analyze_usage(cache_key):
        return analyze_usage()

    @staticmethod
    def get_cached_analysis():
        # Cache for 60 secondes
        cache_key = int(time.time() // 60)
        return HealthCheckHandlerExtension.cached_analyze_usage(cache_key)


def run_health_server(port: int = 8080, host: str = "127.0.0.1"):
    """Run the health check HTTP server."""
    server = HTTPServer((host, port), HealthCheckHandler)

    print(f"🏥 Health check server starting on {host}:{port}")
    print("📊 Endpoints available:")
    print("  GET /health       - Comprehensive health check")
    print("  GET /health/live  - Liveness probe (simple)")
    print("  GET /health/ready - Readiness probe (with data check)")
    print("  GET /metrics      - Basic metrics")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Health check server stopping...")
        server.shutdown()
        server.server_close()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="HTTP health check server for Claude Code Usage Monitor"
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=int(os.getenv("HEALTH_CHECK_PORT", "8080")),
        help="Port to listen on (default: 8080)",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("HEALTH_CHECK_HOST", "127.0.0.1"),
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--test", action="store_true", help="Run a single health check and exit"
    )

    args = parser.parse_args()

    if args.test:
        # Run a single health check
        try:
            health_status = HealthCheckHandlerExtension.get_health_status()
            print(json.dumps(health_status, indent=2))
            sys.exit(0 if health_status["status"] == "healthy" else 1)
        except Exception as e:
            print(f"Health check failed: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Run the server
        run_health_server(args.port, args.host)


if __name__ == "__main__":
    main()
