import contextvars
import logging
import sys
import uuid
from typing import Optional

from app.core.config import settings

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


class ModuleFieldFilter(logging.Filter):
    MODULE_ALIAS = {
        "uvicorn.error": "server",
        "uvicorn.access": "access",
        "uvicorn": "server",
        "fastapi": "api",
    }

    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "module_tag", None):
            record.module_tag = self.MODULE_ALIAS.get(record.name, record.name.split(".")[-1])
        return True


LOG_FORMAT = "%(asctime)s %(levelname)s %(module_tag)s [req:%(request_id)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def generate_request_id() -> str:
    return uuid.uuid4().hex


def set_request_id(request_id: Optional[str]) -> str:
    normalized = normalize_request_id(request_id)
    request_id_var.set(normalized)
    return normalized


def get_request_id() -> str:
    value = request_id_var.get()
    return value or "-"


def clear_request_id() -> None:
    request_id_var.set("-")


def normalize_request_id(request_id: Optional[str]) -> str:
    value = (request_id or "").strip().lower().replace("-", "")
    if len(value) == 32:
        try:
            int(value, 16)
            return value
        except ValueError:
            pass
    return generate_request_id()


def get_logger(module_tag: str) -> logging.Logger:
    logger = logging.getLogger(f"aegis.{module_tag}")
    logger = logging.LoggerAdapter(logger, extra={"module_tag": module_tag})
    return logger  # type: ignore[return-value]


def configure_logging() -> None:
    root = logging.getLogger()
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())
    handler.addFilter(ModuleFieldFilter())

    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
