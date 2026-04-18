import logging
import os

import redis.asyncio as redis
from redis.exceptions import ConnectionError, ResponseError, TimeoutError

from shared.event_schema import DomainEvent

logger = logging.getLogger(__name__)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")


class EventPublisher:
    def __init__(self):
        self.redis_url = REDIS_URL
        self.redis = None

    async def __aenter__(self):
        """Асинхронный контекстный менеджер - вход"""
        self.redis = redis.from_url(self.redis_url, decode_responses=False)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер - выход"""
        if self.redis:
            await self.redis.close()

    async def publish(self, event: DomainEvent):
        """Публикация события в Redis Stream"""
        redis_client = None
        try:
            redis_client = redis.from_url(
                self.redis_url, decode_responses=False)
            payload = {"payload": event.model_dump_json()}
            await redis_client.xadd("domain-events", payload)
            logger.info(
                f"📤 Событие опубликовано: {event.event_type} (ID: {event.event_id})")
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"❌ Не удалось подключиться к Redis: {e}")
        except ResponseError as e:
            logger.error(f"❌ Ошибка Redis при публикации: {e}")
        except Exception as e:
            logger.error(
                f"❌ Неизвестная ошибка при публикации события: {e}", exc_info=True)
        finally:
            if redis_client:
                await redis_client.close()
