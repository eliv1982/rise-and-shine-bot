# Rise and Shine Daily

Telegram-бот для ежедневных аффирмаций: генерация текста (Yandex GPT), картинок (OpenAI-совместимый API) и озвучка (Yandex SpeechKit). Поддержка голосового ввода темы и стиля, подписка на рассылку. Языки: русский и английский.

## Возможности

- **Регистрация** — имя, пол (учёт рода в тексте аффирмаций).
- **Генерация аффирмаций** — Yandex GPT по выбранной сфере жизни и теме (текст или голос).
- **Генерация изображений** — стили (реалистичный, природа, космос, мандала и др.), опциональное описание голосом или текстом; разнообразная цветовая гамма и композиция при каждой генерации.
- **Озвучка** — Yandex SpeechKit TTS, паузы между аффирмациями (ffmpeg).
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

- Python 3.11+
- [aiogram](https://docs.aiogram.dev/) 3.x
- Yandex GPT, Yandex SpeechKit (TTS/STT), ProxiAPI (OpenAI-совместимый image API)
- SQLite (aiosqlite), APScheduler, Docker

## Требования

- Токен бота ([@BotFather](https://t.me/BotFather))
- API-ключи: Yandex Cloud (GPT + SpeechKit), ProxiAPI (или другой OpenAI-совместимый сервис для картинок)
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

### Docker

```bash
cp .env.example .env
# заполни .env
docker compose up -d --build
```

Локально имя образа по умолчанию — `rise-and-shine-bot:latest`. Для публикации в Docker Hub задай в `.env` переменную `DOCKERHUB_IMAGE=логин/rise-and-shine-bot:latest`, затем `docker compose build && docker compose push`.

Логи: `docker compose logs -f bot`

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `BOT_TOKEN` | Токен Telegram-бота |
| `YANDEX_API_KEY` | API-ключ Yandex Cloud (GPT) |
| `YANDEX_FOLDER_ID` | Идентификатор каталога Yandex Cloud |
| `YANDEX_SPEECHKIT_API_KEY` | API-ключ SpeechKit (TTS/STT), можно тот же, что и выше |
| `PROXI_API_KEY` | Ключ ProxiAPI (или аналог) |
| `PROXI_BASE_URL` | URL API (по умолчанию: `https://openai.api.proxyapi.ru/v1`) |

Опционально: `FFMPEG_PATH` — путь к ffmpeg, если не в PATH.

## Деплой на сервер

- **[DEPLOY.md](DEPLOY.md)** — общий деплой (Docker, скрипты, cron).
- **[DEPLOY_DOCKERHUB.md](DEPLOY_DOCKERHUB.md)** — деплой через образ на Docker Hub (один `docker-compose.yml`, на сервере в `.env` задаётся `DOCKERHUB_IMAGE`).

Важно: с одним токеном бота должен работать только один экземпляр (локально или на сервере), иначе Telegram вернёт ошибку Conflict.

## Структура проекта

```
├── bot.py              # Точка входа
├── config.py           # Настройки из .env
├── database.py         # SQLite, пользователи, подписки
├── states.py           # FSM-состояния
├── scheduler.py        # Ежедневная рассылка
├── handlers/           # Обработчики команд и сценариев
├── keyboards/          # Inline-клавиатуры
├── services/           # Yandex GPT, SpeechKit, генерация изображений
├── Dockerfile
└── docker-compose.yml        # локальная сборка и прод с Docker Hub (DOCKERHUB_IMAGE в .env)
```

## Лицензия

MIT (или укажи свою).
