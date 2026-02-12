import logging
import asyncio
import os
import redis.asyncio as redis
import json
from redis.exceptions import ConnectionError, TimeoutError, ResponseError
from shared.event_schema import DomainEvent
from shared.event_publisher import EventPublisher
from app.database import get_db_session
from app.repository.notification_repository import NotificationRepository
from app.schemas import NotificationCreate, NotificationResponse
from app.routers.websocket import active_connections


logger = logging.getLogger(__name__)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

class EventListener:
    def __init__(self):
        self.publisher = EventPublisher()

    async def listen(self):
        """Начать прослушивание потока событий"""
        redis_client = None

        while True:
            try:
                # Создаем новое соединение с Redis
                if redis_client is None:
                    redis_client = redis.from_url(REDIS_URL, decode_responses=False)
                    logger.info("🔌 Подключение к Redis установлено")

                # Создаем поток, если он не существует
                try:
                    await redis_client.xgroup_create("domain-events", "notification-group", id="0", mkstream=True)
                    logger.info("✅ Группа потребителей 'notification-group' создана")
                except ResponseError as e:
                    if "BUSYGROUP" in str(e):
                        logger.info("ℹ️ Группа потребителей 'notification-group' уже существует")
                    else:
                        raise e

                logger.info("👂 Начинаем прослушивание потока 'domain-events'")

                # Основной цикл обработки событий
                while True:
                    try:
                        # Получаем сообщения из потока (всегда используем ">", чтобы читать только новые)
                        messages = await redis_client.xreadgroup(
                            groupname="notification-group",
                            consumername="notification-service-consumer",
                            streams={"domain-events": ">"},
                            count=10,
                            block=5000
                        )

                        if messages:
                            # messages имеет вид: [(stream_name, [(message_id, message_data), ...]), ...]
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

                                            # Обрабатываем событие
                                            await self.handle_event(event)

                                            # Подтверждаем обработку сообщения
                                            await redis_client.xack("domain-events", "notification-group", message_id)
                                            logger.info(f"✅ Событие {event.event_type} обработано успешно")

                                    except Exception as e:
                                        logger.error(f"❌ Ошибка обработки сообщения {message_id}: {e}", exc_info=True)
                                        # Не ACK'аем сообщение при ошибке, чтобы попробовать позже

                    except TimeoutError:
                        # Таймаут - это нормально, продолжаем слушать
                        continue
                    except (ConnectionError, Exception) as e:
                        logger.error(f"❌ Ошибка соединения с Redis: {e}")
                        # Закрываем соединение и пересоздадим его
                        if redis_client:
                            await redis_client.close()
                            redis_client = None
                        await asyncio.sleep(2)  # Ждем перед переподключением
                        break  # Выходим из внутреннего цикла, чтобы переподключиться

            except Exception as e:
                logger.error(f"❌ Критическая ошибка Event Listener: {e}", exc_info=True)
                if redis_client:
                    await redis_client.close()
                    redis_client = None
                await asyncio.sleep(5)  # Ждем перед повтором
        
    # Словарь для сопоставления типов событий с обработчиками
    _event_handlers = {
        "purpose.created": "_handle_purpose_created",
        "purpose.progress": "_handle_purpose_progress",
        "purpose.deleted": "_handle_purpose_deleted",
        "user.registered": "_handle_user_registered",
        "user.updated": "_handle_user_updated",
        "bank_account.added": "_handle_bank_account_added",
        "bank_account.deleted": "_handle_bank_account_deleted",
        "user.avatar.updated": "_handle_user_avatar_updated",
    }
    
    async def _send_notification_websocket(self, user_id: int, notification_data: dict):
        """Отправка уведомления по WebSocket, если есть подключения"""
        if user_id in active_connections:
            message = json.dumps(notification_data)
            disconnected = []
            for ws in active_connections[user_id]:
                try:
                    await ws.send_text(message)
                except Exception as e:
                    logger.warning(
                        f"Ошибка отправки WebSocket пользователю {user_id}: {e}")
                    disconnected.append(ws)

            # Удаляем разорванные соединения
            for ws in disconnected:
                active_connections[user_id].remove(ws)
            if not active_connections[user_id]:
                del active_connections[user_id]


    async def _create_and_broadcast_notification(
        self,
        user_id: int,
        title: str,
        body: str
    ):
        """Создаёт уведомление в БД и рассылает по WebSocket"""
        
        # Сохраняем в БД
        async with get_db_session() as db:
            repo = NotificationRepository(db)
            notification_data = NotificationCreate(
                user_id=user_id,
                title=title,
                body=body
            )
            saved = await repo.create_notification(notification_data)

        # Формируем payload
        ws_payload = self.build_notification_payload(saved, is_read=False)

        # Рассылаем по WebSocket
        await self._send_notification_websocket(user_id, ws_payload)

        logger.info(f"✅ Уведомление сохранено и отправлено пользователю {user_id}")


    def build_notification_payload(self, saved, is_read: bool = False) -> dict:
        """Создание объекта уведомления"""
        return {
            "id": str(saved.id),
            "user_id": saved.user_id,
            "title": saved.title,
            "body": saved.body,
            "created_at": saved.created_at.isoformat(),
            "is_read": is_read,
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
    
    async def _handle_purpose_progress(self, event: DomainEvent):
        """Обработка события прогресса цели"""
        payload = event.payload
        user_id = self._extract_user_id(payload)
        if user_id is None:
            return
        
        purpose_name = payload.get("purpose_name")
        progress_percent = payload.get("progress_percent")
        threshold = payload.get("threshold")
        
        title = f"Прогресс цели: {threshold}%"
        message = f"🎯 Цель \"{purpose_name}\" достигла {progress_percent}% прогресса! Продолжайте в том же духе!"
        logger.info(f"🔔 Уведомление для пользователя {user_id}: {message}")
        
        # Сохраняем уведомление в базу данных
        await self._create_and_broadcast_notification(user_id, title, message)
    
    async def _handle_purpose_created(self, event: DomainEvent):
        """Обработка события создания цели"""
        payload = event.payload
        user_id = self._extract_user_id(payload)
        if user_id is None:
            return
        
        purpose_name = payload.get("name", "неизвестная цель")
        target_amount = payload.get("target_amount")
        
        title = "Цель создана"
        message = f"🎯 Новая цель создана: {purpose_name} ({target_amount} руб)"
        logger.info(f"🔔 Уведомление для пользователя {user_id}: {message}")
        
        # Сохраняем уведомление в базу данных
        await self._create_and_broadcast_notification(user_id, title, message)
        
    async def _handle_purpose_deleted(self, event: DomainEvent):
        """Обработка события удаления цели"""
        payload = event.payload
        user_id = self._extract_user_id(payload)
        if user_id is None:
            return
        
        purpose_name = payload.get("name", "неизвестная цель")
        target_amount = payload.get("target_amount")
        
        title = "Цель удалена"
        message = f"🗑️ Цель \"{purpose_name}\" удалена. Было запланировано: {target_amount} руб."
        logger.info(f"🔔 Уведомление для пользователя {user_id}: {message}")
        
        # Сохраняем уведомление в базу данных
        await self._create_and_broadcast_notification(user_id, title, message)

    async def _handle_user_registered(self, event: DomainEvent):
        """Обработка события регистрации пользователя"""
        payload = event.payload
        user_id = self._extract_user_id(payload)
        if user_id is None:
            return
        
        first_name = payload.get("first_name", "Пользователь")
        
        title = "Добро пожаловать!"
        message = f"🎉 Добро пожаловать в Smart Budget, {first_name}!"
        logger.info(f"🔔 Уведомление для пользователя {user_id}: {message}")
        
        # Сохраняем уведомление в базу данных
        await self._create_and_broadcast_notification(user_id, title, message)

    async def _handle_user_updated(self, event: DomainEvent):
        """Обработка события обновления данных пользователя"""
        payload = event.payload
        user_id = self._extract_user_id(payload)
        if user_id is None:
            return
        
        first_name = payload.get("first_name", "Пользователь")
        last_name = payload.get("last_name", "")
        
        title = "Данные обновлены"
        message = f"✅ Ваши данные успешно обновлены, {first_name} {last_name}"
        logger.info(f"🔔 Уведомление для пользователя {user_id}: {message}")
        
        # Сохраняем уведомление в базу данных
        await self._create_and_broadcast_notification(user_id, title, message)
    
    async def _handle_bank_account_added(self, event: DomainEvent):
        """Обработка события добавления банковского счёта"""
        payload = event.payload
        user_id = self._extract_user_id(payload)
        if user_id is None:
            return
        
        bank_name = payload.get("bank_name", "неизвестный банк")
        
        title = "Счёт добавлен"
        message = f"💳 Новый счёт добавлен из банка {bank_name}"
        logger.info(f"🔔 Уведомление для пользователя {user_id}: {message}")
        
        # Сохраняем уведомление в базу данных
        await self._create_and_broadcast_notification(user_id, title, message)
        
    async def _handle_bank_account_deleted(self, event: DomainEvent):
        """Обработка события удаления банковского счёта"""
        payload = event.payload
        user_id = self._extract_user_id(payload)
        if user_id is None:
            return
        
        bank_name = payload.get("bank_name", "неизвестный банк")
        
        title = "Счёт удалён"
        message = f"🗑️ Счёт из банка {bank_name} был удалён"
        logger.info(f"🔔 Уведомление для пользователя {user_id}: {message}")
        
        # Сохраняем уведомление в базу данных
        await self._create_and_broadcast_notification(user_id, title, message)
        
    async def _handle_user_avatar_updated(self, event: DomainEvent):
        """Обработка события обновления аватара пользователя"""
        payload = event.payload
        user_id = self._extract_user_id(payload)
        if user_id is None:
            return
        
        title = "Аватар обновлён"
        message = f"✅ Вы успешно обновили свой аватар"
        logger.info(f"🔔 Уведомление для пользователя {user_id}: {message}")
        
        # Сохраняем уведомление в базу данных
        await self._create_and_broadcast_notification(user_id, title, message)