from fastapi import FastAPI

from app.api import admin, auth, health, inspections, reports, selfchecks, systems
from app.core.config import settings

app = FastAPI(title=settings.APP_NAME)

app.include_router(health.router)
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(inspections.router, prefix=settings.API_PREFIX)
app.include_router(selfchecks.router, prefix=settings.API_PREFIX)
app.include_router(systems.router, prefix=settings.API_PREFIX)
app.include_router(reports.router, prefix=settings.API_PREFIX)
app.include_router(admin.router, prefix=settings.API_PREFIX)


@app.get("/")
def root():
    return {"service": settings.APP_NAME, "env": settings.APP_ENV}
