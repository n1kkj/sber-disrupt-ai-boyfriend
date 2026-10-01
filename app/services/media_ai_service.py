import asyncio
import time
from typing import Any, List, NoReturn, Optional

from google import genai
from google.genai import types

from app.logging import logger
from app.services.gemini_rate_limiter import GeminiRateLimiter
from settings import config


class GeminiMultimodalService:
    @classmethod
    def _native_base_url(cls: type['GeminiMultimodalService']) -> str:
        native_base_url = config.gemini.native_base_url
        if native_base_url:
            return native_base_url.rstrip('/')
        return config.gemini.base_url.removesuffix('/v1').rstrip('/')

    @classmethod
    def _client(cls: type['GeminiMultimodalService']) -> genai.Client:
        if not config.gemini.api_key:
            raise ValueError('Не задан GEMINI_API_KEY для обработки media.')
        client_args = {}
        if config.gemini.proxy_url:
            client_args['proxy'] = config.gemini.proxy_url
        return genai.Client(
            api_key=config.gemini.api_key,
            http_options=types.HttpOptions(
                base_url=cls._native_base_url(),
                timeout=120000,
                client_args=client_args,
            ),
        )

    @classmethod
    def _raise_provider_error(
        cls: type['GeminiMultimodalService'],
        error: Exception,
    ) -> NoReturn:
        status_code = getattr(error, 'status_code', None)
        error_text = str(error).casefold()
        logger.exception(
            'gemini_multimodal_provider_error status=%s error=%s',
            status_code,
            error,
        )
        if status_code in {400, 401, 403} or 'api key' in error_text or 'unauthorized' in error_text:
            raise ValueError(
                'Gemini отклонил запрос media. Проверьте GEMINI_API_KEY, '
                'GEMINI_NATIVE_BASE_URL и GEMINI_MODEL в окружении Celery worker.'
            ) from error
        raise error

    @classmethod
    def _generate_text_sync(
        cls: type['GeminiMultimodalService'],
        contents: Any,
    ) -> str:
        response = None
        for attempt in range(1, 4):
            client = cls._client()
            try:
                GeminiRateLimiter.acquire()
                response = client.models.generate_content(
                    model=config.gemini.model,
                    contents=cls._to_user_content(contents),
                )
                break
            except Exception as error:
                if not cls._is_retryable_network_error(error) or attempt == 3:
                    cls._raise_provider_error(error)
                logger.warning(
                    'Ошибка соединения с Gemini, повторная попытка %s из 3: %s',
                    attempt + 1,
                    error,
                )
                time.sleep(attempt * 2)
            finally:
                client.close()

        if response is None:
            raise RuntimeError('Gemini не вернул ответ после повторных попыток')

        response_text = getattr(response, 'text', None)
        if response_text:
            return response_text.strip()

        text_parts: List[str] = []
        for candidate in getattr(response, 'candidates', None) or []:
            content = getattr(candidate, 'content', None)
            for part in getattr(content, 'parts', None) or []:
                part_text = getattr(part, 'text', None)
                if part_text:
                    text_parts.append(part_text)

        result = ' '.join(text_parts).strip()
        if not result:
            raise ValueError('Gemini не вернул текстовый результат')
        return result

    @classmethod
    def _is_retryable_network_error(
        cls: type['GeminiMultimodalService'],
        error: Exception,
    ) -> bool:
        error_text = str(error).casefold()
        return any(
            marker in error_text
            for marker in ('readerror', 'connection reset', 'connection error', 'timed out', 'timeout')
        )

    @classmethod
    def _to_user_content(
        cls: type['GeminiMultimodalService'],
        contents: list,
    ) -> types.Content:
        parts = []
        for item in contents:
            if isinstance(item, str):
                parts.append(types.Part.from_text(text=item))
            else:
                parts.append(item)
        return types.Content(role='user', parts=parts)

    @classmethod
    async def _generate_text(
        cls: type['GeminiMultimodalService'],
        contents: Any,
    ) -> str:
        return await asyncio.to_thread(cls._generate_text_sync, contents)

    @classmethod
    async def transcribe_audio(
        cls: type['GeminiMultimodalService'],
        data: bytes,
        mime_type: str,
    ) -> str:
        logger.info('gemini_audio_transcription_started bytes=%s mime=%s', len(data), mime_type)
        contents = [
            'Точно транскрибируй аудио на языке оригинала. Верни только текст без комментариев и оформления.',
            types.Part.from_bytes(data=data, mime_type=mime_type),
        ]
        text = await cls._generate_text(contents)
        logger.info('gemini_audio_transcription_completed chars=%s', len(text))
        return text

    @classmethod
    async def describe_image(
        cls: type['GeminiMultimodalService'],
        data: bytes,
        mime_type: str,
    ) -> str:
        logger.info('gemini_image_description_started bytes=%s mime=%s', len(data), mime_type)
        contents = [
            'Кратко опиши изображение для контекста личного диалога. '
            'Не придумывай факты, 2-4 предложения.',
            types.Part.from_bytes(data=data, mime_type=mime_type),
        ]
        text = await cls._generate_text(contents)
        logger.info('gemini_image_description_completed chars=%s', len(text))
        return text

    @classmethod
    async def describe_sticker(
        cls: type['GeminiMultimodalService'],
        data: bytes,
        mime_type: str,
    ) -> str:
        logger.info('Начато описание стикера Gemini bytes=%s mime=%s', len(data), mime_type)
        contents = [
            'Определи смысл и эмоциональный посыл стикера для личного диалога. '
            'Кратко опиши персонажа, действие, эмоцию и уместный контекст, если они понятны. '
            'Не выдумывай детали, 1-3 предложения.',
            types.Part.from_bytes(data=data, mime_type=mime_type),
        ]
        text = await cls._generate_text(contents)
        logger.info('Описание стикера Gemini завершено chars=%s', len(text))
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
            'Не придумывай события между кадрами. Учитывай транскрипт аудио, если он есть. '
            '2-5 предложений.\n'
            f'Транскрипт аудио: {audio_transcript or "отсутствует"}'
        )
        contents: List[Any] = [prompt]
        for frame in frames:
            contents.append(types.Part.from_bytes(data=frame, mime_type='image/jpeg'))

        text = await cls._generate_text(contents)
        logger.info('gemini_video_description_completed chars=%s', len(text))
        return text
