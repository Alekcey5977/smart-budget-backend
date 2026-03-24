import asyncio
import json
import logging
import os

import redis.asyncio as redis
from app.database import get_db_session
from app.repository.history_repository import HistoryRepository
from app.routers.websocket import active_connections
from app.schemas import HistoryEntryCreate
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
                    logger.info("🔌 Подключение к Redis установлено")

                try:
                    await redis_client.xgroup_create("domain-events", "history-group", id="0", mkstream=True)
                    logger.info("✅ Группа потребителей 'history-group' создана")
                except ResponseError as e:
                    if "BUSYGROUP" in str(e):
                        logger.info("ℹ️ Группа потребителей 'history-group' уже существует")
                    else:
                        raise e

                logger.info("👂 Начинаем прослушивание потока 'domain-events'")

                while True:
                    try:
                        messages = await redis_client.xreadgroup(
                            groupname="history-group",
                            consumername="history-service-consumer",
                            streams={"domain-events": ">"},
                            count=10,
                            block=5000
                        )

                        if messages:
                            for stream, message_list in messages:
                                for message_id, message_data in message_list:
                                    try:
                                        payload_json = message_data.get(b"payload") or message_data.get("payload")

                                        if payload_json:
                                            if isinstance(payload_json, bytes):
                                                payload_json = payload_json.decode('utf-8')

                                            event_dict = json.loads(payload_json)
                                            event = DomainEvent(**event_dict)

                                            logger.info(f"📥 Получено событие: {event.event_type} (ID: {event.event_id})")

                                            await self.handle_event(event)

                                            await redis_client.xack("domain-events", "history-group", message_id)
                                            logger.info(f"✅ Событие {event.event_type} обработано успешно")

                                    except Exception as e:
                                        logger.error(f"❌ Ошибка обработки сообщения {message_id}: {e}", exc_info=True)

                    except TimeoutError:
                        continue
                    except (ConnectionError, Exception) as e:
                        logger.error(f"❌ Ошибка соединения с Redis: {e}")
                        if redis_client:
                            await redis_client.close()
                            redis_client = None
                        await asyncio.sleep(2)
                        break

            except Exception as e:
                logger.error(f"❌ Критическая ошибка Event Listener: {e}", exc_info=True)
                if redis_client:
                    await redis_client.close()
                    redis_client = None
                await asyncio.sleep(5)

    _event_handlers = {
        "user.updated": "_handle_user_updated",
        "user.avatar.updated": "_handle_user_avatar_updated",
        "purpose.created": "_handle_purpose_created",
        "purpose.deleted": "_handle_purpose_deleted",
        "purpose.updated": "_handle_purpose_updated",
        "bank_account.added": "_handle_bank_account_added",
        "bank_account.deleted": "_handle_bank_account_deleted",
        "transaction.category.updated": "_handle_transaction_category_updated",
    }

    async def _send_history_websocket(self, user_id: int, entry_data: dict):
        """Отправка записи истории по WebSocket, если есть подключения"""
        if user_id in active_connections:
            message = json.dumps(entry_data)
            disconnected = []
            for ws in active_connections[user_id]:
                try:
                    await ws.send_text(message)
                except Exception as e:
                    logger.warning(f"Ошибка отправки WebSocket пользователю {user_id}: {e}")
                    disconnected.append(ws)

            for ws in disconnected:
                active_connections[user_id].remove(ws)
            if not active_connections[user_id]:
                del active_connections[user_id]

    async def _create_and_broadcast_entry(self, user_id: int, title: str, body: str):
        """Создаёт запись истории в БД и рассылает по WebSocket"""
        async with get_db_session() as db:
            repo = HistoryRepository(db)
            entry_data = HistoryEntryCreate(
                user_id=user_id,
                title=title,
                body=body
            )
            saved = await repo.create_entry(entry_data)

        ws_payload = self.build_entry_payload(saved)

        await self._send_history_websocket(user_id, ws_payload)

        logger.info(f"✅ Запись истории сохранена и отправлена пользователю {user_id}")

    def build_entry_payload(self, saved) -> dict:
        """Создание объекта записи истории"""
        return {
            "id": str(saved.id),
            "user_id": saved.user_id,
            "title": saved.title,
            "body": saved.body,
            "created_at": saved.created_at.isoformat(),
        }

    def _extract_user_id(self, payload: dict) -> int | None:
        """Извлекает и валидирует user_id из payload события."""
        raw_user_id = payload.get("user_id")
        if raw_user_id is None:
            logger.error("Отсутствует user_id в событии")
            return None

        try:
            return int(raw_user_id)
        except (TypeError, ValueError):
            logger.error(f"Некорректный user_id в событии: {raw_user_id}")
            return None

    async def handle_event(self, event: DomainEvent):
        """Обработка конкретного события"""
        try:
            handler_name = self._event_handlers.get(event.event_type)
            if handler_name:
                handler = getattr(self, handler_name)
                await handler(event)
            else:
                logger.warning(f"⚠️ Неизвестный тип события: {event.event_type}")

        except Exception as e:
            logger.error(f"❌ Ошибка при обработке события {event.event_type}: {e}")

    async def _handle_user_updated(self, event: DomainEvent):
        """Обработка события обновления профиля пользователя"""
        payload = event.payload
        user_id = self._extract_user_id(payload)
        if user_id is None:
            return

        title = "Профиль обновлён"
        body = "Вы обновили данные профиля"
        logger.info(f"📝 История для пользователя {user_id}: {title}")

        await self._create_and_broadcast_entry(user_id, title, body)

    async def _handle_user_avatar_updated(self, event: DomainEvent):
        """Обработка события обновления аватара"""
        payload = event.payload
        user_id = self._extract_user_id(payload)
        if user_id is None:
            return

        title = "Аватар обновлён"
        body = "Вы успешно обновили свой аватар"
        logger.info(f"📝 История для пользователя {user_id}: {title}")

        await self._create_and_broadcast_entry(user_id, title, body)

    async def _handle_purpose_created(self, event: DomainEvent):
        """Обработка события создания цели"""
        payload = event.payload
        user_id = self._extract_user_id(payload)
        if user_id is None:
            return

        purpose_name = payload.get("name", "неизвестная цель")
        target_amount = payload.get("target_amount")

        title = "Цель создана"
        body = f"Цель «{purpose_name}» на сумму {target_amount} руб. создана"
        logger.info(f"📝 История для пользователя {user_id}: {title}")

        await self._create_and_broadcast_entry(user_id, title, body)

    async def _handle_purpose_deleted(self, event: DomainEvent):
        """Обработка события удаления цели"""
        payload = event.payload
        user_id = self._extract_user_id(payload)
        if user_id is None:
            return

        purpose_name = payload.get("name", "неизвестная цель")
        target_amount = payload.get("target_amount")

        title = "Цель удалена"
        body = f"Цель «{purpose_name}» на сумму {target_amount} руб. удалена"
        logger.info(f"📝 История для пользователя {user_id}: {title}")

        await self._create_and_broadcast_entry(user_id, title, body)

    async def _handle_purpose_updated(self, event: DomainEvent):
        """Обработка события изменения цели"""
        payload = event.payload
        user_id = self._extract_user_id(payload)
        if user_id is None:
            return

        purpose_name = payload.get("name", "неизвестная цель")

        title = "Цель изменена"
        body = f"Цель «{purpose_name}» была изменена"
        logger.info(f"📝 История для пользователя {user_id}: {title}")

        await self._create_and_broadcast_entry(user_id, title, body)

    async def _handle_bank_account_added(self, event: DomainEvent):
        """Обработка события добавления банковского счёта"""
        payload = event.payload
        user_id = self._extract_user_id(payload)
        if user_id is None:
            return

        bank_name = payload.get("bank_name", "неизвестный банк")

        title = "Счёт добавлен"
        body = f"Банковский счёт {bank_name} добавлен"
        logger.info(f"📝 История для пользователя {user_id}: {title}")

        await self._create_and_broadcast_entry(user_id, title, body)

    async def _handle_transaction_category_updated(self, event: DomainEvent):
        """Обработка события изменения категории транзакции"""
        payload = event.payload
        user_id = self._extract_user_id(payload)
        if user_id is None:
            return

        old_category = payload.get("old_category_name", "старая категория")
        new_category = payload.get("new_category_name", "новая категория")

        title = "Категория транзакции изменена"
        body = f"Категория изменена: «{old_category}» → «{new_category}»"
        logger.info(f"📝 История для пользователя {user_id}: {title}")

        await self._create_and_broadcast_entry(user_id, title, body)

    async def _handle_bank_account_deleted(self, event: DomainEvent):
        """Обработка события удаления банковского счёта"""
        payload = event.payload
        user_id = self._extract_user_id(payload)
        if user_id is None:
            return

        bank_name = payload.get("bank_name", "неизвестный банк")

        title = "Счёт удалён"
        body = f"Банковский счёт {bank_name} удалён"
        logger.info(f"📝 История для пользователя {user_id}: {title}")

        await self._create_and_broadcast_entry(user_id, title, body)
