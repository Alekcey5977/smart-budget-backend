"""
Асинхронный Redis-клиент для кэширования.

Паттерн Cache-Aside:
  1. Попытка получить из кэша -> если есть, вернуть
  2. При промахе -> запрос в БД → сохранить в кэш -> вернуть
  3. При изменении данных -> инвалидировать соответствующие ключи
"""

import json
import os
from typing import Any

import redis.asyncio as aioredis


class CacheClient:
    """Асинхронный клиент для кэширования в Redis"""

    def __init__(self, redis_url: str = "redis://redis:6379") -> None:
        self._redis: aioredis.Redis | None = None
        self._url = redis_url  # Проблема с подключением к Redis, проверьте настройки и запущенность сервиса

    async def connect(self) -> None:
        """Подключиться к Redis"""
        self._redis = aioredis.from_url(
            self._url,
            decode_responses=True,
            encoding="utf-8",
            socket_connect_timeout=10,
            socket_keepalive=True,
            retry_on_timeout=True,
            health_check_interval=30,
        )

    async def close(self) -> None:
        """Закрыть соединение"""
        if self._redis:
            await self._redis.aclose()

    @property
    def redis(self) -> aioredis.Redis:
        """Получить экземпляр Redis-клиента."""
        if self._redis is None:
            raise RuntimeError(
                "CacheClient не подключён. Сначала вызовите connect().")
        return self._redis

    async def get(self, key: str) -> Any | None:
        """Получить значение из кэша"""
        raw = await self.redis.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Сериализовать в JSON и сохранить в кэш с TTL (секунды)"""
        serialized = json.dumps(value, default=str)
        await self.redis.set(key, serialized, ex=ttl)

    async def delete(self, key: str) -> None:
        """Удалить один ключ"""
        await self.redis.delete(key)

    async def delete_pattern(self, pattern: str) -> int:
        """Удалить все ключи по шаблону (например, 'categories:*')"""
        deleted = 0
        async for key in self.redis.scan_iter(match=pattern, count=100):
            await self.redis.delete(key)
            deleted += 1
        return deleted

    async def get_raw(self, key: str) -> str | None:
        """Получить строковое значение"""
        return await self.redis.get(key)

    async def set_raw(self, key: str, value: str, ttl: int = 3600) -> None:
        """Сохранить строковое значение"""
        await self.redis.set(key, value, ex=ttl)


# Глобальный экземпляр для использования в сервисах
# Берёт REDIS_URL из окружения, fallback на дефолт
cache_client = CacheClient(redis_url=os.getenv(
    "REDIS_URL", "redis://redis:6379"))
