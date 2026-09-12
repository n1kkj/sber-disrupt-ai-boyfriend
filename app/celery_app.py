from celery import Celery

from settings import config


celery_app = Celery(
    'ai_companion',
    broker=config.redis.url,
    backend=config.redis.url,
    include=['app.tasks.message_task', 'app.tasks.media_task', 'app.tasks.speech_task'],
)
celery_app.conf.update(
    task_default_queue=config.celery.default_queue,
    task_routes={
        'app.tasks.message_task.ProcessMessageTask': {'queue': 'messages'},
        'app.tasks.speech_task.ProcessSpeechTask': {'queue': 'tts'},
    },
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    task_time_limit=config.celery.task_time_limit_seconds,
    timezone='UTC',
    enable_utc=True,
)
