from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field, validator


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    role_code: str


class CreateAIExternalApiKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    remark: Optional[str] = Field(default=None, max_length=500)


class CreateAssetRequest(BaseModel):
    asset_code: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    category: str = Field(default="server", min_length=1, max_length=64)
    system_id: Optional[int] = None
    room_id: Optional[int] = None
    location: Optional[str] = Field(default=None, max_length=255)
    ip_address: Optional[str] = Field(default=None, max_length=64)
    port: Optional[int] = None
    connection_type: Optional[str] = Field(default=None, max_length=32)
    status: str = Field(default="in_use", min_length=1, max_length=32)
    remark: Optional[str] = Field(default=None, max_length=500)


class UpdateAssetRequest(BaseModel):
    asset_code: Optional[str] = Field(default=None, min_length=2, max_length=64)
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    category: Optional[str] = Field(default=None, min_length=1, max_length=64)
    system_id: Optional[int] = None
    room_id: Optional[int] = None
    location: Optional[str] = Field(default=None, max_length=255)
    ip_address: Optional[str] = Field(default=None, max_length=64)
    port: Optional[int] = None
    connection_type: Optional[str] = Field(default=None, max_length=32)
    status: Optional[str] = Field(default=None, min_length=1, max_length=32)
    remark: Optional[str] = Field(default=None, max_length=500)


class CreateRoomRequest(BaseModel):
    room_code: Optional[str] = Field(default=None, min_length=1, max_length=64)
    room_name: str = Field(min_length=1, max_length=128)
    qr_content: str = Field(min_length=1, max_length=255)
    nfc_tag: Optional[str] = Field(default=None, max_length=255)
    check_items: List[str] = Field(default_factory=list, max_items=50)
    building: Optional[str] = Field(default=None, max_length=128)
    floor: Optional[str] = Field(default=None, max_length=64)
    location_detail: Optional[str] = Field(default=None, max_length=255)
    remark: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = True


class UpdateRoomRequest(BaseModel):
    room_code: Optional[str] = Field(default=None, min_length=1, max_length=64)
    room_name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    qr_content: Optional[str] = Field(default=None, min_length=1, max_length=255)
    nfc_tag: Optional[str] = Field(default=None, max_length=255)
    check_items: Optional[List[str]] = Field(default=None, max_items=50)
    building: Optional[str] = Field(default=None, max_length=128)
    floor: Optional[str] = Field(default=None, max_length=64)
    location_detail: Optional[str] = Field(default=None, max_length=255)
    remark: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None


class CreateInspectionPointRequest(BaseModel):
    room_id: int
    system_id: Optional[int] = None
    point_code: str = Field(min_length=1, max_length=64)
    point_name: str = Field(min_length=1, max_length=128)
    point_type: str = Field(default="qr", max_length=32)
    qr_content: Optional[str] = Field(default=None, max_length=255)
    nfc_tag: Optional[str] = Field(default=None, max_length=255)
    location_detail: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = True


class UpdateInspectionPointRequest(BaseModel):
    room_id: Optional[int] = None
    system_id: Optional[int] = None
    point_code: Optional[str] = Field(default=None, min_length=1, max_length=64)
    point_name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    point_type: Optional[str] = Field(default=None, max_length=32)
    qr_content: Optional[str] = Field(default=None, max_length=255)
    nfc_tag: Optional[str] = Field(default=None, max_length=255)
    location_detail: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = None


class BatchCreateAssetsRequest(BaseModel):
    items: List[CreateAssetRequest] = Field(default_factory=list, min_items=1, max_items=500)


class ThreatIntelQueryRequest(BaseModel):
    ips: List[str] = Field(default_factory=list, min_items=1, max_items=100)
    lang: str = Field(default="zh", pattern="^(zh|en)$")
    realtime_verdict: bool = True


class ThreatIntelQuickInputRequest(BaseModel):
    raw_input: str = Field(min_length=1, max_length=20000)
    lang: str = Field(default="zh", pattern="^(zh|en)$")
    realtime_verdict: bool = True

    @validator("raw_input")
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
