# ── Build stage ────────────────────────────────────────────────────
# Uses venv to install packages — never installs as root.
# This eliminates: WARNING: Running pip as root
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .

# Create virtual environment and install inside it
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# ── Runtime stage ───────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Create non-root user for runtime
RUN groupadd -r jarvis && useradd -r -g jarvis -d /app -s /bin/false jarvis

# Copy venv from builder stage (not system-wide Python packages)
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy app code
COPY app/ app/
COPY requirements.txt .

# Create data directory (reminders DB, traces DB, installed_apps.json)
RUN mkdir -p /app/.jarvis_data && chown -R jarvis:jarvis /app

USER jarvis

EXPOSE 8000

ENV FLASK_ENV=production
ENV RENDER=true
ENV AND9_REMINDERS_DB=/app/.jarvis_data/reminders.db
ENV AND9_REMINDERS_STORAGE_DB=/app/.jarvis_data/reminders_engine.db
ENV AND9_TRACES_DB=/app/.jarvis_data/intent_traces.db
ENV AND9_INSTALLED_APPS_PATH=/app/.jarvis_data/installed_apps.json

CMD gunicorn app.main:app --workers 2 --threads 4 --timeout 120 --bind "0.0.0.0:${PORT:-8000}"
