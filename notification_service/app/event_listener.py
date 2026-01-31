import logging
import asyncio
import redis.asyncio as redis
from redis.exceptions import ConnectionError, TimeoutError, ResponseError
from shared.event_schema import DomainEvent
from shared.event_publisher import EventPublisher
import json
from app.database import get_db
from app.repository.notification_repository import NotificationRepository
from app.schemas import NotificationCreate

logger = logging.getLogger(__name__)


class EventListener:
    def __init__(self):
        self.redis = redis.from_url("redis://localhost:6379")
        self.publisher = EventPublisher()
    
    async def listen(self):
        """Начать прослушивание потока событий"""
        try:
            # Создаем поток, если он не существует
            try:
                await self.redis.xgroup_create("domain-events", "notification-group", id="0", mkstream=True)
                logger.info("✅ Группа потребителей 'notification-group' создана")
            except ResponseError as e:
                if "BUSYGROUP" in str(e):
                    logger.info("Группа потребителей 'notification-group' уже существует")
                else:
                    raise e
            
            # ID последнего обработанного сообщения (">" означает новые сообщения)
            last_id = ">"
            
            logger.info("👂 Начинаем прослушивание потока 'domain-events'")
            
            while True:
                try:
                    # Получаем сообщения из потока
                    messages = await self.redis.xreadgroup(
                        groupname="notification-group",
                        consumername="notification-service-consumer",
                        streams={"domain-events": last_id},
                        count=1,
                        block=1000
                    )
                    
                    if messages:
                        # messages имеет вид: [(stream_name, [(message_id, message_data), ...]), ...]
                        for stream, message_list in messages:
                            for message_id, message_data in message_list:
                                try:
                                    payload_json = message_data.get(b"payload") or message_data.get("payload")
                                    
                                    if payload_json:
                                        event_dict = json.loads(payload_json)
                                        event = DomainEvent(**event_dict)
                                        
                                        logger.info(f"📥 Получено событие: {event.event_type} (ID: {event.event_id})")
                                        
                                        # Обрабатываем событие
                                        await self.handle_event(event)
                                        
                                        # Подтверждаем обработку сообщения
                                        await self.redis.xack("domain-events", "notification-group", message_id)
                                        
                                        last_id = message_id
                                    
                                except Exception as e:
                                    logger.error(f"❌ Ошибка обработки сообщения {message_id}: {e}")
                                    
                except TimeoutError:
                    continue
                
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"❌ Не удалось подключиться к Redis: {e}")
        except Exception as e:
            logger.error(f"❌ Неизвестная ошибка при прослушивании потока: {e}")
        
    # Словарь для сопоставления типов событий с обработчиками
    _event_handlers = {
        "transaction.created": "_handle_transaction_created",
        "purpose.created": "_handle_purpose_created",
        "user.registered": "_handle_user_registered",
        "purpose.progress": "_handle_purpose_progress",
        "purpose.deleted": "_handle_purpose_deleted"
    }

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
        user_id = payload.get("user_id")
        purpose_name = payload.get("purpose_name")
        progress_percent = payload.get("progress_percent")
        threshold = payload.get("threshold")
        
        title = f"Прогресс цели: {threshold}%"
        message = f"🎯 Цель \"{purpose_name}\" достигла {progress_percent}% прогресса! Продолжайте в том же духе!"
        logger.info(f"🔔 Уведомление для пользователя {user_id}: {message}")
        
        # Сохраняем уведомление в базу данных
        async with get_db() as db:
            repo = NotificationRepository(db)
            notification_data = NotificationCreate(
                user_id=str(user_id),
                title=title,
                body=message
            )
            await repo.create_notification(notification_data)
            
        logger.info(f"✅ Уведомление сохранено в базу данных для пользователя {user_id}")
    
    async def _handle_purpose_created(self, event: DomainEvent):
        """Обработка события создания цели"""
        payload = event.payload
        user_id = payload.get("user_id")
        purpose_name = payload.get("name", "неизвестная цель")
        target_amount = payload.get("target_amount")
        
        title = "Цель создана"
        message = f"🎯 Новая цель создана: {purpose_name} ({target_amount} руб)"
        logger.info(f"🔔 Уведомление для пользователя {user_id}: {message}")
        
        # Сохраняем уведомление в базу данных
        async with get_db() as db:
            repo = NotificationRepository(db)
            notification_data = NotificationCreate(
                user_id=str(user_id),
                title=title,
                body=message
            )
            await repo.create_notification(notification_data)
            
        logger.info(f"✅ Уведомление сохранено в базу данных для пользователя {user_id}")
        
    async def _handle_purpose_deleted(self, event: DomainEvent):
        """Обработка события удаления цели"""
        payload = event.payload
        user_id = payload.get("user_id")
        purpose_name = payload.get("name", "неизвестная цель")
        target_amount = payload.get("target_amount")
        
        title = "Цель удалена"
        message = f"🗑️ Цель \"{purpose_name}\" удалена. Было запланировано: {target_amount} руб."
        logger.info(f"🔔 Уведомление для пользователя {user_id}: {message}")
        
        # Сохраняем уведомление в базу данных
        async with get_db() as db:
            repo = NotificationRepository(db)
            notification_data = NotificationCreate(
                user_id=str(user_id),
                title=title,
                body=message
            )
            await repo.create_notification(notification_data)
            
        logger.info(f"✅ Уведомление об удалении цели сохранено в базу данных для пользователя {user_id}")