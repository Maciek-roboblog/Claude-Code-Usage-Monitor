"""
Tests unitaires pour le Dockerfile.
"""

import re
from pathlib import Path

import pytest


class TestDockerfile:
    """Tests pour le Dockerfile."""

    @property
    def dockerfile_path(self):
        """Chemin vers le Dockerfile."""
        return Path(__file__).parent.parent.parent / "Dockerfile"

    def test_dockerfile_exists(self):
        """Test que le Dockerfile existe."""
        assert self.dockerfile_path.exists()
        assert self.dockerfile_path.is_file()

    def test_dockerfile_multi_stage_build(self):
        """Test que le Dockerfile utilise un build multi-étapes."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Vérifier les étapes de build
        assert "FROM python:3.11-slim AS builder" in content
        assert "FROM python:3.11-slim AS runtime" in content

    def test_dockerfile_labels(self):
        """Test les métadonnées LABEL du Dockerfile."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Vérifier les labels requis
        required_labels = [
            'LABEL maintainer="GiGiDKR',
            'LABEL description="Claude Code Usage Monitor',
            'LABEL version="1.0.19"',
            "LABEL org.opencontainers.image.source=",
            "LABEL org.opencontainers.image.title=",
            "LABEL org.opencontainers.image.description=",
            "LABEL org.opencontainers.image.version=",
        ]

        for label in required_labels:
            assert label in content, f"Label manquant: {label}"

    def test_dockerfile_base_images(self):
        """Test les images de base utilisées."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Rechercher toutes les lignes FROM
        from_lines = re.findall(r"^FROM\s+(.+)$", content, re.MULTILINE)

        # Devrait avoir exactement 2 lignes FROM (multi-stage)
        assert len(from_lines) == 2

        # Les deux devraient utiliser python:3.11-slim
        for from_line in from_lines:
            if "AS" in from_line:
                base_image = from_line.split(" AS ")[0].strip()
            else:
                base_image = from_line.strip()
            assert base_image == "python:3.11-slim"

    def test_dockerfile_workdir(self):
        """Test les répertoires de travail."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Vérifier les WORKDIR
        assert "WORKDIR /build" in content  # Stage builder
        assert "WORKDIR /app" in content  # Stage runtime

    def test_dockerfile_system_dependencies(self):
        """Test l'installation des dépendances système."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Vérifier l'installation de curl et git dans le builder
        assert "apt-get install -y --no-install-recommends" in content
        assert "curl" in content
        assert "git" in content

        # Vérifier le nettoyage des listes APT
        assert "rm -rf /var/lib/apt/lists/*" in content

    def test_dockerfile_python_dependencies(self):
        """Test l'installation des dépendances Python."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Vérifier l'installation d'uv
        assert "pip install --no-cache-dir uv" in content

        # Vérifier l'installation des dépendances
        assert "uv pip install --system --no-cache-dir ." in content

    def test_dockerfile_file_copy_operations(self):
        """Test les opérations de copie de fichiers."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Vérifier les copies dans le stage builder
        assert "COPY pyproject.toml ./" in content
        assert "COPY uv.lock ./" in content
        assert "COPY README.md ./" in content
        assert "COPY usage_analyzer/ ./usage_analyzer/" in content
        assert "COPY claude_monitor.py ./" in content

        # Vérifier les copies dans le stage runtime
        assert "COPY --from=builder" in content

    def test_dockerfile_user_creation(self):
        """Test la création d'un utilisateur non-root."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Vérifier la création du groupe et de l'utilisateur
        assert "groupadd -r claude" in content
        assert "useradd -r -g claude -u 1001 claude" in content
        assert "mkdir -p /data /app" in content
        assert "chown -R claude:claude /data /app" in content

    def test_dockerfile_environment_variables(self):
        """Test les variables d'environnement par défaut."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Vérifier les variables d'environnement essentielles
        env_vars = [
            'CLAUDE_DATA_PATH="/data"',
            'CLAUDE_PLAN="pro"',
            'CLAUDE_TIMEZONE="UTC"',
            'CLAUDE_THEME="auto"',
            'CLAUDE_REFRESH_INTERVAL="3"',
            'CLAUDE_DEBUG_MODE="false"',
            'PYTHONPATH="/app"',
            "PYTHONUNBUFFERED=1",
        ]

        for env_var in env_vars:
            assert env_var in content, f"Variable d'environnement manquante: {env_var}"

    def test_dockerfile_volume_declaration(self):
        """Test la déclaration du volume."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert 'VOLUME ["/data"]' in content

    def test_dockerfile_user_switch(self):
        """Test le passage à l'utilisateur non-root."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "USER claude" in content

    def test_dockerfile_healthcheck(self):
        """Test la configuration du contrôle de santé."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Vérifier la présence du HEALTHCHECK
        assert "HEALTHCHECK" in content
        assert "--interval=30s" in content
        assert "--timeout=10s" in content
        assert "--start-period=40s" in content
        assert "--retries=3" in content
        assert "./scripts/health-check.sh" in content

    def test_dockerfile_entrypoint_and_cmd(self):
        """Test l'ENTRYPOINT et CMD."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert 'ENTRYPOINT ["./docker-entrypoint.sh"]' in content
        assert "CMD []" in content

    def test_dockerfile_script_permissions(self):
        """Test que les scripts ont les bonnes permissions."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Vérifier que les scripts sont rendus exécutables
        assert "chmod +x docker-entrypoint.sh scripts/health-check.sh" in content

    def test_dockerfile_no_exposed_ports(self):
        """Test qu'aucun port n'est exposé (application console)."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Vérifier qu'il n'y a pas de directive EXPOSE
        # Le commentaire devrait indiquer pourquoi
        assert (
            "# EXPOSE directive intentionally omitted as this is a console app"
            in content
        )

        # S'assurer qu'il n'y a pas de EXPOSE non commenté
        lines = content.split("\n")
        for line in lines:
            if line.strip().startswith("EXPOSE") and not line.strip().startswith("#"):
                pytest.fail(
                    f"Port exposé trouvé alors qu'aucun ne devrait l'être: {line}"
                )

    def test_dockerfile_optimization_practices(self):
        """Test les bonnes pratiques d'optimisation Docker."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Vérifier l'utilisation de --no-cache-dir
        assert "--no-cache-dir" in content

        # Vérifier l'utilisation de --no-install-recommends
        assert "--no-install-recommends" in content

        # Vérifier le nettoyage des caches apt
        assert "rm -rf /var/lib/apt/lists/*" in content

    def test_dockerfile_layer_efficiency(self):
        """Test l'efficacité des couches Docker."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Vérifier que les installations APT sont combinées avec &&
        apt_install_pattern = r"apt-get install.*&&.*rm -rf /var/lib/apt/lists/\*"
        assert re.search(apt_install_pattern, content, re.DOTALL)

    def test_dockerfile_build_context_optimization(self):
        """Test l'optimisation du contexte de build."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Vérifier que les fichiers de dépendances sont copiés en premier
        lines = content.split("\n")

        copy_lines = [
            i
            for i, line in enumerate(lines)
            if line.strip().startswith("COPY") and "pyproject.toml" in line
        ]
        source_copy_lines = [
            i
            for i, line in enumerate(lines)
            if line.strip().startswith("COPY") and "usage_analyzer/" in line
        ]

        # pyproject.toml devrait être copié avant le code source pour optimiser le cache
        if copy_lines and source_copy_lines:
            assert copy_lines[0] < source_copy_lines[0]

    def test_dockerfile_security_practices(self):
        """Test les bonnes pratiques de sécurité."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Vérifier l'utilisation d'un utilisateur non-root
        assert "USER claude" in content

        # Vérifier que l'utilisateur a un UID spécifique
        assert "-u 1001" in content

        # Vérifier que les répertoires ont les bonnes permissions
        assert "chown -R claude:claude" in content

    def test_dockerfile_metadata_completeness(self):
        """Test la complétude des métadonnées."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extraire toutes les lignes LABEL
        label_lines = re.findall(r"^LABEL\s+(.+)$", content, re.MULTILINE)

        # Vérifier qu'il y a suffisamment de métadonnées
        assert len(label_lines) >= 5

        # Vérifier que les labels contiennent des valeurs
        for label_line in label_lines:
            assert "=" in label_line or '"' in label_line

    def test_dockerfile_stage_naming(self):
        """Test que les étapes ont des noms significatifs."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Vérifier les noms des étapes
        assert "AS builder" in content
        assert "AS runtime" in content

    def test_dockerfile_consistent_base_images(self):
        """Test la cohérence des images de base."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Rechercher toutes les versions de Python mentionnées
        python_versions = re.findall(r"python:([0-9.]+)", content)

        # Toutes les versions devraient être identiques
        if python_versions:
            base_version = python_versions[0]
            for version in python_versions:
                assert version == base_version, (
                    f"Versions Python incohérentes: {version} vs {base_version}"
                )


class TestDockerfileBuildInstructions:
    """Tests pour les instructions spécifiques du Dockerfile."""

    @property
    def dockerfile_path(self):
        """Chemin vers le Dockerfile."""
        return Path(__file__).parent.parent.parent / "Dockerfile"

    def test_dockerfile_copy_instructions_order(self):
        """Test l'ordre des instructions COPY pour optimiser le cache."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Trouver les instructions COPY dans le stage builder
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

        # Vérifier l'ordre optimal: dependencies d'abord, puis source
        dependency_files = ["pyproject.toml", "uv.lock", "README.md"]
        source_files = ["usage_analyzer/", "claude_monitor.py"]

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

        # Les fichiers de dépendances devraient être copiés avant les sources
        if dependency_indices and source_indices:
            assert max(dependency_indices) < min(source_indices)

    def test_dockerfile_run_instruction_optimization(self):
        """Test l'optimisation des instructions RUN."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Vérifier que les commandes apt sont combinées
        apt_commands = re.findall(
            r"RUN apt-get.*?(?=RUN|\n\n|FROM|$)", content, re.DOTALL
        )

        for apt_command in apt_commands:
            # Chaque commande apt devrait inclure update, install et cleanup
            if "apt-get" in apt_command:
                assert "apt-get update" in apt_command
                assert "apt-get install" in apt_command
                assert "rm -rf /var/lib/apt/lists/*" in apt_command

    def test_dockerfile_env_instruction_format(self):
        """Test le format de l'instruction ENV."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Trouver l'instruction ENV
        env_match = re.search(r"ENV\s+(.*?)(?=\n\n|\n[A-Z]|$)", content, re.DOTALL)
        assert env_match, "Instruction ENV non trouvée"

        env_content = env_match.group(1)

        # Vérifier que toutes les variables sont définies
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
            assert var in env_content, f"Variable d'environnement {var} manquante"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
