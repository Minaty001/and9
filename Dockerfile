# ---- Build stage ----
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Runtime stage ----
FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r jarvis && useradd -r -g jarvis -d /app -s /bin/false jarvis

# Copy Python packages from builder (system-wide, accessible by all users)
COPY --from=builder /usr/local /usr/local

# Copy app code (no render.yaml or tests needed at runtime)
# Note: also add a .dockerignore to exclude unnecessary files from build context
COPY app/ app/
COPY requirements.txt .

# Create data directory
RUN mkdir -p /app/.jarvis_data && chown -R jarvis:jarvis /app

USER jarvis

EXPOSE 8000

ENV FLASK_ENV=production
ENV RENDER=true

CMD gunicorn app.main:app --workers 2 --threads 4 --timeout 120 --bind "0.0.0.0:${PORT:-8000}"
