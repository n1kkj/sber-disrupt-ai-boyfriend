from typing import Tuple

from redis import Redis

from app.logging import logger
from settings import config


class RateLimitService:
    @classmethod
    def consume(cls: type['RateLimitService'], scope: str, identity: str) -> Tuple[bool, int]:
        key = f'rate_limit:{scope}:{identity}'
        client = Redis.from_url(config.redis.url, decode_responses=True)
        try:
            pipeline = client.pipeline(transaction=True)
            pipeline.incr(key)
            pipeline.ttl(key)
            count, ttl = pipeline.execute()
            if count == 1:
                client.expire(key, config.rate_limit.window_seconds)
                ttl = config.rate_limit.window_seconds
            allowed = int(count) <= config.rate_limit.max_messages
            retry_after = max(int(ttl), 1)
            if not allowed:
                logger.warning(
                    'rate_limit_exceeded scope=%s retry_after=%s',
                    scope,
                    retry_after,
                )
            return allowed, retry_after
        except Exception:
            logger.exception('rate_limit_check_failed scope=%s fail_open=true', scope)
            return True, 0
        finally:
            client.close()
