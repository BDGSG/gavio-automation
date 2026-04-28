FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=utf-8 \
    TZ=Europe/Paris

# System deps : ca-certificates pour HTTPS, tzdata pour timezone
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates tzdata curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps (cache layer)
COPY automation/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy package
COPY automation /app/automation

# Logs + data dirs
RUN mkdir -p /data/gavio_blog /app/logs

EXPOSE 5000

# Healthcheck via /health
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fsS http://localhost:5000/health || exit 1

CMD ["python", "-m", "automation"]
