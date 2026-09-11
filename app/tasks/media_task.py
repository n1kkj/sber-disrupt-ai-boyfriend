import asyncio
from typing import Any, Dict
from uuid import UUID

from celery import Task

from app.celery_app import celery_app
from app.database import async_session
from app.logging import logger
from app.services.media_service import MediaService
from app.services.redis_task_service import RedisTaskService
from settings import config


class ProcessMediaTask(Task):
    media_type: str = ''

    def run(self: 'ProcessMediaTask', asset_id: str) -> Dict[str, Any]:
        logger.info('celery_media_task_started asset_id=%s type=%s task_id=%s', asset_id, self.media_type, self.request.id)
        try:
            asyncio.run(self._process(asset_id))
            RedisTaskService.save_state(asset_id, self.request.id or '', 'completed')
            logger.info('celery_media_task_completed asset_id=%s type=%s', asset_id, self.media_type)
            return {'asset_id': asset_id, 'status': 'completed'}
        except Exception as error:
            if isinstance(error, ValueError) or self.request.retries >= config.celery.max_retries:
                RedisTaskService.save_state(asset_id, self.request.id or '', 'failed', str(error))
                logger.exception('celery_media_task_failed asset_id=%s type=%s', asset_id, self.media_type)
                raise
            countdown = min(
                config.celery.retry_backoff_seconds * (2 ** self.request.retries),
                config.celery.retry_backoff_max_seconds,
            )
            RedisTaskService.save_state(asset_id, self.request.id or '', 'retrying', str(error))
            logger.warning('celery_media_task_retrying asset_id=%s type=%s countdown=%s', asset_id, self.media_type, countdown)
            raise self.retry(exc=error, countdown=countdown)

    async def _process(self: 'ProcessMediaTask', asset_id: str) -> None:
        async with async_session() as session:
            processor = {
                'audio': MediaService.process_audio,
                'image': MediaService.process_image,
                'video': MediaService.process_video,
            }[self.media_type]
            await processor(session, UUID(asset_id))


class ProcessAudioTask(ProcessMediaTask):
    name = 'app.tasks.media_task.ProcessAudioTask'
    media_type = 'audio'


class ProcessImageTask(ProcessMediaTask):
    name = 'app.tasks.media_task.ProcessImageTask'
    media_type = 'image'


class ProcessVideoTask(ProcessMediaTask):
    name = 'app.tasks.media_task.ProcessVideoTask'
    media_type = 'video'


process_audio_task = celery_app.register_task(ProcessAudioTask())
process_image_task = celery_app.register_task(ProcessImageTask())
process_video_task = celery_app.register_task(ProcessVideoTask())
