# Деплой через Docker Hub

Образ хранится на Docker Hub. Подставь **свой логин Docker Hub** и **хост/IP сервера** в команды ниже.

Используется **один** файл [docker-compose.yml](docker-compose.yml): локально он собирает образ (`build`), на сервере с тем же файлом и переменной `DOCKERHUB_IMAGE` в `.env` выполняется `pull` готового образа (сборка на сервере не нужна).

**Кратко (обновление после изменений в коде):** локально `docker build` + `docker push` (или `docker compose build && docker compose push` при заданном `DOCKERHUB_IMAGE` в `.env`), на сервере `docker compose pull && docker compose up -d`.

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
docker compose build
docker compose push
```

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

**Создать каталог:**
```bash
mkdir -p /opt/rise-and-shine
cd /opt/rise-and-shine
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
YANDEX_API_KEY=твой_яндекс_ключ
YANDEX_FOLDER_ID=твой_folder_id
YANDEX_SPEECHKIT_API_KEY=твой_speechkit_ключ
PROXI_API_KEY=твой_proxi_ключ
PROXI_BASE_URL=https://openai.api.proxyapi.ru/v1
```

Остальные переменные — по необходимости из `.env.example` в репозитории.

Сохранить: `Ctrl+O`, Enter, выход: `Ctrl+X`.

Compose подставит `DOCKERHUB_IMAGE` в поле `image:` сервиса `bot` и подтянет образ с Docker Hub. Секция `build` в том же файле на сервере не используется, если не запускать `docker compose build`.

---

## 4. Запуск и обновление на сервере

**Первый запуск:**
```bash
cd /opt/rise-and-shine
docker compose pull
docker compose up -d
```

**Проверка:**
```bash
docker compose ps
docker compose logs -f bot
```
Выход из логов: `Ctrl+C`.

**После `docker push` с локальной машины — обновить бота:**
```bash
cd /opt/rise-and-shine
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
*/10 * * * * cd /opt/rise-and-shine && docker compose pull -q && docker compose up -d >> /var/log/rise-and-shine-deploy.log 2>&1
```

---

## 7. Полезные команды на сервере

| Действие | Команда |
|----------|---------|
| Логи бота | `cd /opt/rise-and-shine && docker compose logs -f bot` |
| Остановить | `cd /opt/rise-and-shine && docker compose down` |
| Запустить | `cd /opt/rise-and-shine && docker compose up -d` |
| Перезапустить | `cd /opt/rise-and-shine && docker compose restart bot` |
| Подтянуть образ и перезапустить | `cd /opt/rise-and-shine && docker compose pull && docker compose up -d` |

Все команды выполнять **на сервере** после SSH.
