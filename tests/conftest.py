import os
import pytest

# Минимальные переменные до импорта модулей, вызывающих get_settings()
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("BOT_TOKEN", "test-bot-token")
os.environ.setdefault("OPENAI_BASE_URL", "https://api.openai.com/v1")
os.environ.setdefault("OPENAI_TEXT_MODEL", "gpt-4o-mini")
os.environ.setdefault("OPENAI_IMAGE_MODEL", "gpt-image-1")
os.environ.setdefault("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
os.environ.setdefault("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe")
os.environ.setdefault("YANDEX_API_KEY", "test-yandex-key")
os.environ.setdefault("YANDEX_FOLDER_ID", "test-folder")
os.environ.setdefault("PROXI_API_KEY", "test-proxi-key")


@pytest.fixture(autouse=True)
def isolate_provider_env(monkeypatch):
    monkeypatch.setenv("TEXT_PROVIDER", "openai")
    monkeypatch.setenv("IMAGE_PROVIDER", "openai")
    monkeypatch.setenv("TTS_PROVIDER", "openai")
    monkeypatch.setenv("STT_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
    monkeypatch.setenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
    monkeypatch.setenv("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe")
    monkeypatch.setenv("BOT_TOKEN", "test-bot-token")
