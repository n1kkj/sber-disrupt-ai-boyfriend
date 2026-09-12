from typing import NoReturn

from openai import AsyncOpenAI

from app.clients.http_client import HttpClientFactory
from app.logging import logger
from settings import config


class GeminiSpeechService:
    @classmethod
    def _client(cls: type['GeminiSpeechService']) -> AsyncOpenAI:
        if not config.gemini.api_key:
            raise ValueError('Не задан GEMINI_API_KEY для синтеза речи.')
        return AsyncOpenAI(
            api_key=config.gemini.api_key,
            base_url=config.gemini.base_url,
            http_client=HttpClientFactory.get_httpx_async_proxy_client('gemini'),
        )

    @classmethod
    def _raise_provider_error(cls: type['GeminiSpeechService'], error: Exception) -> NoReturn:
        status_code = getattr(error, 'status_code', None)
        response = getattr(error, 'response', None)
        status_code = status_code or getattr(response, 'status_code', None)
        error_text = str(error).casefold()
        if status_code in {400, 401, 403} or 'api key' in error_text or 'unauthorized' in error_text:
            raise ValueError(
                'Artemox отклонил TTS-запрос. Проверьте GEMINI_API_KEY, GEMINI_BASE_URL, '
                'GEMINI_TTS_MODEL и GEMINI_TTS_VOICE.'
            ) from error
        raise error

    @classmethod
    async def synthesize(cls: type['GeminiSpeechService'], text: str) -> bytes:
        clean_text = text.strip()
        if not clean_text:
            raise ValueError('Нельзя синтезировать пустой текст')
        logger.info(
            'gemini_speech_started chars=%s model=%s voice=%s',
            len(clean_text),
            config.gemini.tts_model,
            config.gemini.tts_voice,
        )
        try:
            response = await cls._client().audio.speech.create(
                model=config.gemini.tts_model,
                voice=config.gemini.tts_voice,
                input=clean_text,
                response_format=config.gemini.tts_response_format,
            )
            audio = response.content
        except Exception as error:
            cls._raise_provider_error(error)
        if not audio:
            raise ValueError('Artemox не вернул аудио для TTS')
        logger.info('gemini_speech_completed bytes=%s', len(audio))
        return audio
