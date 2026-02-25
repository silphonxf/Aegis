from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.audit import log_action

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username, User.is_active == True).first()
    if not user or not verify_password(data.password, user.password_hash):
        log_action(
            db,
            "login_failed",
            "auth",
            detail={"username": data.username, "ip": request.client.host if request.client else None},
            username=data.username,
        )
        raise HTTPException(status_code=401, detail={"code": "AUTH_INVALID", "message": "用户名或密码错误"})

    token = create_access_token(user.username)
    log_action(
        db,
        "login_success",
        "auth",
        user=user,
        detail={"ip": request.client.host if request.client else None},
    )
    return TokenResponse(access_token=token)


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role.code,
        "is_active": current_user.is_active,
    }
