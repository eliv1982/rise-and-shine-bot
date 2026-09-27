# Деплой через Docker Hub

Образ хранится на Docker Hub. Подставь **свой логин Docker Hub** и **хост/IP сервера** в команды ниже.

Используется **один** файл [docker-compose.yml](docker-compose.yml): локально он собирает образ (`build`), на сервере с тем же файлом и переменной `DOCKERHUB_IMAGE` в `.env` выполняется `pull` готового образа (сборка на сервере не нужна).

**Кратко (обновление после изменений в коде):** локально `docker build` + `docker push` (или `docker compose build bot && docker compose push bot` при заданном `DOCKERHUB_IMAGE` в `.env`), на сервере `docker compose pull && docker compose up -d`.

---

## 1. На локальном компьютере (сборка и публикация образа)

Открыть терминал в **корне проекта** (где лежит `Dockerfile`).

**Вход в Docker Hub:**
```bash
docker login
```

**Вариант А — вручную** (подставь свой логин вместо `DOCKERHUB_USERNAME`):
```bash
docker build -t DOCKERHUB_USERNAME/rise-and-shine-bot:latest .
docker push DOCKERHUB_USERNAME/rise-and-shine-bot:latest
```

**Вариант Б — через Compose** (в `.env` должна быть строка `DOCKERHUB_IMAGE=DOCKERHUB_USERNAME/rise-and-shine-bot:latest`):
```bash
docker compose build bot
docker compose push bot
```
Компоуз-файл включает и сервис `postgres` (образ `postgres:16` с Docker Hub, не собирается локально) — публикуй только `bot`; не пересобирай и не пушь `postgres` под свой логин.

После каждого изменения кода снова собери и запушь образ, затем на сервере подтяни образ и перезапусти контейнер (раздел 4).

---

## 2. Подключение к серверу

**В своём терминале (PowerShell или cmd):**
```bash
ssh root@SERVER_HOST
```
Вместо `SERVER_HOST` — IP или домен. Дальше команды выполняются **на сервере**.

---

## 3. Первый раз на сервере: каталог, .env и compose

**Создать каталог** — используй канонический production-путь `/home/elvi/apps/rise-and-shine-bot` (имя каталога определяет имя Compose-проекта и, следовательно, имена volumes с данными — см. [DEPLOY.md](DEPLOY.md#инвариант-каталог-и-имя-compose-проекта); не используй `/opt/rise-and-shine`):
```bash
mkdir -p /home/elvi/apps/rise-and-shine-bot
cd /home/elvi/apps/rise-and-shine-bot
```

**Положить в каталог файл `docker-compose.yml`** из репозитория (scp, git clone или скопировать содержимое с GitHub) — тот же файл, что в проекте.

**Создать `.env`:**
```bash
nano .env
```

Вставить (подставь свои значения; **обязательно** укажи образ с Hub):

```
DOCKERHUB_IMAGE=DOCKERHUB_USERNAME/rise-and-shine-bot:latest
BOT_TOKEN=токен_от_BotFather
OPENAI_API_KEY=твой_openai_ключ
POSTGRES_USER=rise_bot
POSTGRES_PASSWORD=надёжный_пароль
POSTGRES_DB=rise_bot
DATABASE_URL=postgresql://rise_bot:надёжный_пароль@postgres:5432/rise_bot
```

PostgreSQL — сервис `postgres` в этом же `docker-compose.yml` (не отдельный внешний сервис); `DATABASE_URL` указывает на него по Compose-хосту `postgres` — см. [DEPLOY.md](DEPLOY.md#архитектура-production-бд) и [docs/production_env.md](docs/production_env.md). `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` обязательны — без них `docker compose up` откажется стартовать. Без `DATABASE_URL` бот использует SQLite — это только для локальной разработки без Docker Compose, не для прода.

Остальные переменные — по необходимости из `.env.example` в репозитории.

Перед первым запуском на сервере выполни чек-лист из [DEPLOY.md](DEPLOY.md#первый-запуск-на-сервере) (владение volume, `./scripts/preflight.sh`, бэкап) — здесь он не дублируется.

Сохранить: `Ctrl+O`, Enter, выход: `Ctrl+X`.

Compose подставит `DOCKERHUB_IMAGE` в поле `image:` сервиса `bot` и подтянет образ с Docker Hub. Секция `build` в том же файле на сервере не используется, если не запускать `docker compose build`.

---

## 4. Запуск и обновление на сервере

**Первый запуск:**
```bash
cd /home/elvi/apps/rise-and-shine-bot
docker compose pull
docker compose up -d
```

**Проверка:**
```bash
docker compose ps
docker compose logs -f bot
./scripts/smoke_check.sh
```
Выход из логов: `Ctrl+C`.

**После `docker push` с локальной машины — обновить бота:**
```bash
cd /home/elvi/apps/rise-and-shine-bot
docker compose pull
docker compose up -d
```

---

## 5. Автоперезапуск при перезагрузке сервера

В compose указано `restart: unless-stopped`. После перезагрузки сервера контейнер поднимется сам.

---

## 6. Автообновление по расписанию (по желанию)

```bash
crontab -e
```

Пример (раз в 10 минут):
```
*/10 * * * * cd /home/elvi/apps/rise-and-shine-bot && docker compose pull -q && docker compose up -d >> /var/log/rise-and-shine-deploy.log 2>&1
```

---

## 7. Полезные команды на сервере

| Действие | Команда |
|----------|---------|
| Логи бота | `cd /home/elvi/apps/rise-and-shine-bot && docker compose logs -f bot` |
| Остановить | `cd /home/elvi/apps/rise-and-shine-bot && docker compose down` |
| Запустить | `cd /home/elvi/apps/rise-and-shine-bot && docker compose up -d` |
| Перезапустить | `cd /home/elvi/apps/rise-and-shine-bot && docker compose restart bot` |
| Подтянуть образ и перезапустить | `cd /home/elvi/apps/rise-and-shine-bot && docker compose pull && docker compose up -d` |

Все команды выполнять **на сервере** после SSH.
