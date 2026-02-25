from pydantic import BaseModel, Field


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    role_code: str


class CreateAssetRequest(BaseModel):
    asset_code: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    category: str = Field(default="server", min_length=1, max_length=64)
    system_id: int | None = None
    location: str | None = Field(default=None, max_length=255)
    status: str = Field(default="in_use", min_length=1, max_length=32)


class BatchCreateAssetsRequest(BaseModel):
    items: list[CreateAssetRequest] = Field(default_factory=list, min_length=1, max_length=500)
