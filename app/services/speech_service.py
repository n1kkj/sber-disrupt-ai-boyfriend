import asyncio
import base64
import subprocess
from typing import NoReturn

from google import genai
from google.genai import types

from app.logging import logger
from settings import config


class GeminiSpeechService:
    @classmethod
    def _raise_provider_error(cls: type['GeminiSpeechService'], error: Exception) -> NoReturn:
        status_code = getattr(error, 'status_code', None) or getattr(error, 'code', None)
        error_text = str(error).casefold()
        logger.error('gemini_speech_provider_error status=%s error=%s', status_code, error)
        if status_code in {400, 401, 403} or 'api key' in error_text or 'unauthorized' in error_text:
            raise ValueError(
                'Artemox отклонил Gemini TTS-запрос. Проверьте GEMINI_API_KEY, '
                'GEMINI_NATIVE_BASE_URL, GEMINI_TTS_MODEL и GEMINI_TTS_VOICE.'
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
            pcm_audio = await asyncio.to_thread(cls._generate_pcm, clean_text)
            audio = await asyncio.to_thread(cls._convert_to_telegram_ogg, pcm_audio)
        except Exception as error:
            cls._raise_provider_error(error)
        if not audio:
            raise ValueError('Artemox не вернул аудио для TTS')
        logger.info('gemini_speech_completed bytes=%s', len(audio))
        return audio

    @classmethod
    def _generate_pcm(cls: type['GeminiSpeechService'], text: str) -> bytes:
        if not config.gemini.api_key:
            raise ValueError('Не задан GEMINI_API_KEY для синтеза речи.')
        client = genai.Client(
            api_key=config.gemini.api_key,
            http_options=types.HttpOptions(base_url=cls._native_base_url()),
        )
        response = client.models.generate_content(
            model=config.gemini.tts_model,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=['AUDIO'],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=config.gemini.tts_voice,
                        )
                    )
                ),
            ),
        )
        for candidate in response.candidates or []:
            content = candidate.content
            if content is None:
                continue
            for part in content.parts or []:
                inline_data = part.inline_data
                if inline_data is None or inline_data.data is None:
                    continue
                if isinstance(inline_data.data, bytes):
                    return inline_data.data
                return base64.b64decode(inline_data.data)
        raise ValueError('Gemini не вернул inline audio data')

    @classmethod
    def _native_base_url(cls: type['GeminiSpeechService']) -> str:
        native_base_url = config.gemini.native_base_url
        if native_base_url:
            return native_base_url.rstrip('/')
        return config.gemini.base_url.removesuffix('/v1')

    @classmethod
    def _convert_to_telegram_ogg(
        cls: type['GeminiSpeechService'],
        pcm_audio: bytes,
    ) -> bytes:
        if not pcm_audio:
            raise ValueError('Gemini вернул пустое аудио')
        result = subprocess.run(
            [
                'ffmpeg',
                '-hide_banner',
                '-loglevel',
                'error',
                '-f',
                's16le',
                '-ar',
                '24000',
                '-ac',
                '1',
                '-i',
                'pipe:0',
                '-c:a',
                'libopus',
                '-f',
                'ogg',
                'pipe:1',
            ],
            input=pcm_audio,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0 or not result.stdout:
            error = result.stderr.decode('utf-8', errors='replace').strip()
            raise RuntimeError(f'Не удалось конвертировать TTS в OGG/Opus: {error}')
        return result.stdout
