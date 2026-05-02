from pydantic import BaseModel, Field


class DiagnoseRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    detail: str = Field(min_length=1, max_length=2000)
    severity: str = Field(default="medium", regex="^(low|medium|high)$")
