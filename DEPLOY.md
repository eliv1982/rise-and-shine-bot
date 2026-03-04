# Деплой бота Rise and Shine Daily

## Локальный запуск через Docker

1. Создай `.env` в корне проекта (скопируй из `.env.example` и заполни ключи).
2. Собери и запусти:
   ```bash
   docker compose up -d --build
   ```
3. Логи: `docker compose logs -f bot`
4. Остановка: `docker compose down`

Данные (БД, логи, картинки, TTS) хранятся в volume `bot_data` и сохраняются при перезапуске контейнера и обновлении образа.

---

## Деплой на сервер

### Требования на сервере

- Docker и Docker Compose (v2)
- Git (если деплой через `git pull`)

### Первый запуск на сервере

1. Клонируй репозиторий (или скопируй проект):
   ```bash
   git clone <url-репозитория> /opt/rise-and-shine
   cd /opt/rise-and-shine
   ```
2. Создай `.env` с реальными ключами (BOT_TOKEN, YANDEX_*, PROXI_* и т.д.).
3. Запусти:
   ```bash
   docker compose up -d --build
   ```

Контейнер запущен с политикой **restart: unless-stopped**: при перезагрузке сервера Docker поднимет контейнер автоматически.

### Подтягивание изменений с локальной машины

Вариант **A — вручную**: после `git push` зайди на сервер и выполни:
```bash
cd /opt/rise-and-shine
./scripts/deploy.sh
```
Скрипт сделает `git pull`, пересоберёт образ и перезапустит контейнер.

Вариант **B — автоматически по расписанию**: добавь cron (crontab -e), например каждые 5 минут:
```cron
*/5 * * * * cd /opt/rise-and-shine && ./scripts/deploy.sh >> /var/log/rise-and-shine-deploy.log 2>&1
```
Тогда после `git push` в течение нескольких минут на сервере подтянется новый код и бот перезапустится.

Вариант **C — по webhook (GitHub/GitLab)**: настрой CI (например GitHub Actions), который по push подключается к серверу по SSH и выполняет `./scripts/deploy.sh`. Подробности зависят от твоего репозитория и доступа к серверу.

### Полезные команды на сервере

| Действие | Команда |
|----------|--------|
| Логи бота | `docker compose logs -f bot` |
| Перезапуск | `docker compose restart bot` |
| Остановка | `docker compose down` |
| Запуск | `docker compose up -d` |

### Переменные окружения в Docker

- **BOT_DATA_DIR** — в контейнере задаётся `/app/data`. В этот каталог монтируется volume: там хранятся `bot.db`, `bot.log` и папка `outputs` (картинки, озвучки).
- Остальные переменные берутся из `.env` (env_file в docker-compose).

### ffmpeg

В образ уже установлен ffmpeg (озвучка с паузами работает без доп. настроек на сервере).
