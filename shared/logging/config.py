import logging
import sys


class ServiceFilter(logging.Filter):
    """Filter для добавления service_name в каждый лог"""

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def filter(self, record: logging.LogRecord) -> bool:
        record.service_name = self.service_name
        return True


def setup_logging(service_name: str, level: int = logging.INFO, log_format: str = "text") -> None:
    """Настройка логирования для микросервиса"""

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    root_logger.handlers = []

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    console_handler.addFilter(ServiceFilter(service_name))

    if log_format == "json":
        from pythonjsonlogger import jsonlogger

        formatter = jsonlogger.JsonFormatter(fmt="%(asctime)s %(levelname)s %(name)s %(message)s %(service_name)s")
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(service_name)s - %(name)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Настраиваем логгер uvicorn
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers = []
    uvicorn_logger.addHandler(console_handler)
    uvicorn_logger.setLevel(level)

    # Настраиваем логгер для HTTP запросов
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers = []
    uvicorn_access.addHandler(console_handler)
    uvicorn_access.setLevel(level)

    # Настраиваем SQLAlchemy логгер
    sqlalchemy_logger = logging.getLogger("sqlalchemy")
    sqlalchemy_logger.handlers = []
    sqlalchemy_logger.addHandler(console_handler)
    sqlalchemy_logger.setLevel(logging.WARNING)

    logging.info(f"Логирование настроено для сервиса: {service_name}")
