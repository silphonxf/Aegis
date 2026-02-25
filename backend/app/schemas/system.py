from typing import Literal

from pydantic import BaseModel, Field


class SystemCreate(BaseModel):
    system_code: str
    name: str
    owner_user_id: int | None = None
    env: str = "prod"


class StatusSnapshotCreate(BaseModel):
    host_online: Literal["normal", "abnormal", "unknown"] = "unknown"
    port_ok: Literal["normal", "abnormal", "unknown"] = "unknown"

    cpu_usage: int | None = Field(default=None, ge=0, le=100)
    mem_usage: int | None = Field(default=None, ge=0, le=100)
    disk_usage: int | None = Field(default=None, ge=0, le=100)

    last_inspection_result: Literal["normal", "abnormal", "unknown"] = "unknown"
    last_selfcheck_result: Literal["normal", "warning", "critical", "unknown"] = "unknown"
