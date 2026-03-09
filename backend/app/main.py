from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api import admin, ai, auth, health, inspections, monitoring, reports, selfchecks, systems, toolbox
from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.inspection import InspectionPoint
from app.models.system import System
from app.models.user import Role, User

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_origin_regex=settings.CORS_ALLOW_ORIGIN_REGEX,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

app.include_router(health.router)
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(inspections.router, prefix=settings.API_PREFIX)
app.include_router(selfchecks.router, prefix=settings.API_PREFIX)
app.include_router(systems.router, prefix=settings.API_PREFIX)
app.include_router(monitoring.router, prefix=settings.API_PREFIX)
app.include_router(reports.router, prefix=settings.API_PREFIX)
app.include_router(admin.router, prefix=settings.API_PREFIX)
app.include_router(toolbox.router, prefix=settings.API_PREFIX)
app.include_router(ai.router, prefix=settings.API_PREFIX)


def _next_id(db: Session, model) -> int:
    current = db.query(func.max(model.id)).scalar()
    return (current or 0) + 1


def init_seed(db: Session):
    role_codes = ["inspector", "admin", "super_admin"]
    next_role_id = _next_id(db, Role)
    for code in role_codes:
        if not db.query(Role).filter(Role.code == code).first():
            db.add(Role(id=next_role_id, code=code, name=code))
            next_role_id += 1
    db.commit()

    super_admin_role = db.query(Role).filter(Role.code == "super_admin").first()
    if not db.query(User).filter(User.username == settings.INIT_ADMIN_USERNAME).first():
        db.add(
            User(
                id=_next_id(db, User),
                username=settings.INIT_ADMIN_USERNAME,
                password_hash=get_password_hash(settings.INIT_ADMIN_PASSWORD),
                role_id=super_admin_role.id,
                is_active=True,
            )
        )
        db.commit()

    if not db.query(System).filter(System.system_code == "DEMO-SYS-001").first():
        sys1 = System(id=_next_id(db, System), system_code="DEMO-SYS-001", name="示例业务系统", env="prod")
        db.add(sys1)
        db.commit()
        db.refresh(sys1)
        db.add(
            InspectionPoint(
                id=_next_id(db, InspectionPoint),
                system_id=sys1.id,
                point_code="P-001",
                qr_content="QR://DEMO-SYS-001/P-001",
                location="机房A-01机柜",
            )
        )
        db.commit()


@app.on_event("startup")
def on_startup():
    # 数据库结构与初始数据统一通过 Alembic + 显式初始化脚本完成。
    return None


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "请求参数校验失败",
            "errors": exc.errors(),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", "HTTP_ERROR")
        message = exc.detail.get("message", "请求失败")
    else:
        code = "HTTP_ERROR"
        message = str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": code,
            "message": message,
        },
    )


@app.get("/")
def root():
    return {"service": settings.APP_NAME, "env": settings.APP_ENV}
