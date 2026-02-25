from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api import admin, auth, health, inspections, monitoring, reports, selfchecks, systems
from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import SessionLocal, engine
from app.models import Base
from app.models.inspection import InspectionPoint
from app.models.system import System
from app.models.user import Role, User

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(inspections.router, prefix=settings.API_PREFIX)
app.include_router(selfchecks.router, prefix=settings.API_PREFIX)
app.include_router(systems.router, prefix=settings.API_PREFIX)
app.include_router(monitoring.router, prefix=settings.API_PREFIX)
app.include_router(reports.router, prefix=settings.API_PREFIX)
app.include_router(admin.router, prefix=settings.API_PREFIX)


def init_seed(db: Session):
    role_codes = ["inspector", "admin", "super_admin"]
    for code in role_codes:
        if not db.query(Role).filter(Role.code == code).first():
            db.add(Role(code=code, name=code))
    db.commit()

    super_admin_role = db.query(Role).filter(Role.code == "super_admin").first()
    if not db.query(User).filter(User.username == settings.INIT_ADMIN_USERNAME).first():
        db.add(
            User(
                username=settings.INIT_ADMIN_USERNAME,
                password_hash=get_password_hash(settings.INIT_ADMIN_PASSWORD),
                role_id=super_admin_role.id,
                is_active=True,
            )
        )
        db.commit()

    if not db.query(System).filter(System.system_code == "DEMO-SYS-001").first():
        sys1 = System(system_code="DEMO-SYS-001", name="示例业务系统", env="prod")
        db.add(sys1)
        db.commit()
        db.refresh(sys1)
        db.add(
            InspectionPoint(
                system_id=sys1.id,
                point_code="P-001",
                qr_content="QR://DEMO-SYS-001/P-001",
                location="机房A-01机柜",
            )
        )
        db.commit()


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        init_seed(db)
    finally:
        db.close()


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
