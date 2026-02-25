from fastapi import APIRouter

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/inspections")
def inspection_report():
    return {"items": []}


@router.get("/selfchecks")
def selfcheck_report():
    return {"items": []}
