from pydantic import BaseModel, Field


class StatusRuleUpdate(BaseModel):
    cpu_warn: int = Field(ge=1, le=100)
    cpu_critical: int = Field(ge=1, le=100)
    mem_warn: int = Field(ge=1, le=100)
    mem_critical: int = Field(ge=1, le=100)
    disk_warn: int = Field(ge=1, le=100)
    disk_critical: int = Field(ge=1, le=100)
