from fastapi import FastAPI # фреймворк для асинхронных REST API.
from fastapi.middleware.cors import CORSMiddleware # middleware для разрешения междоменных запросов (CORS)
import uvicorn
import os
import sys

# Добавляем путь к app в Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Абсолютные импорты
from app.routers import auth

app = FastAPI(title="Gateway Service", description="Точка входа", version="1.0.0")

"""
CORS (Cross-Origin Resource Sharing) middleware
Разрешает браузеру делать запросы с одного домена (frontend) 
на другой домен (наш gateway)
"""
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем запросы с любых доменов (В продакшене заменить на конкретные домены фронтенда)
    allow_credentials=True, # Разрешить cookies и авторизационные заголовки
    allow_methods=["*"],  # Разрешаем все методы (GET, POST, PUT, DELETE и т.д.)
    allow_headers=["*"],  # Разрешаем все заголовки
)

"""
Включение роутеров в приложение
Роутер auth добавляет эндпоинты с префиксом /auth
"""
app.include_router(auth.router)

"""
Health check эндпоинт
Используется для проверки работоспособности сервиса:
- Docker healthchecks
- Kubernetes liveness/readiness probes
- Load balancers
- Мониторинг
"""
@app.get("/health")
async def health():
    return {
        "status": "healthy", 
        "service": "gateway",
        "version": "1.0.0"
    }


"""
Точка входа при запуске файла напрямую
Если файл запущен как основной (не импортирован), 
запускаем Uvicorn сервер
"""
if __name__ == "__main__":
    uvicorn.run(
        app, 
        host="0.0.0.0",  # Слушаем все сетевые интерфейсы
        port=8000        # Порт, на котором запускается сервер
    )