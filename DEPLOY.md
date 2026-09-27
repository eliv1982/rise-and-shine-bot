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

### Архитектура production-БД

Бот работает в Docker Compose (`docker-compose.yml` в этом репозитории) — один проект (`rise-and-shine-bot`, по имени каталога) с двумя сервисами: `bot` и `postgres`. PostgreSQL в проде — **сервис `postgres` в этом же compose-стеке**, не отдельный внешний сервис. Данные PostgreSQL хранятся в named volume `postgres_data` (реальное имя Docker-volume — `rise-and-shine-bot_postgres_data`). Бот ждёт, пока `postgres` станет healthy (`depends_on: condition: service_healthy`), и подключается к нему через `DATABASE_URL` по Compose-хосту `postgres`.

Важно про сетевую доступность: `localhost`/`127.0.0.1` внутри контейнера бота указывает на сам контейнер, а не на сервис `postgres` — так Postgres не увидеть. В `DATABASE_URL` используй Compose DNS-имя `postgres` (как в `.env.example`), а не `localhost`/IP хоста. `scripts/check_runtime_config.py` (см. ниже) предупреждает, если `DATABASE_URL` указывает на `localhost`. Порт PostgreSQL наружу (на хост) не публикуется — это не нужно для работы бота.

Если `DATABASE_URL` не задан, бот использует SQLite (`bot.db`) — это фолбэк для локальной разработки без Docker Compose, не production-конфигурация; сам `docker-compose.yml` всегда поднимает `postgres` (сервис не опционален).

Подробнее: [docs/production_env.md](docs/production_env.md).

### Первый запуск на сервере

1. Клонируй репозиторий (или скопируй проект). Имя каталога определяет имя Compose-проекта (и, следовательно, префикс имён volume) — на живом сервере это `rise-and-shine-bot`:
   ```bash
   git clone <url-репозитория> /opt/rise-and-shine-bot
   cd /opt/rise-and-shine-bot
   ```
2. Создай `.env` с реальными значениями (`BOT_TOKEN`, `OPENAI_API_KEY`, `DATABASE_URL`, `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` и т.д. — см. `.env.example`).
3. Если volume `bot_data` уже существовал и заполнялся контейнером, работавшим от root (до Stage 5), один раз поправь владельца перед первым запуском нового образа:
   ```bash
   docker run --rm -v rise-and-shine-bot_bot_data:/data alpine chown -R 1000:1000 /data
   ```
   Для полностью нового volume это не требуется — Dockerfile создаёт `/app/data` от имени непривилегированного пользователя. **Volume `postgres_data` (владение управляется образом `postgres:16`) трогать `chown` нельзя** — не относится к non-root-хардненингу бота.
4. Прогони префлайт и запусти:
   ```bash
   ./scripts/preflight.sh
   docker compose up -d --build
   ```

Контейнер запущен с политикой **restart: unless-stopped**: при перезагрузке сервера Docker поднимет контейнер автоматически.

### Префлайт, бэкап и smoke-check

- `./scripts/preflight.sh` — перед деплоем проверяет чистое рабочее дерево, наличие `.env`, доступность Docker и корректность runtime-конфигурации (`scripts/preflight_check.py` + `scripts/check_runtime_config.py`). Без сетевых запросов.
- `./scripts/backup.sh [каталог]` — бэкап БД перед деплоем: `pg_dump` для PostgreSQL (через `docker compose exec postgres`, т.к. хост `postgres` в `DATABASE_URL` доступен только внутри Compose-сети), безопасный онлайн-бэкап для SQLite (автоопределение по `DATABASE_URL`).
- `./scripts/restore.sh <файл-бэкапа>` — восстановление из бэкапа (`pg_restore` для `.dump` через `docker compose exec postgres`, копирование файла для `.db`); интерактивное подтверждение, не запускается автоматически.
- `./scripts/smoke_check.sh` — после `docker compose up -d` читает `docker compose ps`/`logs` и проверяет, что контейнер поднялся, БД инициализирована, задачи планировщика зарегистрированы и в логах нет traceback. Не делает сетевых вызовов к Telegram/OpenAI.
- `./scripts/deploy.sh` уже вызывает `preflight.sh` перед `git pull`/пересборкой — см. ниже.

Перед первым продакшн-деплоем на новую конфигурацию рекомендуется сделать бэкап (`./scripts/backup.sh`) и один раз вручную проверить восстановление из него (`./scripts/restore.sh`) на тестовой БД — это ещё не проверено вживую для PostgreSQL-бэкапа (см. Stage 7).

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
| Smoke-check после деплоя | `./scripts/smoke_check.sh` |
| Бэкап БД | `./scripts/backup.sh` |
| Восстановление из бэкапа (откат данных) | `./scripts/restore.sh <файл-бэкапа>` |

### Переменные окружения в Docker

- **BOT_DATA_DIR** — в контейнере задаётся `/app/data`. В этот каталог монтируется volume: там хранятся `bot.db`, `bot.log` и папка `outputs` (картинки, озвучки).
- Остальные переменные берутся из `.env` (env_file в docker-compose).

### ffmpeg

В образ уже установлен ffmpeg (озвучка с паузами работает без доп. настроек на сервере).
