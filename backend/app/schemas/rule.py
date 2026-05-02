from pydantic import BaseModel, Field, root_validator


class StatusRuleUpdate(BaseModel):
    cpu_warn: int = Field(ge=1, le=100)
    cpu_critical: int = Field(ge=1, le=100)
    mem_warn: int = Field(ge=1, le=100)
    mem_critical: int = Field(ge=1, le=100)
    disk_warn: int = Field(ge=1, le=100)
    disk_critical: int = Field(ge=1, le=100)

    @root_validator
    def validate_threshold_order(cls, values):
        if values.get("cpu_warn") >= values.get("cpu_critical"):
            raise ValueError("CPU 黄阈值必须小于红阈值")
        if values.get("mem_warn") >= values.get("mem_critical"):
            raise ValueError("内存黄阈值必须小于红阈值")
        if values.get("disk_warn") >= values.get("disk_critical"):
            raise ValueError("磁盘黄阈值必须小于红阈值")
        return values
