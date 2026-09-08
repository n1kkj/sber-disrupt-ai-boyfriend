import json
from typing import Dict, Optional

from redis import Redis

from app.logging import logger
from settings import config


class RedisTaskService:
    @classmethod
    def save_state(
        cls: type['RedisTaskService'],
        message_id: str,
        task_id: str,
        status: str,
        error: Optional[str] = None,
    ) -> None:
        payload = {'message_id': message_id, 'task_id': task_id, 'status': status}
        if error is not None:
            payload['error'] = error[:2000]
        client = Redis.from_url(config.redis.url, decode_responses=True)
        try:
            client.setex(
                cls._key(message_id),
                config.redis.task_state_ttl_seconds,
                json.dumps(payload),
            )
            logger.debug('redis_task_state_saved message_id=%s task_id=%s status=%s', message_id, task_id, status)
        except Exception:
            logger.exception('redis_task_state_save_failed message_id=%s task_id=%s status=%s', message_id, task_id, status)
            raise
        finally:
            client.close()

    @classmethod
    def get_state(cls: type['RedisTaskService'], message_id: str) -> Optional[Dict[str, str]]:
        client = Redis.from_url(config.redis.url, decode_responses=True)
        try:
            value = client.get(cls._key(message_id))
        finally:
            client.close()
        if value is None:
            logger.debug('redis_task_state_missing message_id=%s', message_id)
            return None
        state = json.loads(value)
        logger.debug('redis_task_state_loaded message_id=%s status=%s', message_id, state.get('status'))
        return state

    @classmethod
    def get_task_id(cls: type['RedisTaskService'], message_id: str) -> Optional[str]:
        state = cls.get_state(message_id)
        return state.get('task_id') if state is not None else None

    @classmethod
    def _key(cls: type['RedisTaskService'], message_id: str) -> str:
        return f'message_task:{message_id}'
