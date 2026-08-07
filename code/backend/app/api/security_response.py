from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.security_response import FeishuUserBinding, IpBlockBatch
from app.models.user import User
from app.schemas.security_response import (
    FeishuBindingUpdate,
    SecurityBatchAnalyzeRequest,
    SecurityBatchConfirmRequest,
    SecurityBatchExecuteRequest,
    SecurityBatchPrepareRequest,
)
from app.services.audit import log_action
from app.services.security_response import (
    SecurityResponseError,
    create_analysis_batch,
    execute_batch,
    prepare_batch,
    confirm_jinan_batch,
    serialize_batch,
    serialize_binding,
    upsert_feishu_binding,
)


router = APIRouter(prefix="/admin/security-response", tags=["security-response"])


def _error(exc: SecurityResponseError) -> HTTPException:
    return HTTPException(status_code=400, detail={"code": "SECURITY_RESPONSE_ERROR", "message": str(exc)})


@router.get("/feishu-bindings")
def list_feishu_bindings(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("super_admin")),
):
    rows = db.query(FeishuUserBinding).order_by(FeishuUserBinding.id.desc()).all()
    return {"items": [serialize_binding(row) for row in rows]}


@router.put("/feishu-bindings")
def save_feishu_binding(
    payload: FeishuBindingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("super_admin")),
):
    try:
        binding = upsert_feishu_binding(db=db, **payload.dict())
    except SecurityResponseError as exc:
        raise _error(exc) from exc
    result = serialize_binding(binding)
    log_action(db, "save_feishu_security_binding", "security_response", current_user, result)
    return result


@router.post("/batches/analyze")
def analyze_batch(
    payload: SecurityBatchAnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    try:
        batch = create_analysis_batch(
            db,
            raw_input=payload.raw_input,
            requester_user_id=current_user.id,
            requester_open_id=None,
            source_chat_id=payload.source_chat_id,
            source_message_id=payload.source_message_id,
            firewall_target_code=payload.firewall_target_code,
        )
    except SecurityResponseError as exc:
        raise _error(exc) from exc
    return serialize_batch(db, batch)


@router.get("/batches/{batch_id}")
def get_batch(
    batch_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "super_admin")),
):
    batch = db.query(IpBlockBatch).filter(IpBlockBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail={"code": "BATCH_NOT_FOUND", "message": "批次不存在"})
    return serialize_batch(db, batch)


@router.post("/batches/{batch_id}/prepare")
def prepare_block_batch(
    batch_id: str,
    payload: SecurityBatchPrepareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    try:
        batch = prepare_batch(db, batch_id, payload.selection, current_user.id, None)
    except SecurityResponseError as exc:
        raise _error(exc) from exc
    return serialize_batch(db, batch)


@router.post("/batches/{batch_id}/confirm-jinan")
def confirm_jinan(
    batch_id: str,
    payload: SecurityBatchConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    try:
        batch = confirm_jinan_batch(db, batch_id, current_user.id, None)
    except SecurityResponseError as exc:
        raise _error(exc) from exc
    return serialize_batch(db, batch)


@router.post("/batches/{batch_id}/execute")
def execute_block_batch(
    batch_id: str,
    payload: SecurityBatchExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    try:
        batch = execute_batch(db, batch_id, current_user.id, None, payload.dry_run)
    except SecurityResponseError as exc:
        raise _error(exc) from exc
    return serialize_batch(db, batch)
