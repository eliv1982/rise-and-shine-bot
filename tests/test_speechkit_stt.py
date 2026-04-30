import asyncio

from config import SttProviderConfig
from services import speechkit_stt


def test_yandex_fallback_prefers_ru_when_en_result_is_poor(monkeypatch, tmp_path):
    audio = tmp_path / "sample.ogg"
    audio.write_bytes(b"fake")

    cfg = SttProviderConfig(
        provider="yandex",
        base_url=None,
        api_key="x",
        model="general",
        language="",
        timeout_seconds=30,
        options={"folder_id": "f", "prefer_language": "ru-RU"},
    )
    monkeypatch.setattr(speechkit_stt, "get_stt_provider_config", lambda: cfg)

    async def _fake_once(_cfg, _audio_path, language_hint):
        if language_hint == "en":
            return "do stoint weh weh weh"
        return "достоинство и вера в себя"

    monkeypatch.setattr(speechkit_stt, "_transcribe_once", _fake_once)
    result = asyncio.run(speechkit_stt.transcribe_audio_with_meta(str(audio), language="en"))
    assert result["recognized_text_final"] == "достоинство и вера в себя"
    assert result["stt_language_attempts"] == ["ru"]
