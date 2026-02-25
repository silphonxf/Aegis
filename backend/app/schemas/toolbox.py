from pydantic import BaseModel, Field


class PingRequest(BaseModel):
    host: str = Field(default="127.0.0.1", min_length=1, max_length=255)
    count: int = Field(default=1, ge=1, le=4)


class PortCheckRequest(BaseModel):
    host: str = Field(default="127.0.0.1", min_length=1, max_length=255)
    port: int = Field(ge=1, le=65535)
    timeout_ms: int = Field(default=1200, ge=100, le=5000)


class RestartTaskRequest(BaseModel):
    target: str = Field(default="local-host", min_length=1, max_length=255)
    reason: str | None = Field(default=None, max_length=255)
