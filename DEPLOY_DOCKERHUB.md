# Деплой через Docker Hub

Образ хранится на Docker Hub. Подставь **свой логин Docker Hub** и **хост/IP сервера** в команды ниже.

**Кратко (обновление после изменений в коде):** локально `docker build` + `docker push`, на сервере `docker compose -f docker-compose.prod.yml pull && docker compose -f docker-compose.prod.yml up -d`.

---

## 1. На локальном компьютере (сборка и публикация образа)

Открыть терминал в **корне проекта** (где лежит `Dockerfile`).

**Вход в Docker Hub:**
```bash
docker login
```
Ввести свой логин и пароль от Docker Hub.

**Сборка и пуш образа** (подставь свой логин вместо `DOCKERHUB_USERNAME`):
```bash
docker build -t DOCKERHUB_USERNAME/rise-and-shine-bot:latest .
docker push DOCKERHUB_USERNAME/rise-and-shine-bot:latest
```

После каждого изменения кода: снова выполнить эти две команды, затем на сервере подтянуть образ и перезапустить (см. раздел 4).

---

## 2. Подключение к серверу

**Вводить в своём терминале (PowerShell или cmd):**
```bash
ssh root@SERVER_HOST
```
Вместо `SERVER_HOST` — IP или доменное имя сервера. Дальше все команды — **уже на сервере** (в этой SSH-сессии).

---

## 3. Первый раз на сервере: каталог, .env и compose

**Создать каталог:**
```bash
mkdir -p /opt/rise-and-shine
cd /opt/rise-and-shine
```

**Создать файл с переменными окружения:**
```bash
nano .env
```
Вставить (подставить свои значения):
```
BOT_TOKEN=токен_от_BotFather
YANDEX_API_KEY=твой_яндекс_ключ
YANDEX_FOLDER_ID=твой_folder_id
YANDEX_SPEECHKIT_API_KEY=твой_speechkit_ключ
PROXI_API_KEY=твой_proxi_ключ
PROXI_BASE_URL=https://openai.api.proxyapi.ru/v1
```
Сохранить: `Ctrl+O`, Enter, выход: `Ctrl+X`.

**Создать production compose (образ с Docker Hub):**
```bash
nano docker-compose.prod.yml
```
Вставить (подставь свой логин Docker Hub вместо `DOCKERHUB_USERNAME`):
```yaml
services:
  bot:
    image: DOCKERHUB_USERNAME/rise-and-shine-bot:latest
    container_name: rise-and-shine-bot
    restart: unless-stopped
    env_file: .env
    volumes:
      - bot_data:/app/data
    environment:
      - BOT_DATA_DIR=/app/data

volumes:
  bot_data:
```
Сохранить: `Ctrl+O`, Enter, выход: `Ctrl+X`.

---

## 4. Запуск и обновление на сервере

**Первый запуск:**
```bash
cd /opt/rise-and-shine
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

**Проверка:**
```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f bot
```
Выход из логов: `Ctrl+C`.

**После того как на локальной машине сделали `docker build` и `docker push` — обновить бота на сервере:**
```bash
cd /opt/rise-and-shine
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

---

## 5. Автоперезапуск при перезагрузке сервера

Уже настроено: в compose указано `restart: unless-stopped`. После перезагрузки сервера контейнер поднимется сам.

---

## 6. Автообновление по расписанию (по желанию)

Чтобы сервер сам периодически подтягивал новый образ и перезапускал контейнер:

```bash
crontab -e
```
Добавить строку (например, раз в 10 минут):
```
*/10 * * * * cd /opt/rise-and-shine && docker compose -f docker-compose.prod.yml pull -q && docker compose -f docker-compose.prod.yml up -d >> /var/log/rise-and-shine-deploy.log 2>&1
```
Сохранить и выйти.

---

## 7. Полезные команды на сервере

| Действие              | Команда |
|-----------------------|--------|
| Логи бота             | `cd /opt/rise-and-shine && docker compose -f docker-compose.prod.yml logs -f bot` |
| Остановить            | `cd /opt/rise-and-shine && docker compose -f docker-compose.prod.yml down` |
| Запустить             | `cd /opt/rise-and-shine && docker compose -f docker-compose.prod.yml up -d` |
| Перезапустить         | `cd /opt/rise-and-shine && docker compose -f docker-compose.prod.yml restart bot` |
| Подтянуть образ и перезапустить | `cd /opt/rise-and-shine && docker compose -f docker-compose.prod.yml pull && docker compose -f docker-compose.prod.yml up -d` |

Все команды выполнять **на сервере** после подключения по SSH.
