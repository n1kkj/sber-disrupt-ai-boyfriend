import asyncio
from typing import Any, Dict
from uuid import UUID

from celery import Task

from app.celery_app import celery_app
from app.dao.message_dao import MessageDao
from app.database import async_session
from app.logging import logger
from app.services.redis_task_service import RedisTaskService
from app.services.speech_service import GeminiSpeechService
from settings import config


class ProcessSpeechTask(Task):
    name = 'app.tasks.speech_task.ProcessSpeechTask'

    def run(
        self: 'ProcessSpeechTask',
        assistant_message_id: str,
        telegram_id: int,
        telegram_connected: bool,
    ) -> Dict[str, Any]:
        logger.info(
            'celery_speech_task_started assistant_message_id=%s telegram_suffix=%s task_id=%s',
            assistant_message_id,
            str(telegram_id)[-4:],
            self.request.id,
        )
        task_id = self.request.id or ''
        RedisTaskService.save_state(assistant_message_id, task_id, 'running')
        try:
            audio = asyncio.run(self._synthesize(assistant_message_id))
            logger.info(
                'celery_speech_audio_ready assistant_message_id=%s bytes=%s',
                assistant_message_id,
                len(audio),
            )
            from app.services.telegram_service import TelegramService

            asyncio.run(TelegramService.send_voice(telegram_id, audio, telegram_connected))
            RedisTaskService.save_state(assistant_message_id, task_id, 'completed')
            logger.info('celery_speech_task_completed assistant_message_id=%s', assistant_message_id)
            return {'assistant_message_id': assistant_message_id, 'status': 'completed'}
        except Exception as error:
            if self.request.retries >= config.celery.max_retries:
                RedisTaskService.save_state(assistant_message_id, task_id, 'failed', str(error))
                logger.exception('celery_speech_task_failed assistant_message_id=%s', assistant_message_id)
                raise
            countdown = min(
                config.celery.retry_backoff_seconds * (2 ** self.request.retries),
                config.celery.retry_backoff_max_seconds,
            )
            RedisTaskService.save_state(assistant_message_id, task_id, 'retrying', str(error))
            logger.warning('celery_speech_task_retrying assistant_message_id=%s countdown=%s', assistant_message_id, countdown)
            raise self.retry(exc=error, countdown=countdown)

    async def _synthesize(self: 'ProcessSpeechTask', assistant_message_id: str) -> bytes:
        async with async_session() as session:
            message = await MessageDao.get_by_id(session, UUID(assistant_message_id))
            if message is None or message.role != 'assistant':
                raise LookupError('Assistant message not found')
            return await GeminiSpeechService.synthesize(message.content)


process_speech_task = celery_app.register_task(ProcessSpeechTask())
