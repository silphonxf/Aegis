from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
def list_users():
    return {"items": []}


@router.get("/systems")
def list_systems():
    return {"items": []}
