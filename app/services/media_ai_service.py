import base64
from typing import Any, List, NoReturn, Optional

from langchain_openai import ChatOpenAI
from openai import AsyncOpenAI

from app.clients.http_client import HttpClientFactory
from app.logging import logger
from settings import config


class GeminiMultimodalService:
    @classmethod
    def _client(cls: type['GeminiMultimodalService']) -> ChatOpenAI:
        if not config.gemini.api_key:
            raise ValueError('Не задан GEMINI_API_KEY для обработки media.')
        return ChatOpenAI(
            model=config.gemini.model,
            api_key=config.gemini.api_key,
            base_url=config.gemini.base_url,
            temperature=0,
            http_client=HttpClientFactory.get_httpx_proxy_client('gemini'),
            http_async_client=HttpClientFactory.get_httpx_async_proxy_client('gemini'),
        )

    @classmethod
    def _audio_client(cls: type['GeminiMultimodalService']) -> AsyncOpenAI:
        if not config.gemini.api_key:
            raise ValueError('Не задан GEMINI_API_KEY для распознавания audio.')
        return AsyncOpenAI(
            api_key=config.gemini.api_key,
            base_url=config.gemini.base_url,
            http_client=HttpClientFactory.get_httpx_async_proxy_client('gemini'),
        )

    @classmethod
    def _raise_provider_error(cls: type['GeminiMultimodalService'], error: Exception) -> NoReturn:
        status_code = getattr(error, 'status_code', None)
        response = getattr(error, 'response', None)
        status_code = status_code or getattr(response, 'status_code', None)
        error_text = str(error).casefold()
        if status_code in {400, 401, 403} or 'api key' in error_text or 'unauthorized' in error_text:
            raise ValueError(
                'LiteLLM отклонил запрос media. Проверьте GEMINI_API_KEY, GEMINI_BASE_URL '
                'и модели GEMINI_MODEL/GEMINI_TRANSCRIPTION_MODEL в окружении Celery worker.'
            ) from error
        raise error

    @classmethod
    async def _invoke(
        cls: type['GeminiMultimodalService'],
        content: List[dict[str, Any]],
    ) -> str:
        try:
            response = await cls._client().ainvoke([('user', content)])
        except Exception as error:
            cls._raise_provider_error(error)
        if isinstance(response.content, str):
            text = response.content
        else:
            text = ' '.join(str(part.get('text', part)) if isinstance(part, dict) else str(part) for part in response.content)
        result = text.strip()
        if not result:
            raise ValueError('LiteLLM не вернул текстовый результат')
        return result

    @classmethod
    async def transcribe_audio(
        cls: type['GeminiMultimodalService'],
        data: bytes,
        mime_type: str,
    ) -> str:
        logger.info('gemini_audio_transcription_started bytes=%s mime=%s', len(data), mime_type)
        filename = 'audio.wav' if mime_type in {'audio/wav', 'audio/x-wav'} else 'audio.mp3'
        model = config.gemini.transcription_model or config.gemini.model
        try:
            response = await cls._audio_client().audio.transcriptions.create(
                model=model,
                file=(filename, data, mime_type),
                response_format='text',
                prompt='Точно транскрибируй аудио на языке оригинала. Верни только текст без комментариев и оформления.',
            )
        except Exception as error:
            cls._raise_provider_error(error)
        text = response if isinstance(response, str) else str(getattr(response, 'text', '') or '')
        text = text.strip()
        if not text:
            raise ValueError('Artemox не вернул текст транскрибации')
        logger.info('gemini_audio_transcription_completed chars=%s', len(text))
        return text

    @classmethod
    async def describe_image(
        cls: type['GeminiMultimodalService'],
        data: bytes,
        mime_type: str,
    ) -> str:
        logger.info('gemini_image_description_started bytes=%s mime=%s', len(data), mime_type)
        data_url = f'data:{mime_type};base64,{base64.b64encode(data).decode("ascii")}'
        text = await cls._invoke([
            {
                'type': 'text',
                'text': 'Кратко опиши изображение для контекста личного диалога. Не придумывай факты, 2-4 предложения.',
            },
            {'type': 'image_url', 'image_url': {'url': data_url}},
        ])
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
        contents: List[dict[str, Any]] = [{'type': 'text', 'text': prompt}]
        contents.extend(
            {
                'type': 'image_url',
                'image_url': {'url': f'data:image/jpeg;base64,{base64.b64encode(frame).decode("ascii")}'},
            }
            for frame in frames
        )
        text = await cls._invoke(contents)
        logger.info('gemini_video_description_completed chars=%s', len(text))
        return text
