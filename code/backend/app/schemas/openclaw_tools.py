from typing import Optional

from pydantic import BaseModel, Field


class OpenClawIpAnalyzeRequest(BaseModel):
    raw_input: str = Field(min_length=2, max_length=20000)
    session_key: Optional[str] = Field(default=None, max_length=128)
    message_id: Optional[str] = Field(default=None, max_length=128)


class OpenClawBatchPrepareRequest(BaseModel):
    selection: str = Field(default="recommended", pattern="^(recommended|all_malicious)$")


class OpenClawBatchConfirmRequest(BaseModel):
    pass


class OpenClawBatchExecuteRequest(BaseModel):
    dry_run: bool = True
    confirmed: bool = False
