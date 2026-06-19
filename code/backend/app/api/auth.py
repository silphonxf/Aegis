from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.logging import get_logger
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, TokenResponse, UserProfileUpdateRequest
from app.services.audit import log_action

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger("auth")


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    logger.info("收到登录请求: username=%s", data.username)
    user = db.query(User).filter(User.username == data.username, User.is_active == True).first()
    if not user or not verify_password(data.password, user.password_hash):
        logger.warning("登录失败: username=%s client=%s", data.username, request.client.host if request.client else "-")
        log_action(
            db,
            "login_failed",
            "auth",
            detail={"username": data.username, "ip": request.client.host if request.client else None},
            username=data.username,
        )
        raise HTTPException(status_code=401, detail={"code": "AUTH_INVALID", "message": "用户名或密码错误"})

    token = create_access_token(user.username)
    logger.info("登录成功: user=%s", user.username)
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
        "nickname": current_user.nickname,
        "avatar_url": current_user.avatar_url,
        "role": current_user.role.code,
        "is_active": current_user.is_active,
    }


@router.put("/profile")
def update_profile(
    payload: UserProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info("更新账号信息: user=%s", current_user.username)
    current_user.nickname = payload.nickname
    current_user.avatar_url = payload.avatar_url
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    log_action(db, "update_profile", "auth", current_user, {"nickname": payload.nickname, "avatar_url": payload.avatar_url})
    return {
        "id": current_user.id,
        "username": current_user.username,
        "nickname": current_user.nickname,
        "avatar_url": current_user.avatar_url,
    }


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info("修改密码: user=%s", current_user.username)
    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail={"code": "PASSWORD_OLD_INVALID", "message": "旧密码不正确"})

    current_user.password_hash = get_password_hash(payload.new_password)
    db.add(current_user)
    db.commit()

    log_action(db, "change_password", "auth", current_user, None)
    return {"ok": True, "message": "密码修改成功"}
