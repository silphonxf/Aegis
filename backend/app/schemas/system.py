from pydantic import BaseModel


class SystemCreate(BaseModel):
    system_code: str
    name: str
    owner_user_id: int | None = None
    env: str = "prod"
