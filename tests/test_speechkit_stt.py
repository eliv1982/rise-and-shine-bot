import asyncio

from config import SttProviderConfig
from services import speechkit_stt


def test_openai_cross_language_fallback_prefers_ru_when_auto_result_is_poor(monkeypatch, tmp_path):
    audio = tmp_path / "sample.ogg"
    audio.write_bytes(b"fake")

    cfg = SttProviderConfig(
        provider="openai",
        base_url="https://api.openai.com/v1",
        api_key="x",
        model="gpt-4o-mini-transcribe",
        language="",
        timeout_seconds=30,
        options={"allow_cross_language_stt_fallback": True},
    )
    monkeypatch.setattr(speechkit_stt, "get_stt_provider_config", lambda: cfg)

    async def _fake_once(_cfg, _audio_path, language_hint):
        if language_hint == "auto":
            return "do stoint weh weh weh"
        return "достоинство и вера в себя"

    monkeypatch.setattr(speechkit_stt, "_transcribe_once", _fake_once)
    result = asyncio.run(speechkit_stt.transcribe_audio_with_meta(str(audio), language="en"))
    assert result["recognized_text_final"] == "достоинство и вера в себя"
    assert result["stt_language_attempts"] == ["en", "ru"]
