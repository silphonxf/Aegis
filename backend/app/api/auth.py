from fastapi import APIRouter

from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest):
    # TODO: 接入真实用户校验与JWT签发
    fake_token = f"token_for_{data.username}"
    return TokenResponse(access_token=fake_token)


@router.get("/me")
def me():
    # TODO: 接入真实鉴权上下文
    return {"username": "demo", "role": "super_admin"}
