FROM python:3.11-slim

# Install Node.js (required for Claude Code CLI)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash curl wget git build-essential jq nano procps \
    && curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace

# Create non-root user for runtime
RUN useradd -ms /bin/bash agent \
    && usermod -aG root agent \
    && mkdir -p /home/agent \
    && chown -R agent:root /home/agent && chmod -R 775 /home/agent \
    && chown -R agent:root /workspace && chmod -R 775 /workspace

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code@latest

# Switch to non-root user
USER agent

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Copy only dependency files first (for better caching)
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -e ".[api-server]"

# Expose the API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run the API server
CMD ["python", "-m", "claude_agent_sdk.api_server", "--host", "0.0.0.0", "--port", "8000"]
