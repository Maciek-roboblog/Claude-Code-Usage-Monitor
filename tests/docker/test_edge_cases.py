"""
Tests de cas limites et gestion d'erreurs pour l'implémentation Docker.
"""

import json
import socket
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


class TestDockerEdgeCases:
    """Tests pour les cas limites de l'implémentation Docker."""

    def test_empty_data_directory_handling(self, empty_data_dir, docker_utils):
        """Test la gestion d'un répertoire de données vide via un vrai serveur HTTP."""
        from http.client import HTTPConnection

        # Simuler l'environnement Docker avec un répertoire vide
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

                # Trouver un port libre
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("localhost", 0))
                    port = s.getsockname()[1]

                server = HTTPServer(("localhost", port), HealthCheckHandler)

                def run_server():
                    server.serve_forever()

                thread = threading.Thread(target=run_server, daemon=True)
                thread.start()
                time.sleep(0.2)  # Laisser le serveur démarrer

                try:
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
                    server.shutdown()
                    thread.join(timeout=1)

        finally:
            docker_utils.restore_environment(original_env)

    def test_corrupted_jsonl_files_handling(self, temp_data_dir, docker_utils):
        """Test la gestion de fichiers JSONL corrompus via un vrai serveur HTTP."""
        from http.client import HTTPConnection

        # Créer un fichier JSONL corrompu
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
                mock_analyze.side_effect = Exception("Erreur de parsing JSON")

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
        """Test la gestion des erreurs de permissions via un vrai serveur HTTP."""
        from http.client import HTTPConnection

        # Créer un fichier avec des permissions restrictives
        restricted_file = temp_data_dir / "restricted.jsonl"
        with open(restricted_file, "w") as f:
            f.write('{"test": "data"}\n')

        # Simuler une erreur de permission
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
        """Test la gestion de fichiers JSONL très volumineux via un vrai serveur HTTP."""
        from http.client import HTTPConnection

        # Créer un fichier JSONL très volumineux
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
        """Test la gestion de variables d'environnement malformées."""
        malformed_env = {
            "CLAUDE_PLAN": "",  # Vide
            "CLAUDE_THEME": "invalid_theme",
            "CLAUDE_REFRESH_INTERVAL": "not_a_number",
            "CLAUDE_DEBUG_MODE": "maybe",  # Pas un booléen
            "CLAUDE_TIMEZONE": "Invalid/Timezone",
        }

        errors = docker_utils.validate_env_vars(malformed_env)

        # Devrait détecter plusieurs erreurs
        assert len(errors) >= 2, f"Pas assez d'erreurs détectées: {errors}"

    def test_dockerfile_parsing_edge_cases(self):
        """Test les cas limites de parsing du Dockerfile."""
        dockerfile_path = Path(__file__).parent.parent.parent / "Dockerfile"

        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Test parsing avec des lignes vides et commentaires
        lines = content.split("\n")

        # Compter les lignes non vides et non commentaires
        instruction_lines = [
            line.strip()
            for line in lines
            if line.strip() and not line.strip().startswith("#")
        ]

        assert len(instruction_lines) > 10, "Dockerfile trop simple"

        # Vérifier qu'il n'y a pas de syntaxe étrange
        for line in instruction_lines:
            if line.startswith(("FROM", "RUN", "COPY", "ENV")):
                # Les instructions devraient avoir du contenu après le mot-clé
                parts = line.split(" ", 1)
                assert len(parts) >= 2, f"Instruction malformée: {line}"

    def test_docker_compose_parsing_edge_cases(self):
        """Test les cas limites de parsing docker-compose.yml."""

        compose_path = Path(__file__).parent.parent.parent / "docker-compose.yml"

        with open(compose_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Test parsing YAML avec différents encodages
        try:
            compose_config = yaml.safe_load(content)
            assert isinstance(compose_config, dict)

            # Vérifier la structure profonde
            service = compose_config["services"]["claude-monitor"]

            # Test des valeurs par défaut manquantes
            env_vars = service["environment"]
            for key, value in env_vars.items():
                assert value is not None, f"Valeur None pour {key}"
                assert str(value).strip() != "", f"Valeur vide pour {key}"

        except yaml.YAMLError as e:
            pytest.fail(f"Erreur de parsing YAML: {e}")


class TestDockerErrorRecovery:
    """Tests de récupération d'erreurs Docker."""

    def test_container_restart_behavior(self):
        """Test le comportement de redémarrage du conteneur."""

        compose_path = Path(__file__).parent.parent.parent / "docker-compose.yml"

        with open(compose_path, "r", encoding="utf-8") as f:
            compose_config = yaml.safe_load(f)

        service = compose_config["services"]["claude-monitor"]

        # Vérifier la politique de redémarrage
        assert "restart" in service
        restart_policy = service["restart"]

        # Politiques de redémarrage acceptables
        valid_policies = ["unless-stopped", "always", "on-failure"]
        assert restart_policy in valid_policies

    def test_graceful_shutdown_handling(self):
        """Test la gestion de l'arrêt gracieux."""
        entrypoint_path = Path(__file__).parent.parent.parent / "docker-entrypoint.sh"

        with open(entrypoint_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Vérifier la gestion des signaux
        assert "cleanup()" in content
        assert "trap cleanup SIGTERM SIGINT SIGQUIT" in content

        # Vérifier que le cleanup tue les processus en arrière-plan
        assert "jobs -p | xargs" in content


class TestDockerSecurityEdgeCases:
    """Tests de sécurité et cas limites."""

    def test_container_escape_prevention(self):
        """Test la prévention d'évasion de conteneur."""
        dockerfile_path = Path(__file__).parent.parent.parent / "Dockerfile"

        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Vérifier l'absence de configurations dangereuses
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
                f"Configuration dangereuse détectée: {pattern}"
            )

    def test_secrets_exposure_prevention(self):
        """Test la prévention d'exposition de secrets."""
        # Vérifier les fichiers de configuration
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
                    # Permettre les références aux variables d'environnement
                    if pattern in content and not any(
                        env_ref in content
                        for env_ref in ["${", "$", "environment", "env_file"]
                    ):
                        pytest.fail(
                            f"Possible exposition de secret '{pattern}' dans {config_file}"
                        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
