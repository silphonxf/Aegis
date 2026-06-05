from __future__ import annotations

from typing import Any, Dict, Optional

import app.db.session as db_session_module
from app.models.inspection import InspectionRecord
from app.models.system import System
from app.services.assistant.schemas import ToolSpec


def list_inspection_records(system_name: Optional[str] = None, **_: Any) -> Dict[str, Any]:
    db = db_session_module.SessionLocal()
    try:
        q = db.query(InspectionRecord)
        matched_system = None
        if system_name:
            matched_system = db.query(System).filter(System.name.like(f"%{system_name}%")).order_by(System.id.asc()).first()
            if not matched_system:
                return {"success": False, "summary": f"未找到名称包含“{system_name}”的系统", "data": {"items": []}, "cards": [], "actions": []}
            q = q.filter(InspectionRecord.system_id == matched_system.id)

        items = q.order_by(InspectionRecord.inspected_at.desc()).limit(5).all()
        summary = (
            f"系统 {matched_system.name} 最近巡检记录 {len(items)} 条"
            if matched_system
            else f"最近巡检记录 {len(items)} 条"
        )
        payload_items = [
            {
                "id": item.id,
                "system_id": item.system_id,
                "point_id": item.point_id,
                "result": item.result,
                "note": item.note,
                "inspected_at": item.inspected_at.isoformat(),
            }
            for item in items
        ]
        return {
            "success": True,
            "summary": summary,
            "data": {
                "system_name": matched_system.name if matched_system else None,
                "items": payload_items,
            },
            "cards": [{"type": "inspection_records", "title": "巡检记录", "items": payload_items}],
            "actions": [{"type": "refresh_inspection_records", "label": "刷新巡检记录", "payload": {"message": f"看看{matched_system.name}最近巡检记录" if matched_system else "看看最近巡检记录"}}],
        }
    finally:
        db.close()


def register_inspection_tools(registry) -> None:
    registry.register(ToolSpec(name="list_inspection_records", description="查询巡检记录", handler=list_inspection_records))
