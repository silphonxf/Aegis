from typing import Any, Dict, List, Literal, Optional, Set, Tuple

from pydantic import BaseModel, Field, validator


class SystemLogConfigSave(BaseModel):
    id: Optional[int] = None
    log_name: str = Field(min_length=1, max_length=128)
    absolute_path: str = Field(min_length=1, max_length=500)
    log_level: str = Field(default="warning", pattern="^(info|warning|error)$")
    is_active: bool = True
    remark: Optional[str] = None

    @validator("absolute_path")
    def absolute_path_must_be_absolute(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("日志位置必须是系统所在服务器的绝对路径")
        return value


class SystemCreate(BaseModel):
    system_code: str
    name: str
    host_address: Optional[str] = None
    owner_user_id: Optional[int] = None
    owner_user_ids: List[int] = Field(default_factory=list)
    env: str = "prod"
    check_frequency: Optional[str] = None
    remark: Optional[str] = None
    log_configs: List[SystemLogConfigSave] = Field(default_factory=list)


class SystemUpdate(BaseModel):
    system_code: Optional[str] = None
    name: Optional[str] = None
    host_address: Optional[str] = None
    owner_user_id: Optional[int] = None
    owner_user_ids: Optional[List[int]] = None
    env: Optional[str] = None
    check_frequency: Optional[str] = None
    remark: Optional[str] = None
    is_active: Optional[bool] = None
    log_configs: Optional[List[SystemLogConfigSave]] = None


class StatusSnapshotCreate(BaseModel):
    host_online: Literal["normal", "abnormal", "unknown"] = "unknown"
    port_ok: Literal["normal", "abnormal", "unknown"] = "unknown"

    cpu_usage: Optional[int] = Field(default=None, ge=0, le=100)
    mem_usage: Optional[int] = Field(default=None, ge=0, le=100)
    disk_usage: Optional[int] = Field(default=None, ge=0, le=100)

    last_inspection_result: Literal["normal", "abnormal", "unknown"] = "unknown"
    last_selfcheck_result: Literal["normal", "warning", "critical", "unknown"] = "unknown"
