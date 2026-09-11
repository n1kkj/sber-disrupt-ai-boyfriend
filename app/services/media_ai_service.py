from typing import List, Optional

from google import genai
from google.genai import types

from app.logging import logger
from settings import config


class GeminiMultimodalService:
    @classmethod
    def _client(cls: type['GeminiMultimodalService']) -> genai.Client:
        if not config.gemini.api_key:
            raise ValueError('Не задан GEMINI_API_KEY для обработки media.')
        return genai.Client(api_key=config.gemini.api_key)

    @classmethod
    async def transcribe_audio(
        cls: type['GeminiMultimodalService'],
        data: bytes,
        mime_type: str,
    ) -> str:
        logger.info('gemini_audio_transcription_started bytes=%s mime=%s', len(data), mime_type)
        client = cls._client()
        response = await client.aio.models.generate_content(
            model=config.gemini.model,
            contents=[
                'Точно транскрибируй аудио на языке оригинала. Верни только текст без комментариев и оформления.',
                types.Part.from_bytes(data=data, mime_type=mime_type),
            ],
        )
        text = (response.text or '').strip()
        if not text:
            raise ValueError('Gemini не вернул транскрипт аудио')
        logger.info('gemini_audio_transcription_completed chars=%s', len(text))
        return text

    @classmethod
    async def describe_image(
        cls: type['GeminiMultimodalService'],
        data: bytes,
        mime_type: str,
    ) -> str:
        logger.info('gemini_image_description_started bytes=%s mime=%s', len(data), mime_type)
        client = cls._client()
        response = await client.aio.models.generate_content(
            model=config.gemini.model,
            contents=[
                'Кратко опиши изображение для контекста личного диалога. Не придумывай факты, 2-4 предложения.',
                types.Part.from_bytes(data=data, mime_type=mime_type),
            ],
        )
        text = (response.text or '').strip()
        if not text:
            raise ValueError('Gemini не вернул описание изображения')
        logger.info('gemini_image_description_completed chars=%s', len(text))
        return text

    @classmethod
    async def describe_video_frames(
        cls: type['GeminiMultimodalService'],
        frames: List[bytes],
        audio_transcript: Optional[str],
    ) -> str:
        if not frames:
            return 'Видео не содержит доступных кадров.'
        logger.info('gemini_video_description_started frames=%s', len(frames))
        prompt = (
            'Кратко опиши, что происходит на видео по выбранным кадрам. '
            'Не придумывай события между кадрами. Учитывай транскрипт аудио, если он есть. 2-5 предложений.\n'
            f'Транскрипт аудио: {audio_transcript or "отсутствует"}'
        )
        contents: List[object] = [prompt]
        contents.extend(types.Part.from_bytes(data=frame, mime_type='image/jpeg') for frame in frames)
        client = cls._client()
        response = await client.aio.models.generate_content(model=config.gemini.model, contents=contents)
        text = (response.text or '').strip()
        if not text:
            raise ValueError('Gemini не вернул описание видео')
        logger.info('gemini_video_description_completed chars=%s', len(text))
        return text
