import logging
import time

from fastapi import Request, Response
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware для автоматического логирования всех HTTP-запросов.

    Логирует:
    - Метод и путь запроса
    - Статус ответа
    - Время выполнения
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        trace_id = request.headers.get("X-Trace-Id", None)

        # Логируем начало запроса
        logger.info(
            f"Запрос: {request.method} {request.url.path}",
            extra={
                "trace_id": trace_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params) if request.query_params else None,
            },
        )

        start_time = time.time()

        # Выполняем запрос
        try:
            response = await call_next(request)
        except Exception as e:
            # Логируем ошибку
            duration = time.time() - start_time
            logger.error(
                f"Ошибка при обработке запроса: {request.method} {request.url.path} - {str(e)}",
                extra={
                    "trace_id": trace_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration * 1000, 2),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

        duration = time.time() - start_time

        # Определяем уровень логирования по статусу
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.INFO
        else:
            log_level = logging.INFO

        # Логируем результат
        logger.log(
            log_level,
            f"Ответ: {request.method} {request.url.path} - {response.status_code}",
            extra={
                "trace_id": trace_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2),
            },
        )

        if trace_id:
            response.headers["X-Trace-Id"] = trace_id

        return response
