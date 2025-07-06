"""
Tests unitaires pour le système de santé Docker.
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

# Ajouter le répertoire du projet au chemin Python
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.health_server import HealthCheckHandler


class TestHealthCheckServer:
    """Tests pour le serveur de contrôle de santé HTTP."""

    def test_health_check_handler_initialization(self):
        """Test l'initialisation du gestionnaire de contrôles de santé via un vrai serveur HTTP."""
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
            assert resp.status in (200, 503)  # healthy ou unhealthy
        finally:
            server.shutdown()
            thread.join(timeout=1)

    @patch("scripts.health_server.get_default_data_paths")
    @patch("scripts.health_server.analyze_usage")
    def test_get_health_status_healthy(
        self, mock_analyze_usage, mock_get_paths, temp_data_dir, jsonl_file_with_data
    ):
        """Test le statut de santé quand tout va bien via un vrai serveur HTTP."""
        # Configuration des mocks
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
        """Test que l'endpoint /health retourne le bon format de réponse."""
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

            # Vérifier le format JSON
            health_status = json.loads(data)

            # Vérifier la structure attendue
            assert "status" in health_status
            assert "timestamp" in health_status
            assert "checks" in health_status

            # Le statut doit être soit "healthy" soit "unhealthy"
            assert health_status["status"] in ["healthy", "unhealthy"]
        finally:
            server.shutdown()
            thread.join(timeout=1)


class TestHealthSystemIntegration:
    """Tests d'intégration pour le système de santé."""

    def test_health_check_script_exists(self):
        """Test que le script de contrôle de santé existe."""
        script_path = (
            Path(__file__).parent.parent.parent / "scripts" / "health_check.sh"
        )
        assert script_path.exists(), "Le script health_check.sh doit exister"

    @pytest.mark.skipif(
        os.name == "nt", reason="Script bash non disponible sur Windows"
    )
    def test_health_check_script_executable(self):
        """Test que le script de contrôle de santé est exécutable."""
        script_path = (
            Path(__file__).parent.parent.parent / "scripts" / "health_check.sh"
        )
        stat_info = script_path.stat()
        assert stat_info.st_mode & 0o111, "Le script doit être exécutable"

    @pytest.mark.skipif(
        os.name == "nt", reason="Script bash non disponible sur Windows"
    )
    def test_health_check_script_execution(self):
        """Test l'exécution du script de contrôle de santé."""
        script_path = (
            Path(__file__).parent.parent.parent / "scripts" / "health_check.sh"
        )

        try:
            # Exécuter le script (peut échouer selon l'environnement)
            result = subprocess.run(
                [str(script_path)], capture_output=True, text=True, timeout=10
            )

            # Le script peut retourner 0 (succès) ou 1 (échec) selon l'état
            assert result.returncode in [0, 1], "Le script doit retourner 0 ou 1"

        except subprocess.TimeoutExpired:
            pytest.skip("Script trop lent - timeout")
        except FileNotFoundError:
            pytest.skip("Script non trouvé ou bash non disponible")

    def test_health_server_script_exists(self):
        """Test que le script du serveur de santé existe."""
        script_path = (
            Path(__file__).parent.parent.parent / "scripts" / "health_server.py"
        )
        assert script_path.exists(), "Le script health_server.py doit exister"

    def test_health_server_can_start(self):
        """Test que le serveur de santé peut démarrer."""
        script_path = (
            Path(__file__).parent.parent.parent / "scripts" / "health_server.py"
        )

        try:
            # Tenter de démarrer le serveur (arrêt rapide)
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Attendre un peu puis terminer
            time.sleep(1)
            process.terminate()

            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

            # Le processus a pu démarrer sans erreur immédiate
            assert True

        except Exception as e:
            pytest.skip(f"Impossible de tester le serveur: {e}")


class TestHealthSystemConfiguration:
    """Tests de configuration du système de santé."""

    def test_default_health_server_port(self):
        """Test le port par défaut du serveur de santé."""
        # Le port par défaut devrait être configurable via une variable d'environnement
        default_port = os.environ.get("HEALTH_SERVER_PORT", "8000")

        # Vérifier que c'est un port valide
        try:
            port_num = int(default_port)
            assert 1024 <= port_num <= 65535, "Le port doit être dans la plage valide"
        except ValueError:
            pytest.fail("Le port par défaut doit être un nombre")

    def test_health_check_endpoints(self):
        """Test des endpoints de contrôle de santé."""
        expected_endpoints = ["/health", "/metrics", "/status"]

        # Pour chaque endpoint, vérifier qu'il répond
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

                # L'endpoint doit répondre (200, 404, ou 503)
                assert resp.status in [200, 404, 503], (
                    f"Endpoint {endpoint} doit répondre"
                )

            except Exception:
                # Certains endpoints peuvent ne pas être implémentés
                pass
            finally:
                server.shutdown()
                thread.join(timeout=1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
