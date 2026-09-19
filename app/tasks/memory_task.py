import asyncio
from typing import Any, Dict
from uuid import UUID

from celery import Task

from app.celery_app import celery_app
from app.database import async_session
from app.logging import logger
from app.services.memory_extraction_service import MemoryExtractionService
from settings import config


class ProcessMemoryTask(Task):
    name = 'app.tasks.memory_task.ProcessMemoryTask'

    def run(self: 'ProcessMemoryTask', message_id: str) -> Dict[str, Any]:
        logger.info('celery_memory_task_started message_id=%s task_id=%s retry=%s', message_id, self.request.id, self.request.retries)
        try:
            asyncio.run(self._process(message_id))
            logger.info('celery_memory_task_completed message_id=%s task_id=%s', message_id, self.request.id)
            return {'message_id': message_id, 'status': 'completed'}
        except LookupError as error:
            logger.error('celery_memory_task_permanent_failure message_id=%s error=%s', message_id, error)
            raise
        except Exception as error:
            if self.request.retries >= config.celery.max_retries:
                logger.exception('celery_memory_task_failed message_id=%s task_id=%s', message_id, self.request.id)
                raise
            countdown = min(
                config.celery.retry_backoff_seconds * (2 ** self.request.retries),
                config.celery.retry_backoff_max_seconds,
            )
            logger.warning(
                'celery_memory_task_retrying message_id=%s retry=%s countdown=%s',
                message_id,
                self.request.retries + 1,
                countdown,
            )
            raise self.retry(exc=error, countdown=countdown)

    async def _process(self: 'ProcessMemoryTask', message_id: str) -> None:
        async with async_session() as session:
            await MemoryExtractionService.process_message(session, UUID(message_id))


process_memory_task = celery_app.register_task(ProcessMemoryTask())
