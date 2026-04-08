"""
Инициализация кэширования для images-service.
"""

import os

from shared.cache import CacheClient

cache_client = CacheClient(redis_url=os.getenv(
    "REDIS_URL", "redis://redis:6379"))

# TTL (в секундах)
DEFAULT_AVATARS_TTL = 3600    # 1 час
CATEGORIES_MAP_TTL = 3600     # 1 час
MERCHANTS_MAP_TTL = 3600      # 1 час

# Ключи кэша
DEFAULT_AVATARS_KEY = "images:default_avatars"
CATEGORIES_MAP_KEY = "images:mapping:categories"
MERCHANTS_MAP_KEY = "images:mapping:merchants"
