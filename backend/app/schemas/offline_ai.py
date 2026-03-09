from pydantic import BaseModel, Field


class OfflineAnalyzeRequest(BaseModel):
    title: str = Field(default="离线错误日志分析", min_length=1, max_length=120)
    source_type: str = Field(default="manual", pattern="^(manual|system)$")
    source_ref: str | None = Field(default=None, max_length=255)
    severity: str = Field(default="medium", pattern="^(low|medium|high)$")
    detail: str = Field(min_length=1, max_length=20000)


class OfflineAnalyzeResponse(BaseModel):
    task_id: int
    status: str
    severity: str
    summary: str
    matched_rules: list[dict]
    suggestions: list[str]
