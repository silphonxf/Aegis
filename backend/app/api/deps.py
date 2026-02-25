from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import ALGORITHM
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/login")


def _auth_error(message: str, code: str = "AUTH_REQUIRED") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": code, "message": message},
    )


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise _auth_error("登录状态无效，请重新登录", "TOKEN_INVALID")
    except ExpiredSignatureError:
        raise _auth_error("登录已过期，请重新登录", "TOKEN_EXPIRED")
    except JWTError:
        raise _auth_error("登录状态无效，请重新登录", "TOKEN_INVALID")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise _auth_error("用户不存在或已被删除", "USER_NOT_FOUND")
    if not user.is_active:
        raise _auth_error("账号已禁用，请联系管理员", "USER_DISABLED")
    return user


def require_roles(*allowed: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role.code not in allowed:
            raise HTTPException(
                status_code=403,
                detail={"code": "FORBIDDEN", "message": "权限不足，无法访问该资源"},
            )
        return user

    return checker
