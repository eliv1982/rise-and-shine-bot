# Rise and Shine Daily

Telegram-бот для ежедневных аффирмаций: генерация текста, картинок, озвучки (TTS) и распознавания голоса (STT) через OpenAI. Поддержка голосового ввода темы и стиля, подписка на ежедневную рассылку. Языки: русский и английский.

## Возможности

- **Регистрация** — имя, пол (учёт рода в тексте аффирмаций).
- **Генерация аффирмаций** — по выбранной сфере жизни и теме (текст или голос).
- **Генерация изображений** — стили (реалистичный, природа, космос, мандала и др.), опциональное описание голосом или текстом; разнообразная цветовая гамма и композиция при каждой генерации.
- **Озвучка** — TTS с паузами между аффирмациями (ffmpeg).
- **Ежедневная рассылка** — выбор языка, сферы, стиля картинки и времени; опции «разные сферы каждый день» и «разный стиль каждый день»; под сообщением рассылки — кнопки «Озвучить», «Отменить подписку», «Изменить подписку».
- **Язык** — переключение русский / English (`/language`); интерфейс и рассылка на выбранном языке.

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Регистрация или приветствие |
| `/new` | Новая аффирмация (сфера → стиль → генерация) |
| `/subscribe` | Подписка на ежедневные аффирмации |
| `/unsubscribe` | Отмена подписки |
| `/profile` | Профиль (имя, пол) |
| `/language` | Смена языка (русский / English) |
| `/help` | Справка по командам |
| `/cancel` | Выход из текущего диалога |
| `/reset` | Полный сброс регистрации |

## Стек

- Python 3.11 (версия в CI и продакшене; локальная разработка на другой совместимой версии допустима)
- [aiogram](https://docs.aiogram.dev/) 3.x
- OpenAI — единственный провайдер: текст, изображения, TTS, STT (прямые официальные эндпоинты `api.openai.com`)
- PostgreSQL в проде — сервис `postgres` в том же Docker Compose проекте, что и бот; SQLite — фолбэк для локальной разработки без Docker Compose
- APScheduler, Docker

## Требования

- Токен бота ([@BotFather](https://t.me/BotFather))
- Ключ OpenAI API
- Для озвучки с паузами: [ffmpeg](https://ffmpeg.org/) (в Docker-образе уже есть)

## Установка и запуск

### Локально

```bash
git clone https://github.com/eliv1982/rise-and-shine-bot.git
cd rise-and-shine-bot
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
```

Скопируй `.env.example` в `.env` и заполни переменные:

```bash
cp .env.example .env
```

Запуск:

```bash
python bot.py
```

По умолчанию (без `DATABASE_URL`) бот использует локальный SQLite-файл `bot.db`.

### Docker

```bash
cp .env.example .env
# заполни .env
docker compose up -d --build
```

Локально имя образа по умолчанию — `rise-and-shine-bot:latest`. Для публикации в Docker Hub задай в `.env` переменную `DOCKERHUB_IMAGE=логин/rise-and-shine-bot:latest`, затем `docker compose build bot && docker compose push bot` (только `bot` — `docker-compose.yml` включает и `postgres:16`, который не нужно и не следует пушить под свой логин; см. [DEPLOY_DOCKERHUB.md](DEPLOY_DOCKERHUB.md)).

Логи: `docker compose logs -f bot`

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `BOT_TOKEN` | Токен Telegram-бота |
| `OPENAI_API_KEY` | Ключ OpenAI API |
| `OPENAI_BASE_URL` | Официальный эндпоинт OpenAI (по умолчанию `https://api.openai.com/v1`) |
| `OPENAI_TEXT_MODEL` | По умолчанию `gpt-6-luna`; поддерживаются `gpt-6.1-terra` и явный откат на `gpt-4o-mini` |
| `OPENAI_TEXT_REASONING_EFFORT` | Для Luna/Terra: по умолчанию `none`, сохраняет текущую температуру; при включении reasoning температура исключается |
| `OPENAI_TEXT_MAX_COMPLETION_TOKENS` | Необязательный общий лимит ответа Luna/Terra, включая reasoning; без него 512 токенов для аффирмаций/промпта картинки и 200 для smalltalk |
| `OPENAI_IMAGE_MODEL` | По умолчанию `gpt-image-2.5-flare`; прежний `IMAGE_MODEL` сохранён как fallback |
| `DATABASE_URL` | `postgresql://...@postgres:5432/...` для PostgreSQL (сервис `postgres` в docker-compose.yml); если не задано — SQLite |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Обязательны для `docker compose up` (сервис `postgres`) |

Опционально: `FFMPEG_PATH` — путь к ffmpeg, если не в PATH.

Полный список переменных, рекомендуемый production-профиль, planner flags и архитектура production-БД — см. [docs/production_env.md](docs/production_env.md).

## Тесты и CI

```bash
python -m pytest
```

GitHub Actions запускает `python -m pytest` на Python 3.11 при каждом push и pull request ([.github/workflows/tests.yml](.github/workflows/tests.yml)).

Безопасное сравнение Luna/Terra: `python scripts/compare_text_models.py --output outputs/text-model-requests.json`
(каталог `outputs` должен существовать). По умолчанию это офлайн-манифест одинаковых
запросов без чтения `.env`, доступа к БД и сообщений в Telegram. Платный запуск,
критерии сравнения и порядок миграции описаны в [docs/text_model_migration.md](docs/text_model_migration.md).

## Деплой на сервер

- **[DEPLOY.md](DEPLOY.md)** — общий деплой (Docker, preflight, backup, smoke check, откат).
- **[DEPLOY_DOCKERHUB.md](DEPLOY_DOCKERHUB.md)** — деплой через образ на Docker Hub (один `docker-compose.yml`, на сервере в `.env` задаётся `DOCKERHUB_IMAGE`).
- **[DEPLOY_UPDATE.md](DEPLOY_UPDATE.md)** — короткая шпаргалка «как выкатить изменения».

Важно: с одним токеном бота должен работать только один экземпляр (локально или на сервере), иначе Telegram вернёт ошибку Conflict.

## Структура проекта

```
├── bot.py              # Точка входа
├── config.py           # Настройки из .env
├── database.py         # SQLite/PostgreSQL, пользователи, подписки
├── states.py           # FSM-состояния
├── scheduler.py        # Ежедневная рассылка
├── handlers/           # Обработчики команд и сценариев
├── keyboards/          # Inline-клавиатуры
├── services/           # OpenAI (текст, изображения, TTS, STT)
├── scripts/            # preflight, backup/restore, healthcheck и т.д.
├── Dockerfile
└── docker-compose.yml  # bot + postgres services; локальная сборка и прод с Docker Hub (DOCKERHUB_IMAGE в .env)
```

## Лицензия

MIT (или укажи свою).
