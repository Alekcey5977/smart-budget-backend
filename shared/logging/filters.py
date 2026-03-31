import logging
import uuid


class ContextFilter(logging.Filter):
    """Filter для добавления контекстной информации в логи"""

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def filter(self, record: logging.LogRecord) -> bool:
        # Добавляем service_name
        record.service_name = self.service_name
        
        trace_id = getattr(record, "trace_id", None)
        if not trace_id:
            trace_id = str(uuid.uuid4())[:8]
        record.trace_id = trace_id
        
        record.span_id = str(uuid.uuid4())[:6]
        
        return True


class TraceIdFilter(logging.Filter):
    """Filter для извлечения trace_id из LogRecord"""

    def filter(self, record: logging.LogRecord) -> bool:
        trace_id = getattr(record, "trace_id", None)
        
        if not trace_id:
            trace_id = str(uuid.uuid4())[:8]
        
        record.trace_id = trace_id
        return True
