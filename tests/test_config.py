from config import get_settings


def _set_required_env(monkeypatch):
    monkeypatch.setenv("YANDEX_API_KEY", "test")
    monkeypatch.setenv("YANDEX_FOLDER_ID", "test")
    monkeypatch.setenv("PROXI_API_KEY", "test")
    monkeypatch.setenv("BOT_TOKEN", "test")


def test_daily_generation_limit_defaults_to_five(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.delenv("DAILY_GENERATION_LIMIT", raising=False)
    monkeypatch.delenv("GENERATION_DAILY_LIMIT", raising=False)
    monkeypatch.delenv("DISABLE_DAILY_GENERATION_LIMIT", raising=False)

    settings = get_settings()

    assert settings.generation_daily_limit == 5
    assert settings.disable_daily_generation_limit is False


def test_daily_generation_limit_zero_means_no_limit(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("DAILY_GENERATION_LIMIT", "0")

    settings = get_settings()

    assert settings.generation_daily_limit == 0


def test_disable_daily_generation_limit_env(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("DAILY_GENERATION_LIMIT", "5")
    monkeypatch.setenv("DISABLE_DAILY_GENERATION_LIMIT", "true")

    settings = get_settings()

    assert settings.generation_daily_limit == 5
    assert settings.disable_daily_generation_limit is True
