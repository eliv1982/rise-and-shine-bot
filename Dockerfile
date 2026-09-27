# Rise and Shine Daily — Telegram-бот (аффирмации, TTS, картинки)
FROM python:3.11-slim

# ffmpeg для озвучки аффирмаций с паузами
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Dedicated non-root user, fixed UID/GID so a mounted data volume's ownership
# (chown -R 1000:1000 <volume>) stays valid across image rebuilds.
RUN groupadd -g 1000 appuser && useradd -u 1000 -g appuser -M -s /usr/sbin/nologin appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py database.py states.py utils.py bot.py scheduler.py monitoring.py cleanup_outputs.py ./
COPY handlers ./handlers
COPY keyboards ./keyboards
COPY services ./services
COPY scripts/healthcheck.py ./scripts/healthcheck.py

# Логи и данные будут в volume (BOT_DATA_DIR=/app/data). Created and owned by
# appuser here so a *fresh* named volume (Docker copies a mount point's
# pre-existing image content/ownership into it on first use) is writable
# immediately. An *existing* volume populated while the container ran as root
# needs a one-time `chown -R 1000:1000` on the server before this image runs -
# see DEPLOY.md / the Stage 5 report's deployment checklist.
RUN mkdir -p /app/data && chown -R appuser:appuser /app

ENV PYTHONUNBUFFERED=1

USER appuser

# Not an HTTP check (this is a polling bot): verifies scheduler.py's per-tick
# heartbeat file is recent, catching a wedged event loop that a plain
# container-exit-based restart wouldn't. See scripts/healthcheck.py.
HEALTHCHECK --interval=60s --timeout=5s --start-period=45s --retries=3 \
    CMD ["python", "scripts/healthcheck.py"]

CMD ["python", "-u", "bot.py"]
