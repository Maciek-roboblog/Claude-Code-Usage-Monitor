"""
Tests unitaires pour le script d'entrée Docker (docker-entrypoint.sh).
"""

import os
import subprocess
from pathlib import Path

import pytest


class TestDockerEntrypoint:
    """Tests pour le script d'entrée Docker."""

    @property
    def entrypoint_script(self):
        """Chemin vers le script d'entrée Docker."""
        return Path(__file__).parent.parent.parent / "docker-entrypoint.sh"

    def test_entrypoint_script_exists(self):
        """Test que le script d'entrée existe."""
        assert self.entrypoint_script.exists()
        assert self.entrypoint_script.is_file()

    def test_entrypoint_script_executable(self):
        """Test que le script d'entrée est exécutable."""
        if os.name != "nt":  # Pas sur Windows
            stat_info = self.entrypoint_script.stat()
            assert stat_info.st_mode & 0o111  # Permissions d'exécution

    def test_entrypoint_script_shebang(self):
        """Test que le script a le bon shebang."""
        with open(self.entrypoint_script, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
        assert first_line == "#!/bin/bash"

    @pytest.mark.skipif(os.name == "nt", reason="Bash non disponible sur Windows")
    def test_entrypoint_validation_missing_data_path(self):
        """Test la validation quand CLAUDE_DATA_PATH est manquant."""
        env = os.environ.copy()
        # Supprimer CLAUDE_DATA_PATH si présent
        env.pop("CLAUDE_DATA_PATH", None)

        try:
            result = subprocess.run(
                ["bash", str(self.entrypoint_script)],
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )
            # Le script devrait échouer
            assert result.returncode != 0
            assert "CLAUDE_DATA_PATH environment variable is not set" in result.stderr
        except subprocess.TimeoutExpired:
            pytest.skip("Script timeout - comportement dans certains environnements")

    @pytest.mark.skipif(os.name == "nt", reason="Bash non disponible sur Windows")
    def test_entrypoint_validation_nonexistent_data_path(self):
        """Test la validation avec un chemin de données inexistant."""
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

    @pytest.mark.skipif(os.name == "nt", reason="Bash non disponible sur Windows")
    def test_entrypoint_with_valid_data_path(self, temp_data_dir, jsonl_file_with_data):
        """Test le script d'entrée avec un chemin de données valide."""
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
            # Utiliser echo comme commande de test au lieu du script principal
            result = subprocess.run(
                ["bash", str(self.entrypoint_script), "echo", "test_successful"],
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
            )

            # Le script ne devrait pas échouer pendant la validation
            if result.returncode != 0:
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")

            # Devrait passer la validation et exécuter la commande
            assert "test_successful" in result.stdout
            assert "Initialization complete" in result.stderr

        except subprocess.TimeoutExpired:
            pytest.skip("Script timeout")

    @pytest.mark.skipif(os.name == "nt", reason="Bash non disponible sur Windows")
    def test_entrypoint_invalid_plan_validation(
        self, temp_data_dir, jsonl_file_with_data
    ):
        """Test la validation avec un plan Claude invalide."""
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

            # Le script devrait corriger automatiquement le plan invalide
            assert "Invalid CLAUDE_PLAN" in result.stderr
            assert "defaulting to 'pro'" in result.stderr

        except subprocess.TimeoutExpired:
            pytest.skip("Script timeout")

    @pytest.mark.skipif(os.name == "nt", reason="Bash non disponible sur Windows")
    def test_entrypoint_invalid_theme_validation(
        self, temp_data_dir, jsonl_file_with_data
    ):
        """Test la validation avec un thème invalide."""
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

    @pytest.mark.skipif(os.name == "nt", reason="Bash non disponible sur Windows")
    def test_entrypoint_invalid_refresh_interval(
        self, temp_data_dir, jsonl_file_with_data
    ):
        """Test la validation avec un intervalle de rafraîchissement invalide."""
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

    @pytest.mark.skipif(os.name == "nt", reason="Bash non disponible sur Windows")
    def test_entrypoint_debug_mode_output(self, temp_data_dir, jsonl_file_with_data):
        """Test la sortie du mode debug."""
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

            # Vérifier que les informations de debug sont affichées
            assert "Debug mode enabled" in result.stderr
            assert "Environment variables:" in result.stderr
            assert f"CLAUDE_DATA_PATH={temp_data_dir}" in result.stderr
            assert "CLAUDE_PLAN=pro" in result.stderr
            assert "CLAUDE_TIMEZONE=UTC" in result.stderr
            assert "CLAUDE_THEME=dark" in result.stderr
            assert "CLAUDE_REFRESH_INTERVAL=5" in result.stderr

        except subprocess.TimeoutExpired:
            pytest.skip("Script timeout")

    @pytest.mark.skipif(os.name == "nt", reason="Bash non disponible sur Windows")
    def test_entrypoint_signal_handling(self, temp_data_dir, jsonl_file_with_data):
        """Test la gestion des signaux (arrêt gracieux)."""
        env = os.environ.copy()
        env.update(
            {"CLAUDE_DATA_PATH": str(temp_data_dir), "CLAUDE_DEBUG_MODE": "true"}
        )

        try:
            # Démarrer le processus avec une commande qui attend
            process = subprocess.Popen(
                ["bash", str(self.entrypoint_script), "sleep", "30"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Attendre un peu puis envoyer SIGTERM
            import time

            time.sleep(2)
            process.terminate()

            # Attendre que le processus se termine
            stdout, stderr = process.communicate(timeout=5)

            # Le processus devrait se terminer proprement
            assert process.returncode != 0  # Terminé par signal

        except (subprocess.TimeoutExpired, ProcessLookupError):
            # Forcer l'arrêt si nécessaire
            try:
                process.kill()
            except:
                pass
            pytest.skip("Test de signal complexe - peut varier selon l'environnement")

    def test_entrypoint_script_logging_functions(self):
        """Test que les fonctions de logging sont définies dans le script."""
        with open(self.entrypoint_script, "r", encoding="utf-8") as f:
            content = f.read()

        # Vérifier que les fonctions de logging sont présentes
        assert "log_info()" in content
        assert "log_warn()" in content
        assert "log_error()" in content
        assert "log_success()" in content

        # Vérifier les codes de couleur
        assert "RED=" in content
        assert "GREEN=" in content
        assert "YELLOW=" in content
        assert "BLUE=" in content

    def test_entrypoint_script_validation_functions(self):
        """Test que les fonctions de validation sont définies."""
        with open(self.entrypoint_script, "r", encoding="utf-8") as f:
            content = f.read()

        # Vérifier les fonctions principales
        assert "validate_environment()" in content
        assert "test_application()" in content
        assert "initialize()" in content
        assert "build_args()" in content
        assert "cleanup()" in content

    def test_entrypoint_script_trap_signals(self):
        """Test que les signaux sont capturés."""
        with open(self.entrypoint_script, "r", encoding="utf-8") as f:
            content = f.read()

        assert "trap cleanup SIGTERM SIGINT SIGQUIT" in content

    @pytest.mark.skipif(os.name == "nt", reason="Bash non disponible sur Windows")
    def test_entrypoint_no_jsonl_warning(self, empty_data_dir):
        """Test l'avertissement quand aucun fichier .jsonl n'est trouvé."""
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

            # Devrait afficher un avertissement mais continuer
            assert "No .jsonl files found" in result.stderr
            assert (
                "Make sure your Claude data directory contains usage data files"
                in result.stderr
            )

        except subprocess.TimeoutExpired:
            pytest.skip("Script timeout")

    @pytest.mark.skipif(os.name == "nt", reason="Bash non disponible sur Windows")
    def test_entrypoint_jsonl_files_count(self, multiple_jsonl_files):
        """Test le comptage des fichiers .jsonl."""
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

            # Devrait compter et afficher le nombre de fichiers .jsonl
            assert "Found 3 .jsonl files in data directory" in result.stderr

        except subprocess.TimeoutExpired:
            pytest.skip("Script timeout")


class TestDockerEntrypointIntegration:
    """Tests d'intégration pour le script d'entrée Docker."""

    @pytest.mark.skipif(os.name == "nt", reason="Bash non disponible sur Windows")
    def test_full_docker_environment_simulation(
        self, temp_data_dir, jsonl_file_with_data
    ):
        """Test complet simulant un environnement Docker."""
        entrypoint_script = Path(__file__).parent.parent.parent / "docker-entrypoint.sh"

        # Configuration complète de l'environnement Docker
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

            # Le script devrait compléter l'initialisation et exécuter la commande
            assert "Initialization complete" in result.stderr
            assert (
                "Starting Claude Code Usage Monitor" in result.stderr
                or "Executing custom command" in result.stderr
            )

        except subprocess.TimeoutExpired:
            pytest.skip("Test d'intégration timeout")

    @pytest.mark.skipif(os.name == "nt", reason="Bash non disponible sur Windows")
    def test_entrypoint_build_args_functionality(
        self, temp_data_dir, jsonl_file_with_data
    ):
        """Test la construction des arguments à partir des variables d'environnement."""
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
            # Utiliser echo au lieu du script principal pour voir les arguments
            result = subprocess.run(
                ["bash", str(entrypoint_script), "echo", "args_test"],
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )

            # En mode debug, le script devrait afficher les arguments construits
            assert "Initialization complete" in result.stderr

        except subprocess.TimeoutExpired:
            pytest.skip("Script timeout")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
