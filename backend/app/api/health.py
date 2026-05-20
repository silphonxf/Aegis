from fastapi import APIRouter, Request

from app.core.logging import get_logger

router = APIRouter()
logger = get_logger("health")


@router.get("/healthz")
def healthz(request: Request):
    logger.info("健康检查通过: path=%s", request.url.path)
    return {"status": "ok", "service": "aegis-api", "request_id": getattr(request.state, "request_id", "-")}
