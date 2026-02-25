from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.system import System
from app.models.user import Role, User
from app.schemas.system import SystemCreate

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
def list_users(db: Session = Depends(get_db), _: User = Depends(require_roles("super_admin"))):
    users = db.query(User).all()
    return {
        "items": [
            {"id": u.id, "username": u.username, "role": u.role.code, "is_active": u.is_active}
            for u in users
        ]
    }


@router.post("/users")
def create_user(
    username: str,
    password: str,
    role_code: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("super_admin")),
):
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    role = db.query(Role).filter(Role.code == role_code).first()
    if not role:
        raise HTTPException(status_code=400, detail="角色不存在")
    user = User(username=username, password_hash=get_password_hash(password), role_id=role.id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id}


@router.get("/systems")
def list_systems(db: Session = Depends(get_db), _: User = Depends(require_roles("admin", "super_admin"))):
    items = db.query(System).all()
    return {"items": [{"id": i.id, "system_code": i.system_code, "name": i.name, "env": i.env} for i in items]}


@router.post("/systems")
def create_system(
    payload: SystemCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "super_admin")),
):
    system = System(
        system_code=payload.system_code,
        name=payload.name,
        owner_user_id=payload.owner_user_id,
        env=payload.env,
    )
    db.add(system)
    db.commit()
    db.refresh(system)
    return {"id": system.id}
