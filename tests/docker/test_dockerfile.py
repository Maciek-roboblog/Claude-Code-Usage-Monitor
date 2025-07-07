"""
Unit tests for the Dockerfile.
"""

import re
from pathlib import Path

import pytest


class TestDockerfile:
    """Tests for the Dockerfile."""

    @property
    def dockerfile_path(self):
        """Path to the Dockerfile."""
        return Path(__file__).parent.parent.parent / "Dockerfile"

    def test_dockerfile_exists(self):
        """Test that the Dockerfile exists."""
        assert self.dockerfile_path.exists()
        assert self.dockerfile_path.is_file()

    def test_dockerfile_multi_stage_build(self):
        """Test that the Dockerfile uses multi-stage build."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check build stages
        assert "FROM python:3.11-slim AS builder" in content
        assert "FROM python:3.11-slim AS runtime" in content

    def test_dockerfile_labels(self):
        """Test Dockerfile LABEL metadata."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check required labels
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
            assert label in content, f"Missing label: {label}"

    def test_dockerfile_base_images(self):
        """Test the base images used."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find all FROM lines
        from_lines = re.findall(r"^FROM\s+(.+)$", content, re.MULTILINE)

        # Should have exactly 2 FROM lines (multi-stage)
        assert len(from_lines) == 2

        # Both should use python:3.11-slim
        for from_line in from_lines:
            if "AS" in from_line:
                base_image = from_line.split(" AS ")[0].strip()
            else:
                base_image = from_line.strip()
            assert base_image == "python:3.11-slim"

    def test_dockerfile_workdir(self):
        """Test working directories."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check WORKDIRs
        assert "WORKDIR /build" in content  # Builder stage
        assert "WORKDIR /app" in content  # Runtime stage

    def test_dockerfile_system_dependencies(self):
        """Test installation of system dependencies."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check installation of curl and git in builder
        assert "apt-get install -y --no-install-recommends" in content
        assert "curl" in content
        assert "git" in content

        # Check APT list cleanup
        assert "rm -rf /var/lib/apt/lists/*" in content

    def test_dockerfile_python_dependencies(self):
        """Test installation of Python dependencies."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check uv installation
        assert "pip install --no-cache-dir uv" in content

        # Check dependencies installation
        assert "uv pip install --system --no-cache-dir ." in content

    def test_dockerfile_file_copy_operations(self):
        """Test file copy operations."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check copies in builder stage
        assert "COPY pyproject.toml ./" in content
        assert "COPY uv.lock ./" in content
        assert "COPY README.md ./" in content
        assert "COPY usage_analyzer/ ./usage_analyzer/" in content
        assert "COPY claude_monitor.py ./" in content

        # Check copies in runtime stage
        assert "COPY --from=builder" in content

    def test_dockerfile_user_creation(self):
        """Test creation of non-root user."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check group and user creation
        assert "groupadd -r claude" in content
        assert "useradd -r -g claude -u 1001 claude" in content
        assert "mkdir -p /data /app" in content
        assert "chown -R claude:claude /data /app" in content

    def test_dockerfile_environment_variables(self):
        """Test default environment variables."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check essential environment variables
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
            assert env_var in content, f"Missing environment variable: {env_var}"

    def test_dockerfile_volume_declaration(self):
        """Test volume declaration."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert 'VOLUME ["/data"]' in content

    def test_dockerfile_user_switch(self):
        """Test switching to non-root user."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "USER claude" in content

    def test_dockerfile_healthcheck(self):
        """Test healthcheck configuration."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check HEALTHCHECK presence
        assert "HEALTHCHECK" in content
        assert "--interval=30s" in content
        assert "--timeout=10s" in content
        assert "--start-period=40s" in content
        assert "--retries=3" in content
        assert "./scripts/health-check.sh" in content

    def test_dockerfile_entrypoint_and_cmd(self):
        """Test ENTRYPOINT and CMD."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert 'ENTRYPOINT ["./docker-entrypoint.sh"]' in content
        assert "CMD []" in content

    def test_dockerfile_script_permissions(self):
        """Test that scripts have correct permissions."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check that scripts are made executable
        assert "chmod +x docker-entrypoint.sh scripts/health-check.sh" in content

    def test_dockerfile_no_exposed_ports(self):
        """Test that no port is exposed (console app)."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check that there is no EXPOSE directive
        # The comment should indicate why
        assert (
            "# EXPOSE directive intentionally omitted as this is a console app"
            in content
        )

        # Ensure there is no uncommented EXPOSE
        lines = content.split("\n")
        for line in lines:
            if line.strip().startswith("EXPOSE") and not line.strip().startswith("#"):
                pytest.fail(
                    f"Exposed port found when none should be: {line}"
                )

    def test_dockerfile_optimization_practices(self):
        """Test Docker optimization best practices."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check use of --no-cache-dir
        assert "--no-cache-dir" in content

        # Check use of --no-install-recommends
        assert "--no-install-recommends" in content

        # Check apt cache cleanup
        assert "rm -rf /var/lib/apt/lists/*" in content

    def test_dockerfile_layer_efficiency(self):
        """Test Docker layer efficiency."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check that APT installs are combined with &&
        apt_install_pattern = r"apt-get install.*&&.*rm -rf /var/lib/apt/lists/\*"
        assert re.search(apt_install_pattern, content, re.DOTALL)

    def test_dockerfile_build_context_optimization(self):
        """Test build context optimization."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check that dependency files are copied first
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

        # pyproject.toml should be copied before source code to optimize cache
        if copy_lines and source_copy_lines:
            assert copy_lines[0] < source_copy_lines[0]

    def test_dockerfile_security_practices(self):
        """Test Docker security best practices."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check use of non-root user
        assert "USER claude" in content

        # Check that user has a specific UID
        assert "-u 1001" in content

        # Check that directories have correct permissions
        assert "chown -R claude:claude" in content

    def test_dockerfile_metadata_completeness(self):
        """Test metadata completeness."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract all LABEL lines
        label_lines = re.findall(r"^LABEL\s+(.+)$", content, re.MULTILINE)

        # Check that there are enough metadata labels
        assert len(label_lines) >= 5

        # Check that labels contain values
        for label_line in label_lines:
            assert "=" in label_line or '"' in label_line

    def test_dockerfile_stage_naming(self):
        """Test that stages have meaningful names."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check stage names
        assert "AS builder" in content
        assert "AS runtime" in content

    def test_dockerfile_consistent_base_images(self):
        """Test consistency of base images."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find all mentioned Python versions
        python_versions = re.findall(r"python:([0-9.]+)", content)

        # All versions should be identical
        if python_versions:
            base_version = python_versions[0]
            for version in python_versions:
                assert version == base_version, (
                    f"Inconsistent Python versions: {version} vs {base_version}"
                )


class TestDockerfileBuildInstructions:
    """Tests for specific Dockerfile instructions."""

    @property
    def dockerfile_path(self):
        """Path to the Dockerfile."""
        return Path(__file__).parent.parent.parent / "Dockerfile"

    def test_dockerfile_copy_instructions_order(self):
        """Test order of COPY instructions for cache optimization."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Find COPY instructions in builder stage
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

        # Check optimal order: dependencies first, then source
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

        # Dependency files should be copied before sources
        if dependency_indices and source_indices:
            assert max(dependency_indices) < min(source_indices)

    def test_dockerfile_run_instruction_optimization(self):
        """Test optimization of RUN instructions."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check that apt commands are combined
        apt_commands = re.findall(
            r"RUN apt-get.*?(?=RUN|\n\n|FROM|$)", content, re.DOTALL
        )

        for apt_command in apt_commands:
            # Each apt command should include update, install, and cleanup
            if "apt-get" in apt_command:
                assert "apt-get update" in apt_command
                assert "apt-get install" in apt_command
                assert "rm -rf /var/lib/apt/lists/*" in apt_command

    def test_dockerfile_env_instruction_format(self):
        """Test ENV instruction format."""
        with open(self.dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find ENV instruction
        env_match = re.search(r"ENV\s+(.*?)(?=\n\n|\n[A-Z]|$)", content, re.DOTALL)
        assert env_match, "ENV instruction not found"

        env_content = env_match.group(1)

        # Check that all variables are defined
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
