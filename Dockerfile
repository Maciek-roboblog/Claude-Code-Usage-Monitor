# 🐳 Claude Code Usage Monitor - Docker Image
# Multi-stage build for optimized production image

# Stage 1: Builder - Install dependencies and build application
FROM python:3.11-slim AS builder

# Metadata labels
LABEL maintainer="GiGiDKR <github.com/GiGiDKR>"
LABEL description="Claude Code Usage Monitor - Real-time token usage monitoring"
LABEL version="1.0.19"
LABEL org.opencontainers.image.source="https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor"
LABEL org.opencontainers.image.title="Claude Code Usage Monitor"
LABEL org.opencontainers.image.description="A real-time terminal monitoring tool for Claude AI token usage"
LABEL org.opencontainers.image.version="1.0.19"

# Install system dependencies (curl for health checks, git for potential future needs)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

# Set work directory for building
WORKDIR /build

# Copy dependency files first for better caching
COPY pyproject.toml ./
COPY uv.lock ./
COPY README.md ./

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

# Install Python dependencies
RUN uv pip install --system --no-cache-dir .

# Copy source code
COPY usage_analyzer/ ./usage_analyzer/
COPY claude_monitor.py ./

# Stage 2: Runtime - Create minimal production image
FROM python:3.11-slim AS runtime

# Metadata labels (repeated for final image)
LABEL maintainer="GiGiDKR <gigi@example.com>"
LABEL description="Claude Code Usage Monitor - Real-time token usage monitoring"
LABEL version="1.0.19"
LABEL org.opencontainers.image.source="https://github.com/GiGiDKR/Claude-Code-Usage-Monitor"

# Install minimal system dependencies for runtime
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r claude && \
    useradd -r -g claude -u 1001 claude && \
    mkdir -p /data /app && \
    chown -R claude:claude /data /app

# Set work directory
WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy application code
COPY --from=builder --chown=claude:claude /build/usage_analyzer/ ./usage_analyzer/
COPY --from=builder --chown=claude:claude /build/claude_monitor.py ./

# Copy and set permissions for entrypoint script and health check
COPY --chown=claude:claude docker-entrypoint.sh ./
COPY --chown=claude:claude scripts/health-check.sh ./scripts/
RUN chmod +x docker-entrypoint.sh scripts/health-check.sh

# Create data directory for Claude data volume
VOLUME ["/data"]

# Environment variables for Docker configuration
ENV CLAUDE_DATA_PATH="/data" \
    CLAUDE_PLAN="pro" \
    CLAUDE_TIMEZONE="UTC" \
    CLAUDE_THEME="auto" \
    CLAUDE_REFRESH_INTERVAL="3" \
    CLAUDE_DEBUG_MODE="false" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1

# Switch to non-root user
USER claude

# Expose no ports (console application)
# EXPOSE directive intentionally omitted as this is a console app

# Health check to verify application can run properly
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["./scripts/health-check.sh"]

# Default command
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD []
