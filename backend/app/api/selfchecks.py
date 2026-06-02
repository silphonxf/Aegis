from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.selfcheck import ChecklistTemplate, SelfcheckRecord
from app.models.system import System
from app.models.user import User
from app.schemas.selfcheck import SelfcheckRecordCreate, SelfcheckRecordSimpleCreate, SelfcheckTemplateCreate
from app.services.audit import log_action

router = APIRouter(prefix="/selfchecks", tags=["selfchecks"])
logger = get_logger("selfchecks")


@router.get("/templates")
def list_templates(
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    logger.info("查询自检模板: page=%s size=%s", page, size)
    page = max(page, 1)
    size = min(max(size, 1), 100)
    q = db.query(ChecklistTemplate).filter(ChecklistTemplate.is_active == True)
    total = q.count()
    items = q.offset((page - 1) * size).limit(size).all()
    logger.info("查询自检模板完成: total=%s returned=%s", total, len(items))
    return {
        "page": page,
        "size": size,
        "total": total,
        "items": [{"id": i.id, "system_id": i.system_id, "check_type": i.check_type, "name": i.name} for i in items],
    }


@router.post("/templates")
def create_template(
    payload: SelfcheckTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    logger.info("创建自检模板: user=%s system_id=%s check_type=%s", current_user.username, payload.system_id, payload.check_type)
    t = ChecklistTemplate(system_id=payload.system_id, check_type=payload.check_type, name=payload.name)
    db.add(t)
    db.commit()
    db.refresh(t)
    logger.info("创建自检模板成功: template_id=%s", t.id)
    log_action(db, "create_template", "checklist_template", current_user, {"template_id": t.id})
    return {"id": t.id}


@router.post("/records")
def create_selfcheck_record(
    payload: SelfcheckRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    logger.info("创建自检记录: user=%s system_id=%s template_id=%s result=%s", current_user.username, payload.system_id, payload.template_id, payload.result)
    if payload.template_id <= 0:
        logger.warning("创建自检记录失败: template_id 非法=%s", payload.template_id)
        raise HTTPException(status_code=400, detail={"code": "TEMPLATE_INVALID", "message": "template_id 必须为正整数"})

    tpl = db.query(ChecklistTemplate).filter(ChecklistTemplate.id == payload.template_id).first()
    if not tpl:
        logger.warning("创建自检记录失败: template_id=%s 不存在", payload.template_id)
        raise HTTPException(status_code=400, detail={"code": "TEMPLATE_NOT_FOUND", "message": "自检模板不存在"})
    if tpl.system_id != payload.system_id:
        logger.warning("创建自检记录失败: template_id=%s system_id=%s 与 payload.system_id=%s 不匹配", payload.template_id, tpl.system_id, payload.system_id)
        raise HTTPException(status_code=400, detail={"code": "TEMPLATE_SYSTEM_MISMATCH", "message": "模板与系统不匹配"})

    r = SelfcheckRecord(
        system_id=payload.system_id,
        template_id=payload.template_id,
        operator_id=current_user.id,
        result=payload.result,
        summary=payload.summary,
        review_status=payload.review_status,
        reviewed_by=payload.reviewed_by,
        reviewed_at=payload.reviewed_at,
        checked_at=payload.checked_at,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    logger.info("创建自检记录成功: record_id=%s", r.id)
    log_action(db, "create_selfcheck_record", "selfcheck_record", current_user, {"record_id": r.id})
    return {"id": r.id}


@router.post("/records/simple")
def create_selfcheck_record_simple(
    payload: SelfcheckRecordSimpleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    logger.info("创建简化自检记录: user=%s system_id=%s result=%s", current_user.username, payload.system_id, payload.result)
    target_system_id = payload.system_id
    if target_system_id is None:
        first_system = db.query(System).filter(System.is_active == True).order_by(System.id.asc()).first()
        if not first_system:
            logger.warning("创建简化自检记录失败: 无可用系统")
            raise HTTPException(status_code=400, detail={"code": "SYSTEM_NOT_FOUND", "message": "系统中无可用业务系统"})
        target_system_id = first_system.id

    tpl = (
        db.query(ChecklistTemplate)
        .filter(ChecklistTemplate.system_id == target_system_id, ChecklistTemplate.is_active == True)
        .order_by(ChecklistTemplate.id.asc())
        .first()
    )
    if not tpl:
        logger.info("简化自检记录未命中模板，自动创建默认模板: system_id=%s", target_system_id)
        # 为简化版自检入口自动兜底创建一个 daily 模板
        tpl = ChecklistTemplate(system_id=target_system_id, check_type="daily", name="默认日检模板")
        db.add(tpl)
        db.commit()
        db.refresh(tpl)

    summary = payload.content.strip()
    if payload.note:
        summary = f"{summary}；备注：{payload.note.strip()}"

    r = SelfcheckRecord(
        system_id=target_system_id,
        template_id=tpl.id,
        operator_id=current_user.id,
        result=payload.result,
        summary=summary,
        checked_at=datetime.utcnow(),
    )
    db.add(r)
    db.commit()
    db.refresh(r)

    logger.info("创建简化自检记录成功: record_id=%s system_id=%s template_id=%s", r.id, target_system_id, tpl.id)
    log_action(db, "create_selfcheck_record_simple", "selfcheck_record", current_user, {"record_id": r.id, "system_id": target_system_id})
    return {"id": r.id, "system_id": target_system_id, "template_id": tpl.id}


@router.get("/records")
def list_selfcheck_records(
    system_id: Optional[int] = None,
    result: Optional[str] = None,
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    logger.info("查询自检记录: system_id=%s result=%s page=%s size=%s", system_id, result, page, size)
    page = max(page, 1)
    size = min(max(size, 1), 100)
    q = db.query(SelfcheckRecord)
    if system_id is not None:
        q = q.filter(SelfcheckRecord.system_id == system_id)
    if result:
        q = q.filter(SelfcheckRecord.result == result)
    if start_at:
        q = q.filter(SelfcheckRecord.checked_at >= start_at)
    if end_at:
        q = q.filter(SelfcheckRecord.checked_at <= end_at)

    total = q.count()
    items = q.order_by(SelfcheckRecord.checked_at.desc()).offset((page - 1) * size).limit(size).all()
    logger.info("查询自检记录完成: total=%s returned=%s", total, len(items))
    return {
        "page": page,
        "size": size,
        "total": total,
        "items": [
            {
                "id": i.id,
                "system_id": i.system_id,
                "template_id": i.template_id,
                "operator_id": i.operator_id,
                "result": i.result,
                "summary": i.summary,
                "review_status": i.review_status,
                "reviewed_by": i.reviewed_by,
                "reviewed_at": i.reviewed_at,
                "checked_at": i.checked_at,
            }
            for i in items
        ],
    }
