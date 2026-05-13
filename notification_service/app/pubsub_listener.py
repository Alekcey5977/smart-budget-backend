import asyncio
import logging
import os

import redis.asyncio as redis
from app.routers.websocket import active_connections

logger = logging.getLogger(__name__)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")


async def start_pubsub_listener():
    """Слушает Redis Pub/Sub и пушит уведомления в локальные WS-соединения воркера."""
    while True:
        redis_client = None
        try:
            redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            pubsub = redis_client.pubsub()
            await pubsub.psubscribe("ws:notification:*")
            logger.info("PubSub listener подписан на ws:notification:*")

            async for message in pubsub.listen():
                if message["type"] != "pmessage":
                    continue
                try:
                    user_id = int(message["channel"].split(":")[-1])
                    data = message["data"]

                    if user_id not in active_connections:
                        continue

                    disconnected = []
                    for ws in active_connections[user_id]:
                        try:
                            await ws.send_text(data)
                        except Exception:
                            disconnected.append(ws)

                    for ws in disconnected:
                        active_connections[user_id].remove(ws)
                    if not active_connections[user_id]:
                        del active_connections[user_id]

                except Exception as e:
                    logger.error(f"Ошибка обработки PubSub сообщения: {e}")

        except Exception as e:
            logger.error(f"PubSub listener упал: {e}")
            await asyncio.sleep(2)
        finally:
            if redis_client:
                await redis_client.aclose()
