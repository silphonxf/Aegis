from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.inspection import InspectionPoint, InspectionRecord
from app.models.shared_data import Room
from app.models.system import System
from app.models.user import User
from app.schemas.inspection import InspectionCreate
from app.services.audit import log_action

router = APIRouter(prefix="/inspections", tags=["inspections"])
logger = get_logger("inspections")


def _parse_check_items(value: Optional[str]) -> List[str]:
    if not value:
        return []
    try:
        data = json.loads(value)
        if isinstance(data, list):
            return [str(item).strip() for item in data if str(item).strip()]
    except Exception:
        pass
    return [line.strip() for line in value.splitlines() if line.strip()]


def _monitoring_confirmation(room_id: Optional[int]) -> Dict[str, Any]:
    return {
        "has_alarm": False,
        "label": "监控无异常",
        "value": "monitoring_no_alarm",
        "options": [{"value": "monitoring_no_alarm", "label": "监控无异常"}],
    }


def _serialize_resolved_point(point: InspectionPoint, db: Session) -> Dict[str, Any]:
    room = db.query(Room).filter(Room.id == point.room_id).first() if point.room_id else None
    system = db.query(System).filter(System.id == point.system_id).first() if point.system_id else None
    point_name = point.point_name or (room.room_name if room else None) or point.location_detail or point.location or point.point_code
    return {
        "point_id": point.id,
        "system_id": point.system_id,
        "system_name": system.name if system else "",
        "point_code": point.point_code,
        "point_name": point_name,
        "location": point.location,
        "room_id": point.room_id,
        "room_name": room.room_name if room else "",
        "location_detail": point.location_detail,
        "check_items": _parse_check_items(getattr(room, "check_items", None)) if room else [],
        "monitoring_confirmation": _monitoring_confirmation(point.room_id),
    }


@router.get("/points/resolve")
def resolve_point_by_qr(qr_content: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    qr_text = (qr_content or "").strip()
    logger.info("解析巡检点: qr_content=%s", qr_text)

    # 管理端配置的机房二维码/NFC 优先级最高，即使值是 "001" 这类纯数字也应按机房解析。
    room = (
        db.query(Room)
        .filter(
            Room.is_active.is_(True),
            (Room.qr_content == qr_text) | (Room.nfc_tag == qr_text),
        )
        .first()
    )
    if room:
        point = (
            db.query(InspectionPoint)
            .filter(InspectionPoint.room_id == room.id, InspectionPoint.is_active.is_(True))
            .order_by(InspectionPoint.id.asc())
            .first()
        )
        if point:
            logger.info("解析机房二维码成功: room_id=%s point_id=%s", room.id, point.id)
            return _serialize_resolved_point(point, db)
        logger.warning("解析机房二维码失败: room_id=%s 未找到巡检点", room.id)
        raise HTTPException(status_code=404, detail="未找到对应机房巡检点")

    # 兼容旧逻辑：二维码为系统ID（纯数字）时，按 system_id 定位系统与巡检点
    if qr_text.isdigit():
        system_id = int(qr_text)
        system = db.query(System).filter(System.id == system_id).first()
        if not system:
            logger.warning("解析巡检点失败: system_id=%s 未找到系统", system_id)
            raise HTTPException(status_code=404, detail="找不到巡检点")

        point = (
            db.query(InspectionPoint)
            .filter(InspectionPoint.system_id == system_id)
            .order_by(InspectionPoint.id.asc())
            .first()
        )
        if not point:
            logger.warning("解析巡检点失败: system_id=%s 未找到巡检点", system_id)
            raise HTTPException(status_code=404, detail="找不到巡检点")

        return _serialize_resolved_point(point, db)

    # 兼容旧逻辑：二维码/NFC 为完整内容
    point = (
        db.query(InspectionPoint)
        .filter(
            InspectionPoint.is_active.is_(True),
            (InspectionPoint.qr_content == qr_text) | (InspectionPoint.nfc_tag == qr_text),
        )
        .first()
    )
    if not point:
        logger.warning("解析巡检点失败: qr_content=%s 未命中", qr_text)
        raise HTTPException(status_code=404, detail="未找到对应巡检点")

    logger.info("解析巡检点成功: point_id=%s system_id=%s", point.id, point.system_id)
    return _serialize_resolved_point(point, db)


@router.get("/rooms/{room_id}/monitoring-confirmation")
def room_monitoring_confirmation(room_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    room = db.query(Room).filter(Room.id == room_id, Room.is_active.is_(True)).first()
    if not room:
        raise HTTPException(status_code=404, detail="机房不存在")
    return _monitoring_confirmation(room_id)


@router.post("/records")
def create_record(
    payload: InspectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("inspector", "admin", "super_admin")),
):
    logger.info("创建巡检记录: user=%s system_id=%s point_id=%s result=%s", current_user.username, payload.system_id, payload.point_id, payload.result)
    point = db.query(InspectionPoint).filter(InspectionPoint.id == payload.point_id).first()
    note_payload = {
        "note": payload.note,
        "check_results": payload.check_results,
        "monitoring_confirmation": payload.monitoring_confirmation,
    }
    note = json.dumps(note_payload, ensure_ascii=False)
    rec = InspectionRecord(
        system_id=payload.system_id,
        point_id=payload.point_id,
        room_id=payload.room_id or (point.room_id if point else None),
        inspector_id=current_user.id,
        result=payload.result,
        note=note,
        source=payload.source,
        inspected_at=payload.inspected_at,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    logger.info("创建巡检记录成功: record_id=%s", rec.id)
    log_action(db, "create_inspection_record", "inspection_record", current_user, {"record_id": rec.id})
    return {"id": rec.id}


@router.get("/records")
def list_records(
    system_id: Optional[int] = None,
    result: Optional[str] = None,
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    logger.info("查询巡检记录: system_id=%s result=%s page=%s size=%s", system_id, result, page, size)
    page = max(page, 1)
    size = min(max(size, 1), 100)

    q = db.query(InspectionRecord)
    if system_id is not None:
        q = q.filter(InspectionRecord.system_id == system_id)
    if result:
        q = q.filter(InspectionRecord.result == result)
    if start_at:
        q = q.filter(InspectionRecord.inspected_at >= start_at)
    if end_at:
        q = q.filter(InspectionRecord.inspected_at <= end_at)

    total = q.count()
    items = q.order_by(InspectionRecord.inspected_at.desc()).offset((page - 1) * size).limit(size).all()
    logger.info("查询巡检记录完成: total=%s returned=%s", total, len(items))
    return {
        "page": page,
        "size": size,
        "total": total,
        "items": [
            {
                "id": i.id,
                "system_id": i.system_id,
                "point_id": i.point_id,
                "inspector_id": i.inspector_id,
                "room_id": i.room_id,
                "result": i.result,
                "note": i.note,
                "source": i.source,
                "inspected_at": i.inspected_at,
            }
            for i in items
        ],
    }
