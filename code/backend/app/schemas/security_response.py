from typing import List, Optional

from pydantic import BaseModel, Field, validator


class FeishuBindingUpdate(BaseModel):
    open_id: str = Field(min_length=3, max_length=128)
    display_name: Optional[str] = Field(default=None, max_length=128)
    aegis_user_id: Optional[int] = None
    can_query: bool = True
    can_block: bool = False
    enabled: bool = True

    @validator("open_id")
    def normalize_open_id(cls, value: str) -> str:
        return value.strip()


class SecurityBatchAnalyzeRequest(BaseModel):
    raw_input: str = Field(min_length=2, max_length=20000)
    source_chat_id: Optional[str] = Field(default=None, max_length=128)
    source_message_id: Optional[str] = Field(default=None, max_length=128)
    firewall_target_code: str = Field(default="test-primary", min_length=1, max_length=64)


class SecurityBatchPrepareRequest(BaseModel):
    selection: str = Field(default="recommended", pattern="^(recommended|all_malicious|selected)$")
    selected_ips: Optional[List[str]] = Field(default=None, max_items=100)


class SecurityBatchItemSelectionRequest(BaseModel):
    ip: str = Field(min_length=7, max_length=45)
    selected: bool


class SecurityBatchConfirmRequest(BaseModel):
    pass


class SecurityBatchExecuteRequest(BaseModel):
    dry_run: bool = True
