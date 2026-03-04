# Rise and Shine Daily — Telegram-бот (аффирмации, TTS, картинки)
FROM python:3.11-slim

# ffmpeg для озвучки аффирмаций с паузами
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py database.py states.py utils.py bot.py scheduler.py ./
COPY handlers ./handlers
COPY keyboards ./keyboards
COPY services ./services

# Логи и данные будут в volume
ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "bot.py"]
