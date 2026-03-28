import os

# Минимальные переменные до импорта модулей, вызывающих get_settings()
os.environ.setdefault("YANDEX_API_KEY", "test-yandex-key")
os.environ.setdefault("YANDEX_FOLDER_ID", "test-folder")
os.environ.setdefault("PROXI_API_KEY", "test-proxi-key")
os.environ.setdefault("BOT_TOKEN", "test-bot-token")
