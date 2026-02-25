from fastapi import APIRouter

router = APIRouter(prefix="/systems", tags=["systems"])


@router.get("/status/overview")
def status_overview():
    return {
        "summary": {"green": 0, "yellow": 0, "red": 0},
        "items": [],
    }


@router.post("/{system_id}/status/snapshot")
def create_status_snapshot(system_id: int):
    return {"system_id": system_id, "saved": True}
