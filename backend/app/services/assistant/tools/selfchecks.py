from __future__ import annotations

from typing import Any, Dict, Optional

from app.db.session import SessionLocal
from app.models.selfcheck import SelfcheckRecord
from app.models.system import System
from app.services.assistant.schemas import ToolSpec


def list_selfcheck_records(system_name: Optional[str] = None, **_: Any) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        q = db.query(SelfcheckRecord)
        matched_system = None
        if system_name:
            matched_system = db.query(System).filter(System.name.like(f"%{system_name}%")).order_by(System.id.asc()).first()
            if not matched_system:
                return {"success": False, "summary": f"未找到名称包含“{system_name}”的系统", "data": {"items": []}, "cards": [], "actions": []}
            q = q.filter(SelfcheckRecord.system_id == matched_system.id)

        items = q.order_by(SelfcheckRecord.checked_at.desc()).limit(5).all()
        summary = (
            f"系统 {matched_system.name} 最近自检记录 {len(items)} 条"
            if matched_system
            else f"最近自检记录 {len(items)} 条"
        )
        payload_items = [
            {
                "id": item.id,
                "system_id": item.system_id,
                "template_id": item.template_id,
                "result": item.result,
                "summary": item.summary,
                "checked_at": item.checked_at.isoformat(),
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
            "cards": [{"type": "selfcheck_records", "title": "自检记录", "items": payload_items}],
            "actions": [{"type": "refresh_selfcheck_records", "label": "刷新自检记录", "payload": {"message": f"看看{matched_system.name}最近自检记录" if matched_system else "看看最近自检记录"}}],
        }
    finally:
        db.close()


def register_selfcheck_tools(registry) -> None:
    registry.register(ToolSpec(name="list_selfcheck_records", description="查询自检记录", handler=list_selfcheck_records))
