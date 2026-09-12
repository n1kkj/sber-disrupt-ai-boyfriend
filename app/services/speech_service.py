import asyncio
import subprocess
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
            max_retries=0,
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
        logger.error('gemini_speech_provider_error status=%s error=%s', status_code, error)
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
            if config.gemini.tts_model.casefold().startswith('gemini-'):
                response = await cls._client().audio.speech.create(
                    model=config.gemini.tts_model,
                    voice=config.gemini.tts_voice,
                    input=clean_text,
                )
            else:
                response = await cls._client().audio.speech.create(
                    model=config.gemini.tts_model,
                    voice=config.gemini.tts_voice,
                    input=clean_text,
                    response_format=config.gemini.tts_response_format or 'mp3',
                )
            content_type = str(response.headers.get('content-type', ''))
            audio = await asyncio.to_thread(cls._convert_to_telegram_ogg, response.content, content_type)
        except Exception as error:
            cls._raise_provider_error(error)
        if not audio:
            raise ValueError('Artemox не вернул аудио для TTS')
        logger.info('gemini_speech_completed bytes=%s', len(audio))
        return audio

    @classmethod
    def _convert_to_telegram_ogg(
        cls: type['GeminiSpeechService'],
        audio: bytes,
        content_type: str,
    ) -> bytes:
        if not audio:
            raise ValueError('Провайдер вернул пустое аудио')
        input_args = []
        normalized_content_type = content_type.casefold()
        if 'pcm' in normalized_content_type or not normalized_content_type:
            input_args = ['-f', 's16le', '-ar', '24000', '-ac', '1']
        command = [
            'ffmpeg',
            '-hide_banner',
            '-loglevel',
            'error',
        ] + input_args + [
            '-i',
            'pipe:0',
            '-c:a',
            'libopus',
            '-f',
            'ogg',
            'pipe:1',
        ]
        result = subprocess.run(
            command,
            input=audio,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0 or not result.stdout:
            error = result.stderr.decode('utf-8', errors='replace').strip()
            raise RuntimeError(f'Не удалось конвертировать TTS в OGG/Opus: {error}')
        return result.stdout
