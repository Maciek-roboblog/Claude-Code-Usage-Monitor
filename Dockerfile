# # Stage 1: Builder - Install dependencies and build application
FROM python:3.11-slim AS builder

# Metadata labels
LABEL maintainer="GiGiDKR <github.com/GiGiDKR>"
LABEL description="Claude Code Usage Monitor - Real-time token usage monitoring"
LABEL version="3.0.4"
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
COPY README.md ./

# Copy source code
COPY src/ ./src/

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

# Install Python dependencies
RUN uv pip install --system --no-cache-dir .

# Stage 2: Runtime - Create minimal production image
FROM python:3.11-slim AS runtime

# Metadata labels (repeated for final image)
LABEL maintainer="GiGiDKR <gigi@example.com>"
LABEL description="Claude Code Usage Monitor - Real-time token usage monitoring"
LABEL version="3.0.4"
LABEL org.opencontainers.image.source="https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor"
LABEL org.opencontainers.image.title="Claude Code Usage Monitor"
LABEL org.opencontainers.image.description="A real-time terminal monitoring tool for Claude AI token usage"
LABEL org.opencontainers.image.version="3.0.4"

# Install minimal system dependencies for runtime
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r claude && \
    useradd -r -g claude -u 1001 claude && \
    mkdir -p /data /app /home/claude && \
    chown -R claude:claude /data /app /home/claude

# Set work directory
WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Application is now installed as a package - no need to copy source code

# Copy and set permissions for entrypoint script and health check
COPY --chown=claude:claude docker-entrypoint.sh ./
COPY --chown=claude:claude scripts/health-check.sh ./scripts/
RUN apt-get update && apt-get install -y --no-install-recommends dos2unix && rm -rf /var/lib/apt/lists/* \
    && dos2unix docker-entrypoint.sh scripts/health-check.sh \
    && chmod +x docker-entrypoint.sh scripts/health-check.sh

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
