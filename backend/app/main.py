from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.api import admin, auth, health, inspections, reports, selfchecks, systems
from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import SessionLocal, engine
from app.models import Base
from app.models.inspection import InspectionPoint
from app.models.system import System
from app.models.user import Role, User

app = FastAPI(title=settings.APP_NAME)

app.include_router(health.router)
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(inspections.router, prefix=settings.API_PREFIX)
app.include_router(selfchecks.router, prefix=settings.API_PREFIX)
app.include_router(systems.router, prefix=settings.API_PREFIX)
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


@app.get("/")
def root():
    return {"service": settings.APP_NAME, "env": settings.APP_ENV}
