from pydantic import BaseModel, Field, model_validator


class StatusRuleUpdate(BaseModel):
    cpu_warn: int = Field(ge=1, le=100)
    cpu_critical: int = Field(ge=1, le=100)
    mem_warn: int = Field(ge=1, le=100)
    mem_critical: int = Field(ge=1, le=100)
    disk_warn: int = Field(ge=1, le=100)
    disk_critical: int = Field(ge=1, le=100)

    @model_validator(mode="after")
    def validate_threshold_order(self):
        if self.cpu_warn >= self.cpu_critical:
            raise ValueError("CPU 黄阈值必须小于红阈值")
        if self.mem_warn >= self.mem_critical:
            raise ValueError("内存黄阈值必须小于红阈值")
        if self.disk_warn >= self.disk_critical:
            raise ValueError("磁盘黄阈值必须小于红阈值")
        return self
