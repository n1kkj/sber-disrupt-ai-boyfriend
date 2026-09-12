import asyncio
from typing import Any, Dict
from uuid import UUID

from celery import Task

from app.celery_app import celery_app
from app.database import async_session
from app.logging import logger
from app.services.message_service import MessageService
from app.services.redis_task_service import RedisTaskService
from settings import config


class ProcessMessageTask(Task):
    name = 'app.tasks.message_task.ProcessMessageTask'

    def run(self: 'ProcessMessageTask', message_id: str) -> Dict[str, Any]:
        logger.info('celery_message_task_started message_id=%s task_id=%s retry=%s', message_id, self.request.id, self.request.retries)
        state = RedisTaskService.get_state(message_id)
        if state is not None and state.get('status') == 'cancelled':
            logger.info('celery_message_task_cancelled_before_start message_id=%s task_id=%s', message_id, self.request.id)
            return {'message_id': message_id, 'status': 'cancelled'}
        task_id = self.request.id or ''
        RedisTaskService.save_state(message_id, task_id, 'running')
        try:
            message, assistant, telegram_id, telegram_connected = asyncio.run(self._process_message(message_id))
            if message.status == 'cancelled':
                RedisTaskService.save_state(message_id, task_id, 'cancelled')
                logger.info('celery_message_task_cancelled message_id=%s task_id=%s', message_id, task_id)
                return {'message_id': message_id, 'status': 'cancelled'}
            if message.platform == 'telegram' and assistant is not None and telegram_id is not None:
                from app.services.telegram_service import TelegramService

                asyncio.run(
                    TelegramService.send_assistant_response(
                        telegram_id,
                        assistant.id,
                        assistant.content,
                        telegram_connected,
                        message.message_type == 'audio_request',
                    )
                )
            RedisTaskService.save_state(message_id, task_id, 'completed')
            logger.info('celery_message_task_completed message_id=%s task_id=%s', message_id, task_id)
            return {
                'message_id': str(message.id),
                'status': 'completed',
                'assistant_message_id': str(assistant.id) if assistant is not None else '',
            }
        except LookupError as error:
            RedisTaskService.save_state(message_id, task_id, 'failed', str(error))
            logger.error('celery_message_task_permanent_failure message_id=%s task_id=%s error=%s', message_id, task_id, error)
            raise
        except Exception as error:
            if self.request.retries >= config.celery.max_retries:
                RedisTaskService.save_state(message_id, task_id, 'failed', str(error))
                logger.exception('celery_message_task_failed message_id=%s task_id=%s', message_id, task_id)
                raise
            RedisTaskService.save_state(message_id, task_id, 'retrying', str(error))
            countdown = min(
                config.celery.retry_backoff_seconds * (2 ** self.request.retries),
                config.celery.retry_backoff_max_seconds,
            )
            logger.warning(
                'celery_message_task_retrying message_id=%s task_id=%s retry=%s countdown=%s',
                message_id,
                task_id,
                self.request.retries + 1,
                countdown,
            )
            raise self.retry(exc=error, countdown=countdown)

    async def _process_message(
        self: 'ProcessMessageTask',
        message_id: str,
    ) -> Any:
        async with async_session() as session:
            return await MessageService.process_message(session, UUID(message_id))


process_message_task = celery_app.register_task(ProcessMessageTask())
