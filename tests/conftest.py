"""
Configuration et fixtures pour les tests Docker.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import Mock

import pytest


@pytest.fixture
def temp_data_dir():
    """Crée un répertoire temporaire pour les tests de données."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_jsonl_data():
    """Données JSONL d'exemple pour les tests."""
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
        {
            "timestamp": "2024-01-15T11:30:00Z",
            "model": "claude-3-opus-20240229",
            "usage": {"input_tokens": 2000, "output_tokens": 1200},
        },
    ]


@pytest.fixture
def jsonl_file_with_data(temp_data_dir, sample_jsonl_data):
    """Crée un fichier JSONL avec des données d'exemple."""
    jsonl_file = temp_data_dir / "test_usage.jsonl"

    with open(jsonl_file, "w") as f:
        for entry in sample_jsonl_data:
            f.write(json.dumps(entry) + "\n")

    return jsonl_file


@pytest.fixture
def empty_data_dir(temp_data_dir):
    """Répertoire de données vide pour tester les cas d'erreur."""
    return temp_data_dir


@pytest.fixture
def invalid_jsonl_file(temp_data_dir):
    """Fichier JSONL avec des données invalides."""
    invalid_file = temp_data_dir / "invalid.jsonl"

    with open(invalid_file, "w") as f:
        f.write('{"invalid": json}\n')  # JSON malformé
        f.write("valid json but wrong structure\n")

    return invalid_file


@pytest.fixture
def multiple_jsonl_files(temp_data_dir, sample_jsonl_data):
    """Plusieurs fichiers JSONL pour tester l'agrégation."""
    files = []

    for i in range(3):
        file_path = temp_data_dir / f"usage_{i}.jsonl"
        with open(file_path, "w") as f:
            # Chaque fichier contient une partie des données
            start_idx = i * len(sample_jsonl_data) // 3
            end_idx = (i + 1) * len(sample_jsonl_data) // 3

            for entry in sample_jsonl_data[start_idx:end_idx]:
                f.write(json.dumps(entry) + "\n")

        files.append(file_path)

    return files


@pytest.fixture
def docker_env_vars():
    """Variables d'environnement Docker par défaut."""
    return {
        "CLAUDE_DATA_PATH": "/data",
        "CLAUDE_PLAN": "pro",
        "CLAUDE_TIMEZONE": "UTC",
        "CLAUDE_THEME": "auto",
        "CLAUDE_REFRESH_INTERVAL": "3",
        "CLAUDE_DEBUG_MODE": "false",
    }


@pytest.fixture
def invalid_env_vars():
    """Variables d'environnement invalides pour tester la validation."""
    return {
        "CLAUDE_PLAN": "invalid_plan",
        "CLAUDE_THEME": "invalid_theme",
        "CLAUDE_REFRESH_INTERVAL": "-1",
        "CLAUDE_DEBUG_MODE": "maybe",
    }


@pytest.fixture
def mock_analyze_usage():
    """Mock de la fonction analyze_usage."""

    def _mock_result(blocks_count: int = 3) -> Dict[str, Any]:
        return {
            "blocks": [
                {
                    "model": "claude-3-sonnet-20240229",
                    "usage": {"input_tokens": 1500, "output_tokens": 800},
                    "timestamp": "2024-01-15T10:30:00Z",
                }
                for _ in range(blocks_count)
            ],
            "total_usage": {
                "input_tokens": blocks_count * 1500,
                "output_tokens": blocks_count * 800,
            },
        }

    mock = Mock(return_value=_mock_result())
    mock.side_effect = lambda: _mock_result()
    return mock


@pytest.fixture
def large_jsonl_dataset(temp_data_dir):
    """Dataset JSONL volumineux pour tester les performances."""
    large_file = temp_data_dir / "large_usage.jsonl"

    # Génère 10000 entrées
    with open(large_file, "w") as f:
        for i in range(10000):
            entry = {
                "timestamp": f"2024-01-{15 + i % 15:02d}T{10 + i % 14:02d}:30:00Z",
                "model": f"claude-3-{'sonnet' if i % 2 else 'haiku'}-20240229",
                "usage": {
                    "input_tokens": 500 + (i % 1000),
                    "output_tokens": 200 + (i % 500),
                },
            }
            f.write(json.dumps(entry) + "\n")

    return large_file


@pytest.fixture
def corrupted_data_dir(temp_data_dir):
    """Répertoire avec des fichiers corrompus et des permissions limitées."""
    # Fichier avec permissions limitées
    restricted_file = temp_data_dir / "restricted.jsonl"
    with open(restricted_file, "w") as f:
        f.write('{"test": "data"}\n')

    # Rendre le fichier non-lisible (sur Unix)
    if os.name != "nt":  # Pas sur Windows
        os.chmod(restricted_file, 0o000)

    # Fichier binaire avec extension .jsonl
    binary_file = temp_data_dir / "binary.jsonl"
    with open(binary_file, "wb") as f:
        f.write(b"\x00\x01\x02\x03\x04\x05")

    return temp_data_dir


class DockerTestUtils:
    """Utilitaires pour les tests Docker."""

    @staticmethod
    def create_test_volume_mount(
        source_dir: Path, target_path: str = "/data"
    ) -> Dict[str, str]:
        """Crée une configuration de montage de volume pour les tests."""
        return {
            "source": str(source_dir.absolute()),
            "target": target_path,
            "type": "bind",
            "readonly": True,
        }

    @staticmethod
    def validate_env_vars(env_vars: Dict[str, str]) -> List[str]:
        """Valide les variables d'environnement et retourne les erreurs."""
        errors = []

        # Validation CLAUDE_PLAN
        valid_plans = ["pro", "max5", "max20", "custom_max"]
        if "CLAUDE_PLAN" in env_vars and env_vars["CLAUDE_PLAN"] not in valid_plans:
            errors.append(f"Invalid CLAUDE_PLAN: {env_vars['CLAUDE_PLAN']}")

        # Validation CLAUDE_THEME
        valid_themes = ["light", "dark", "auto"]
        if "CLAUDE_THEME" in env_vars and env_vars["CLAUDE_THEME"] not in valid_themes:
            errors.append(f"Invalid CLAUDE_THEME: {env_vars['CLAUDE_THEME']}")

        # Validation CLAUDE_REFRESH_INTERVAL
        if "CLAUDE_REFRESH_INTERVAL" in env_vars:
            try:
                interval = int(env_vars["CLAUDE_REFRESH_INTERVAL"])
                if interval < 1:
                    errors.append("CLAUDE_REFRESH_INTERVAL must be >= 1")
            except ValueError:
                errors.append("CLAUDE_REFRESH_INTERVAL must be a valid integer")

        return errors

    @staticmethod
    def simulate_docker_environment(env_vars: Dict[str, str]) -> Dict[str, str]:
        """Simule l'environnement Docker en définissant les variables d'environnement."""
        original_env = {}

        # Sauvegarde l'environnement original
        for key in env_vars:
            original_env[key] = os.environ.get(key)
            os.environ[key] = env_vars[key]

        return original_env

    @staticmethod
    def restore_environment(original_env: Dict[str, str]):
        """Restaure l'environnement original."""
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@pytest.fixture
def docker_utils():
    """Fixture pour les utilitaires Docker."""
    return DockerTestUtils()
