import logging
from typing import Dict, List

from app.auth import verify_websocket_token
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/ws", tags=["websocket"])

active_connections: Dict[int, List[WebSocket]] = {}


@router.websocket("/notification")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    user_id = verify_websocket_token(token)
    if user_id is None:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    await websocket.accept()

    if user_id not in active_connections:
        active_connections[user_id] = []
    active_connections[user_id].append(websocket)

    logger.info(f"🔌 WebSocket подключён для пользователя {user_id}")

    try:
        # Удерживаем соединение открытым
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections[user_id].remove(websocket)
        if not active_connections[user_id]:
            del active_connections[user_id]
        logger.info(f"🔌 WebSocket отключён для пользователя {user_id}")
