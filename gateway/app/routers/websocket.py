import asyncio
import logging
import os

from app.dependencies import verify_websocket_token
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from websockets import connect as ws_connect
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])

NOTIFICATION_SERVICE_URL = (
    os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8006")
    .replace("http://", "ws://")
    .replace("https://", "wss://")
)

HISTORY_SERVICE_URL = (
    os.getenv("HISTORY_SERVICE_URL", "http://history-service:8007")
    .replace("http://", "ws://")
    .replace("https://", "wss://")
)


@router.websocket("/notification")
async def websocket_notification_proxy(
    websocket: WebSocket, token: str = Query(..., description="JWT токен для аутентификации")
):
    """
    WebSocket прокси для получения уведомлений в реальном времени.

    **Аутентификация:** JWT токен передается в query параметре `token`.

    Gateway проверяет токен и проксирует WebSocket соединение к notification-service.

    ## Архитектура:
    ```
    Клиент (WebSocket) ←→ Gateway (WebSocket Proxy) ←→ Notification Service (WebSocket)
    ```

    ## Как работает проксирование:
    1. Gateway принимает WebSocket соединение от клиента
    2. Проверяет JWT токен и извлекает user_id
    3. Устанавливает WebSocket соединение с notification-service
    4. Создает два потока пересылки сообщений:
       - Клиент → Notification Service (если клиент отправляет ping/pong)
       - Notification Service → Клиент (уведомления)
    5. При разрыве любого соединения закрывает оба

    ## Как использовать:
    ```javascript
    const ws = new WebSocket(`ws://localhost:8000/ws/notification?token=${accessToken}`);

    ws.onmessage = (event) => {
        const notification = JSON.parse(event.data);
        console.log('📬 Новое уведомление:', notification);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
    };
    ```

    ## Безопасность:
    - Токен проверяется на gateway перед установкой соединения
    - Неправильный/истекший токен → соединение закрывается с кодом 4001
    - User ID извлекается из токена и не может быть подделан
    - Notification-service также проверяет токен для дополнительной безопасности

    ## Коды закрытия:
    - 1000: Нормальное закрытие
    - 4001: Невалидный или истекший токен
    - 1011: Ошибка проксирования (notification-service недоступен)
    """
    # Проверка токена на gateway
    user_id = verify_websocket_token(token)
    if user_id is None:
        await websocket.close(code=4001, reason="Invalid or expired token")
        logger.warning("❌ WebSocket connection rejected: invalid token")
        return

    # Принимаем WebSocket соединение от клиента
    await websocket.accept()
    logger.info(f"✅ WebSocket accepted from client (user_id={user_id})")

    # URL для подключения к notification-service
    notification_ws_url = f"{NOTIFICATION_SERVICE_URL}/ws/notification?token={token}"

    backend_ws = None
    try:
        # Устанавливаем WebSocket соединение с notification-service
        backend_ws = await ws_connect(notification_ws_url)
        logger.info(f"🔗 Connected to notification-service WebSocket for user {user_id}")

        # Создаем две задачи для двунаправленного проксирования
        async def forward_to_backend():
            """Пересылка сообщений: Клиент → Notification Service"""
            try:
                while True:
                    # Получаем сообщение от клиента
                    message = await websocket.receive_text()
                    # Отправляем в notification-service
                    await backend_ws.send(message)
            except WebSocketDisconnect:
                logger.info(f"📤 Client disconnected (user_id={user_id})")
            except ConnectionClosed:
                logger.info(f"📤 Backend closed while forwarding from client (user_id={user_id})")

        async def forward_to_client():
            """Пересылка сообщений: Notification Service → Клиент"""
            try:
                async for message in backend_ws:
                    # Получили сообщение от notification-service
                    # Отправляем клиенту
                    await websocket.send_text(message)
            except WebSocketDisconnect:
                logger.info(f"📥 Client disconnected while forwarding from backend (user_id={user_id})")
            except ConnectionClosed:
                logger.info(f"📥 Backend closed (user_id={user_id})")

        # Запускаем обе задачи параллельно
        # Когда одна завершится (соединение закрыто), отменяем другую
        _, pending = await asyncio.wait(
            [asyncio.create_task(forward_to_backend()), asyncio.create_task(forward_to_client())],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Отменяем оставшиеся задачи
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        logger.info(f"🔌 WebSocket proxy closed for user {user_id}")

    except ConnectionClosed as e:
        logger.warning(f"⚠️ Backend WebSocket closed: {e}")
        await websocket.close(code=1011, reason="Backend connection closed")

    except Exception as e:
        logger.error(f"❌ WebSocket proxy error for user {user_id}: {e}")
        await websocket.close(code=1011, reason=f"Proxy error: {str(e)}")

    finally:
        # Закрываем соединение с notification-service, если оно открыто
        if backend_ws and not backend_ws.closed:
            await backend_ws.close()
            logger.info(f"🔌 Closed backend WebSocket for user {user_id}")


@router.websocket("/history")
async def websocket_history_proxy(
    websocket: WebSocket, token: str = Query(..., description="JWT токен для аутентификации")
):
    """WebSocket прокси для получения истории действий в реальном времени."""
    user_id = verify_websocket_token(token)
    if user_id is None:
        await websocket.close(code=4001, reason="Invalid or expired token")
        logger.warning("❌ WebSocket history connection rejected: invalid token")
        return

    await websocket.accept()
    logger.info(f"✅ WebSocket history accepted from client (user_id={user_id})")

    history_ws_url = f"{HISTORY_SERVICE_URL}/ws/history?token={token}"

    backend_ws = None
    try:
        backend_ws = await ws_connect(history_ws_url)
        logger.info(f"🔗 Connected to history-service WebSocket for user {user_id}")

        async def forward_to_backend():
            try:
                while True:
                    message = await websocket.receive_text()
                    await backend_ws.send(message)
            except WebSocketDisconnect:
                pass
            except ConnectionClosed:
                pass

        async def forward_to_client():
            try:
                async for message in backend_ws:
                    await websocket.send_text(message)
            except WebSocketDisconnect:
                pass
            except ConnectionClosed:
                pass

        _, pending = await asyncio.wait(
            [asyncio.create_task(forward_to_backend()), asyncio.create_task(forward_to_client())],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        logger.info(f"🔌 WebSocket history proxy closed for user {user_id}")

    except ConnectionClosed as e:
        logger.warning(f"⚠️ History backend WebSocket closed: {e}")
        await websocket.close(code=1011, reason="Backend connection closed")

    except Exception as e:
        logger.error(f"❌ WebSocket history proxy error for user {user_id}: {e}")
        await websocket.close(code=1011, reason=f"Proxy error: {str(e)}")

    finally:
        if backend_ws and not backend_ws.closed:
            await backend_ws.close()
            logger.info(f"🔌 Closed history backend WebSocket for user {user_id}")
