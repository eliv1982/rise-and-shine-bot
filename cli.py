import argparse
import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Optional

from services.yandex_gpt import generate_affirmations
from services.openai_image import generate_image
from services.speechkit_stt import transcribe_audio


def setup_logging() -> None:
    """
    Простая настройка логирования в консоль.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def parse_args() -> argparse.Namespace:
    """
    Парсинг аргументов командной строки.
    """
    parser = argparse.ArgumentParser(
        description="CLI-прототип генерации аффирмаций и позитивных картинок.",
    )

    parser.add_argument(
        "--sphere",
        required=True,
        choices=["career", "relationships", "health", "money", "spirituality"],
        help="Сфера жизни (career, relationships, health, money, spirituality).",
    )

    parser.add_argument(
        "--subsphere",
        required=False,
        choices=["partner", "colleagues", "friends"],
        help="Подсфера для relationships (partner, colleagues, friends). Опционально.",
    )

    parser.add_argument(
        "--image_style",
        required=True,
        choices=[
            "realistic",
            "cartoon",
            "mandala",
            "sacred_geometry",
            "nature",
            "cosmos",
            "abstract",
        ],
        help="Стиль изображения.",
    )

    parser.add_argument(
        "--language",
        required=False,
        choices=["ru", "en"],
        default="ru",
        help="Язык аффирмаций (ru/en). По умолчанию ru.",
    )

    parser.add_argument(
        "--theme_text",
        required=False,
        help="Опциональный текст-уточнение темы от пользователя.",
    )

    parser.add_argument(
        "--audio_path",
        required=False,
        help="Путь к аудиофайлу (ogg/mp3/wav) для голосового ввода темы.",
    )

    parser.add_argument(
        "--output_json",
        action="store_true",
        help="Если указан, аффирмации выводятся в JSON-формате.",
    )

    return parser.parse_args()


def _validate_args(args: argparse.Namespace) -> None:
    """
    Дополнительная валидация связок sphere/subsphere.
    """
    if args.subsphere and args.sphere != "relationships":
        raise SystemExit("--subsphere допустим только при --sphere=relationships")
    if args.sphere == "relationships" and not args.subsphere:
        logging.getLogger(__name__).info(
            "Sphere=relationships, но subsphere не задан. Будет использована общая тема для отношений."
        )


async def async_main() -> None:
    """
    Асинхронная точка входа: параллельный запрос YandexGPT и генерации изображения.
    """
    setup_logging()
    logger = logging.getLogger("cli")

    args = parse_args()
    _validate_args(args)

    sphere: str = args.sphere
    subsphere: Optional[str] = args.subsphere
    image_style: str = args.image_style
    language: str = args.language
    user_text: Optional[str] = args.theme_text
    audio_path: Optional[str] = getattr(args, "audio_path", None)

    logger.info(
        "Starting generation: sphere=%s, subsphere=%s, style=%s, language=%s, audio_path=%s",
        sphere,
        subsphere,
        image_style,
        language,
        audio_path,
    )

    # Если передан audio_path – сначала распознаём речь и используем текст как тему.
    if audio_path:
        logger.info("Audio path provided, starting SpeechKit STT transcription.")
        try:
            recognized_text = await transcribe_audio(audio_path=audio_path, language=language)
        except Exception as exc:
            logger.exception("Speech recognition failed: %s", exc)
            raise SystemExit(f"Speech recognition failed: {exc}") from exc

        # Приоритет у аудио над theme_text.
        user_text = recognized_text
        logger.info("Using recognized text as theme_text: %s", recognized_text)

    try:
        affirmations_task = generate_affirmations(
            sphere=sphere,
            language=language,
            user_text=user_text,
            subsphere=subsphere,
        )
        image_task = generate_image(
            style=image_style,
            sphere=sphere,
            user_text=user_text,
            subsphere=subsphere,
        )

        affirmations, image_path = await asyncio.gather(affirmations_task, image_task)
    except Exception as exc:
        logger.exception("Generation failed: %s", exc)
        raise SystemExit(f"Generation failed: {exc}") from exc

    # Сохраняем аффирмации в outputs/ как JSON.
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name_parts = ["affirmations", sphere]
    if subsphere:
        base_name_parts.append(subsphere)
    base_name_parts.append(language)
    base_name_parts.append(timestamp)
    affirmations_filename = "_".join(base_name_parts) + ".json"
    affirmations_path = os.path.join(output_dir, affirmations_filename)

    with open(affirmations_path, "w", encoding="utf-8") as f:
        json.dump(affirmations, f, ensure_ascii=False, indent=2)

    print("\n=== AFFIRMATIONS ===")
    if args.output_json:
        print(json.dumps(affirmations, ensure_ascii=False, indent=2))
    else:
        for idx, text in enumerate(affirmations, start=1):
            print(f"{idx}. {text}")
    print(f"\nAffirmations saved to: {affirmations_path}")

    print("\n=== IMAGE ===")
    print(f"Saved to: {image_path}")


def main() -> None:
    """
    Синхронная обёртка вокруг async_main для удобного запуска `python cli.py`.
    """
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")


if __name__ == "__main__":
    main()

