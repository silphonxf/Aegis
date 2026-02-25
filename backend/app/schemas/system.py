from pydantic import BaseModel


class SystemCreate(BaseModel):
    system_code: str
    name: str
    owner_user_id: int | None = None
    env: str = "prod"


class StatusSnapshotCreate(BaseModel):
    host_online: str = "unknown"
    port_ok: str = "unknown"
    cpu_usage: int | None = None
    mem_usage: int | None = None
    disk_usage: int | None = None
    last_inspection_result: str = "unknown"
    last_selfcheck_result: str = "unknown"
