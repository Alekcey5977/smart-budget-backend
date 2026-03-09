import logging
import os
import redis.asyncio as redis
from redis.exceptions import ConnectionError, TimeoutError, ResponseError
from shared.event_schema import DomainEvent

logger = logging.getLogger(__name__)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

class EventPublisher:
    def __init__(self):
        self.redis = redis.from_url(REDIS_URL)

    async def publish(self, event: DomainEvent):
        try:
            payload = {"payload": event.model_dump_json()}
            await self.redis.xadd("domain-events", payload)
            logger.info(
                f"📤 Событие опубликовано: {event.event_type} (ID: {event.event_id})")
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"❌ Не удалось подключиться к Redis: {e}")
        except ResponseError as e:
            logger.error(f"❌ Ошибка Redis при публикации: {e}")
        except Exception as e:
            logger.error(f"❌ Неизвестная ошибка при публикации события: {e}")
