import asyncio
from typing import Any, Dict
from uuid import UUID

from celery import Task

from app.celery_app import celery_app
from app.database import async_session
from app.services.message_service import MessageService
from app.services.redis_task_service import RedisTaskService
from settings import config


class ProcessMessageTask(Task):
    name = 'app.tasks.message_task.ProcessMessageTask'

    def run(self: 'ProcessMessageTask', message_id: str) -> Dict[str, Any]:
        state = RedisTaskService.get_state(message_id)
        if state is not None and state.get('status') == 'cancelled':
            return {'message_id': message_id, 'status': 'cancelled'}
        task_id = self.request.id or ''
        RedisTaskService.save_state(message_id, task_id, 'running')
        try:
            message, assistant, telegram_id = asyncio.run(self._process_message(message_id))
            if message.status == 'cancelled':
                RedisTaskService.save_state(message_id, task_id, 'cancelled')
                return {'message_id': message_id, 'status': 'cancelled'}
            if assistant is not None and telegram_id is not None:
                from app.services.telegram_service import TelegramService

                asyncio.run(TelegramService.send_message(telegram_id, assistant.content, TelegramService._connect_keyboard()))
            RedisTaskService.save_state(message_id, task_id, 'completed')
            return {
                'message_id': str(message.id),
                'status': 'completed',
                'assistant_message_id': str(assistant.id) if assistant is not None else '',
            }
        except LookupError as error:
            RedisTaskService.save_state(message_id, task_id, 'failed', str(error))
            raise
        except Exception as error:
            if self.request.retries >= config.celery.max_retries:
                RedisTaskService.save_state(message_id, task_id, 'failed', str(error))
                raise
            RedisTaskService.save_state(message_id, task_id, 'retrying', str(error))
            countdown = min(
                config.celery.retry_backoff_seconds * (2 ** self.request.retries),
                config.celery.retry_backoff_max_seconds,
            )
            raise self.retry(exc=error, countdown=countdown)

    async def _process_message(
        self: 'ProcessMessageTask',
        message_id: str,
    ) -> Any:
        async with async_session() as session:
            return await MessageService.process_message(session, UUID(message_id))


process_message_task = celery_app.register_task(ProcessMessageTask())
