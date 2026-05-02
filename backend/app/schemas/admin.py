from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field, field_validator


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    role_code: str


class CreateAssetRequest(BaseModel):
    asset_code: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    category: str = Field(default="server", min_length=1, max_length=64)
    system_id: Optional[int] = None
    location: Optional[str] = Field(default=None, max_length=255)
    status: str = Field(default="in_use", min_length=1, max_length=32)


class BatchCreateAssetsRequest(BaseModel):
    items: list[CreateAssetRequest] = Field(default_factory=list, min_length=1, max_length=500)


class ThreatIntelQueryRequest(BaseModel):
    ips: List[str] = Field(default_factory=list, min_length=1, max_length=100)
    lang: str = Field(default="zh", pattern="^(zh|en)$")
    realtime_verdict: bool = True


class ThreatIntelQuickInputRequest(BaseModel):
    raw_input: str = Field(min_length=1, max_length=20000)
    lang: str = Field(default="zh", pattern="^(zh|en)$")
    realtime_verdict: bool = True

    @field_validator("raw_input")
    @classmethod
    def normalize_raw_input(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("请输入至少一个 IP")
        return cleaned


class ThreatIntelBlockRequest(BaseModel):
    ip: str = Field(min_length=2, max_length=64)
    risk_level: Optional[str] = Field(default=None, max_length=32)
    reason: Optional[str] = Field(default=None, max_length=500)
    source: str = Field(default="threatbook", max_length=64)
    dry_run: bool = True
