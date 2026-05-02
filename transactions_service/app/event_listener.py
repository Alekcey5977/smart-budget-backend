import asyncio
import json
import logging
import os

import redis.asyncio as redis
from app.database import AsyncSessionLocal
from app.repository.sync_repository import SyncRepository
from redis.exceptions import ConnectionError, ResponseError, TimeoutError

from shared.event_schema import DomainEvent

logger = logging.getLogger(__name__)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")


class EventListener:
    async def listen(self):
        """Начать прослушивание потока событий"""
        redis_client = None

        while True:
            try:
                if redis_client is None:
                    redis_client = redis.from_url(REDIS_URL, decode_responses=False)
                    logger.info("[EventListener] Подключение к Redis установлено")

                try:
                    await redis_client.xgroup_create("domain-events", "transactions-group", id="0", mkstream=True)
                    logger.info("[EventListener] Группа 'transactions-group' создана")
                except ResponseError as e:
                    if "BUSYGROUP" in str(e):
                        logger.info("[EventListener] Группа 'transactions-group' уже существует")
                    else:
                        raise e

                logger.info("[EventListener] Начинаем прослушивание 'domain-events'")

                while True:
                    try:
                        messages = await redis_client.xreadgroup(
                            groupname="transactions-group",
                            consumername="transactions-service-consumer",
                            streams={"domain-events": ">"},
                            count=10,
                            block=5000,
                        )

                        if messages:
                            for stream, message_list in messages:
                                for message_id, message_data in message_list:
                                    try:
                                        payload_json = message_data.get(b"payload") or message_data.get("payload")

                                        if payload_json:
                                            if isinstance(payload_json, bytes):
                                                payload_json = payload_json.decode("utf-8")

                                            event_dict = json.loads(payload_json)
                                            event = DomainEvent(**event_dict)

                                            logger.info(f"[EventListener] Получено событие: {event.event_type}")

                                            await self.handle_event(event)

                                            await redis_client.xack("domain-events", "transactions-group", message_id)

                                    except Exception as e:
                                        logger.error(
                                            f"[EventListener] Ошибка обработки {message_id}: {e}", exc_info=True
                                        )

                    except TimeoutError:
                        continue
                    except (ConnectionError, Exception) as e:
                        logger.error(f"[EventListener] Ошибка соединения: {e}")
                        if redis_client:
                            await redis_client.close()
                            redis_client = None
                        await asyncio.sleep(2)
                        break

            except Exception as e:
                logger.error(f"[EventListener] Критическая ошибка: {e}", exc_info=True)
                if redis_client:
                    await redis_client.close()
                    redis_client = None
                await asyncio.sleep(5)

    _event_handlers = {
        "bank_account.added": "_handle_bank_account_added",
        "bank_account.renamed": "_handle_bank_account_renamed",
    }

    async def handle_event(self, event: DomainEvent):
        try:
            handler_name = self._event_handlers.get(event.event_type)
            if handler_name:
                handler = getattr(self, handler_name)
                await handler(event)
        except Exception as e:
            logger.error(f"[EventListener] Ошибка обработки события {event.event_type}: {e}")

    async def _handle_bank_account_renamed(self, event: DomainEvent):
        """Обновить имя счёта при переименовании"""
        payload = event.payload
        bank_account_hash = payload.get("bank_account_hash")
        new_name = payload.get("new_name")

        if not bank_account_hash or not new_name:
            logger.error(f"[EventListener] Отсутствует bank_account_hash или new_name: {payload}")
            return

        logger.info(f"[EventListener] Переименование счёта {bank_account_hash} → «{new_name}»")

        async with AsyncSessionLocal() as db:
            repo = SyncRepository(db)
            try:
                found = await repo.rename_bank_account(bank_account_hash, new_name)
                if found:
                    logger.info(f"[EventListener] Счёт {bank_account_hash} переименован")
                else:
                    logger.warning(f"[EventListener] Счёт {bank_account_hash} не найден в transactions DB")
            except Exception as e:
                logger.error(f"[EventListener] Ошибка переименования {bank_account_hash}: {e}")

    async def _handle_bank_account_added(self, event: DomainEvent):
        """Синхронизировать счёт при добавлении банковского аккаунта"""
        payload = event.payload
        bank_account_hash = payload.get("bank_account_hash")
        raw_user_id = payload.get("user_id")

        if not bank_account_hash or raw_user_id is None:
            logger.error(f"[EventListener] Отсутствует bank_account_hash или user_id: {payload}")
            return

        try:
            user_id = int(raw_user_id)
        except (TypeError, ValueError):
            logger.error(f"[EventListener] Некорректный user_id: {raw_user_id}")
            return

        logger.info(f"[EventListener] Запуск sync для {bank_account_hash}, user_id={user_id}")

        async with AsyncSessionLocal() as db:
            repo = SyncRepository(db)
            try:
                stats = await repo.sync_by_account(bank_account_hash, user_id)
                logger.info(f"[EventListener] Sync завершён: {stats}")
            except Exception as e:
                logger.error(f"[EventListener] Ошибка sync для {bank_account_hash}: {e}")
