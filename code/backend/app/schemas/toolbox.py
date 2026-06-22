from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field


class PingRequest(BaseModel):
    host: str = Field(default="127.0.0.1", min_length=1, max_length=255)
    count: int = Field(default=1, ge=1, le=10)


class PortCheckRequest(BaseModel):
    host: str = Field(default="127.0.0.1", min_length=1, max_length=255)
    port: int = Field(ge=1, le=65535)
    timeout_ms: int = Field(default=1200, ge=100, le=5000)


class RestartTaskRequest(BaseModel):
    target: str = Field(default="local-host", min_length=1, max_length=255)
    reason: Optional[str] = Field(default=None, max_length=255)


class TaskStatusUpdateRequest(BaseModel):
    status: str = Field(pattern="^(approved|running|rejected|done|failed|cancelled)$")
    note: Optional[str] = Field(default=None, max_length=255)
    executor: Optional[str] = Field(default=None, max_length=32)


class ErrorLogSourceRequest(BaseModel):
    source: str = Field(default="aegis", pattern="^(aegis|system)$")
    file_name: Optional[str] = Field(default=None, max_length=512)
    quick_range: Optional[str] = Field(default="1h", pattern="^(1h|3h|6h|all)?$")
    start_at: Optional[str] = Field(default=None, max_length=32)
    end_at: Optional[str] = Field(default=None, max_length=32)
    level: str = Field(default="warning", pattern="^(info|warning|error)$")
    lines: int = Field(default=5000, ge=1, le=20000)
