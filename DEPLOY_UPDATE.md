# Как скопировать изменения на сервер и проверить

## Деплой через Docker Hub (рекомендуется)

Не нужно копировать файлы на сервер — образ собираешь локально, пушишь в Docker Hub, на сервере только подтягиваешь образ и перезапускаешь.

**1. Локально (в корне проекта):** войти в Docker Hub, собрать и отправить образ (подставь свой логин Docker Hub):

```powershell
docker login
docker build -t DOCKERHUB_USERNAME/rise-and-shine-bot:latest .
docker push DOCKERHUB_USERNAME/rise-and-shine-bot:latest
```

**2. На сервере по SSH:** обновить образ и перезапустить контейнер:

```bash
cd /opt/rise-and-shine
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

Подробная настройка (первый запуск, .env, compose) — в **DEPLOY_DOCKERHUB.md**.

---

## 1. Скопировать код на сервер (если не используешь Docker Hub)

### Вариант А: через Git (если репозиторий уже привязан)

**На своём компьютере** (в папке проекта, где есть git):

```powershell
git add .
git commit -m "Разнообразие картинок, кнопки подписки, random сфера/стиль"
git push origin main
```

**На сервере** (по SSH):

```bash
cd /opt/rise-and-shine
./scripts/deploy.sh
```

Скрипт сделает `git pull`, пересоберёт образ и перезапустит контейнер.

---

### Вариант Б: копирование файлов без Git

Скопировать изменённые файлы на сервер (подставь свой `user` и `server`):

**Из PowerShell (Windows)** — через SCP:

```powershell
scp -r "c:\Users\eliv\Cursor_Projects\Promt engineering\Multimodal\Telegram_bot_Rise_and_Shine\handlers" user@server:/opt/rise-and-shine/
scp -r "c:\Users\eliv\Cursor_Projects\Promt engineering\Multimodal\Telegram_bot_Rise_and_Shine\keyboards" user@server:/opt/rise-and-shine/
scp -r "c:\Users\eliv\Cursor_Projects\Promt engineering\Multimodal\Telegram_bot_Rise_and_Shine\services" user@server:/opt/rise-and-shine/
scp "c:\Users\eliv\Cursor_Projects\Promt engineering\Multimodal\Telegram_bot_Rise_and_Shine\scheduler.py" user@server:/opt/rise-and-shine/
```

**Или одной папкой** (если на сервере нет важных локальных правок):

```powershell
scp -r "c:\Users\eliv\Cursor_Projects\Promt engineering\Multimodal\Telegram_bot_Rise_and_Shine\*" user@server:/opt/rise-and-shine/
```

Не копируй на сервер файл `.env` с сервера — на сервере должен остаться свой `.env` с ключами.

**На сервере** после копирования:

```bash
cd /opt/rise-and-shine
docker compose build --no-cache
docker compose up -d
```

---

## 2. Проверить, что бот запустился

На сервере:

```bash
docker compose logs -f bot
```

Убедись, что в логах нет ошибок при старте. Выход: `Ctrl+C`.

---

## 3. Что проверить в Telegram

1. **Подписка**
   - Напиши боту `/subscribe` или нажми «Настроить подписку» после генерации.
   - Должны быть пункты **«Разные сферы каждый день»** и **«Разный стиль каждый день»** в списках выбора.
   - Выбери сферу и стиль, время, подтверди — должно прийти короткое сообщение: «Подписка сохранена. Рассылка в HH:MM.»

2. **Кнопки под рассылкой**
   - Дождись следующей рассылки по подписке (или временно поставь время на ближайшие минуты и подожди).
   - Под сообщением должны быть кнопки: **Озвучить**, **Отменить подписку**, **Изменить подписку**.
   - Нажми «Изменить подписку» — должно прийти новое сообщение с выбором сферы.
   - При необходимости нажми «Отменить подписку» — должно прийти «Подписка отменена.»

3. **Разнообразие картинок**
   - Оформи подписку с одной сферой и одним стилем (например, «Внутренний покой» + «Природа»).
   - В следующие дни картинки должны отличаться (разная цветовая гамма и композиция при том же стиле).

---

## 4. Если что-то пошло не так

- **Откат на сервере:** если делал `git pull`, откати коммит и перезапусти:
  ```bash
  git log -1
  git reset --hard HEAD~1
  docker compose up -d --build
  ```
- **Логи:** `docker compose logs -f bot` — смотреть стек ошибок.
- **Перезапуск контейнера:** `docker compose restart bot`
