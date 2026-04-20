import logging
import os
from typing import ClassVar

import redis.asyncio as redis
from redis.exceptions import ConnectionError, ResponseError, TimeoutError

from shared.event_schema import DomainEvent

logger = logging.getLogger(__name__)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")


class EventPublisher:
    """
    Публикатор событий в Redis Streams.

    Использует общий пул соединений на уровне класса — одно соединение
    на весь сервис вместо создания нового при каждом publish().

    Использование в lifespan сервиса:
        await EventPublisher.connect()
        ...
        await EventPublisher.close()
    """

    _redis: ClassVar[redis.Redis | None] = None

    @classmethod
    async def connect(cls) -> None:
        """Инициализировать общий пул соединений. Вызывать один раз при старте."""
        cls._redis = redis.from_url(REDIS_URL, decode_responses=False)
        logger.info("EventPublisher: подключение к Redis установлено")

    @classmethod
    async def close(cls) -> None:
        """Закрыть соединение при остановке сервиса."""
        if cls._redis is not None:
            await cls._redis.aclose()
            cls._redis = None
            logger.info("EventPublisher: соединение с Redis закрыто")

    async def publish(self, event: DomainEvent) -> None:
        """Опубликовать событие в Redis Stream domain-events."""
        client = self.__class__._redis
        owns_client = False

        if client is None:
            # Fallback для тестов / сервисов без lifespan-инициализации
            client = redis.from_url(REDIS_URL, decode_responses=False)
            owns_client = True

        try:
            payload = {"payload": event.model_dump_json()}
            await client.xadd("domain-events", payload)
            logger.info(f"📤 Событие опубликовано: {event.event_type} (ID: {event.event_id})")
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"❌ Не удалось подключиться к Redis: {e}")
        except ResponseError as e:
            logger.error(f"❌ Ошибка Redis при публикации: {e}")
        except Exception as e:
            logger.error(f"❌ Неизвестная ошибка при публикации события: {e}", exc_info=True)
        finally:
            if owns_client:
                await client.aclose()
