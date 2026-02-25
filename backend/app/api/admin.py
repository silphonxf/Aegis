from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.system import System
from app.models.user import Role, User
from app.schemas.admin import CreateUserRequest
from app.schemas.system import SystemCreate
from app.services.audit import log_action

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
def list_users(
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("super_admin")),
):
    page = max(page, 1)
    size = min(max(size, 1), 100)
    q = db.query(User)
    total = q.count()
    users = q.offset((page - 1) * size).limit(size).all()
    return {
        "page": page,
        "size": size,
        "total": total,
        "items": [
            {"id": u.id, "username": u.username, "role": u.role.code, "is_active": u.is_active}
            for u in users
        ],
    }


@router.post("/users")
def create_user(
    payload: CreateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("super_admin")),
):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    role = db.query(Role).filter(Role.code == payload.role_code).first()
    if not role:
        raise HTTPException(status_code=400, detail="角色不存在")
    user = User(username=payload.username, password_hash=get_password_hash(payload.password), role_id=role.id)
    db.add(user)
    db.commit()
    db.refresh(user)
    log_action(db, "create_user", "user", current_user, {"new_user_id": user.id, "username": user.username})
    return {"id": user.id}


@router.get("/systems")
def list_systems(
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "super_admin")),
):
    page = max(page, 1)
    size = min(max(size, 1), 100)
    q = db.query(System)
    total = q.count()
    items = q.offset((page - 1) * size).limit(size).all()
    return {
        "page": page,
        "size": size,
        "total": total,
        "items": [{"id": i.id, "system_code": i.system_code, "name": i.name, "env": i.env} for i in items],
    }


@router.post("/systems")
def create_system(
    payload: SystemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
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
    log_action(db, "create_system", "system", current_user, {"system_id": system.id, "system_code": system.system_code})
    return {"id": system.id}


@router.get("/audit-logs")
def list_audit_logs(
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("super_admin")),
):
    page = max(page, 1)
    size = min(max(size, 1), 100)
    q = db.query(AuditLog)
    total = q.count()
    items = q.order_by(AuditLog.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return {
        "page": page,
        "size": size,
        "total": total,
        "items": [
            {
                "id": i.id,
                "user_id": i.user_id,
                "username": i.username,
                "action": i.action,
                "resource": i.resource,
                "detail": i.detail,
                "created_at": i.created_at,
            }
            for i in items
        ],
    }
