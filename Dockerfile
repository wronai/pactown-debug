# Pactown Live Debug - Dockerfile
# Real-time Bash script analyzer with ShellCheck integration

FROM python:3.12-slim

LABEL maintainer="Softreck <info@softreck.dev>"
LABEL description="Pactown Live Debug - Real-time Bash script analyzer"
LABEL version="1.0.0"

# Install ShellCheck and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    shellcheck \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy application files
COPY app /app/
COPY server.py /app/server.py

# Set environment variables
ENV PORT=8080
ENV APP_DIR=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Run the server
CMD ["python3", "/app/server.py"]
