from __future__ import annotations

from typing import Any, Dict, Optional

import app.db.session as db_session_module
from app.models.system import System, SystemStatusSnapshot
from app.services.assistant.schemas import ToolSpec


def _match_system(db, system_name: Optional[str]):
    q = db.query(System)
    if system_name:
        q = q.filter(System.name.like(f"%{system_name}%"))
    return q.order_by(System.id.asc()).first()


def _query_system_items(db, system_name: Optional[str] = None, limit: int = 5) -> list[dict]:
    if system_name:
        systems = db.query(System).filter(System.name.like(f"%{system_name}%")).limit(limit).all()
    else:
        systems = db.query(System).limit(limit).all()

    items = []
    for system in systems:
        snapshot = (
            db.query(SystemStatusSnapshot)
            .filter(SystemStatusSnapshot.system_id == system.id)
            .order_by(SystemStatusSnapshot.captured_at.desc())
            .first()
        )
        items.append(
            {
                "system_id": system.id,
                "system_name": system.name,
                "system_code": system.system_code,
                "env": system.env,
                "status_color": snapshot.status_color if snapshot else "unknown",
                "captured_at": snapshot.captured_at.isoformat() if snapshot and snapshot.captured_at else None,
            }
        )
    return items


def list_accessible_systems(system_name: Optional[str] = None, limit: int = 20, **_: Any) -> Dict[str, Any]:
    db = db_session_module.SessionLocal()
    try:
        items = _query_system_items(db, system_name=system_name, limit=limit)
        if system_name and not items:
            return {
                "success": False,
                "summary": f"当前未找到名称包含“{system_name}”的已接入系统。",
                "data": {"items": []},
                "cards": [],
                "actions": [],
            }
        if not items:
            return {
                "success": True,
                "summary": "当前还没有接入任何系统监控数据。",
                "data": {"items": []},
                "cards": [
                    {
                        "type": "system_status_overview",
                        "title": "已接入系统",
                        "summary": "当前还没有接入任何系统监控数据。",
                        "items": [],
                    }
                ],
                "actions": [],
            }
        summary = f"当前已接入 {len(items)} 个系统。"
        return {
            "success": True,
            "summary": summary,
            "data": {"items": items},
            "cards": [
                {
                    "type": "system_status_overview",
                    "title": "已接入系统",
                    "summary": summary,
                    "items": items,
                }
            ],
            "actions": [
                {"type": "open_system_detail", "label": "查看首个系统详情", "payload": {"system_id": items[0]["system_id"], "system_name": items[0]["system_name"]}}
            ],
        }
    finally:
        db.close()



def get_system_status_overview(system_name: Optional[str] = None, **_: Any) -> Dict[str, Any]:
    db = db_session_module.SessionLocal()
    try:
        items = _query_system_items(db, system_name=system_name, limit=5)

        if system_name and not items:
            return {"success": False, "summary": f"未找到名称包含“{system_name}”的系统", "data": {"items": []}, "cards": [], "actions": []}

        abnormal = [item for item in items if item["status_color"] in {"yellow", "red"}]
        if system_name and items:
            summary = f"找到 {len(items)} 个匹配系统，异常 {len(abnormal)} 个。"
        else:
            summary = f"当前共找到 {len(items)} 个系统，异常 {len(abnormal)} 个。"
        cards = [
            {
                "type": "system_status_overview",
                "title": "系统状态总览",
                "summary": summary,
                "items": items,
            }
        ]
        actions = []
        if items:
            first = items[0]
            actions.append({"type": "open_system_detail", "label": "查看系统详情", "payload": {"system_id": first["system_id"], "system_name": first["system_name"]}})
        if abnormal:
            actions.append({"type": "open_abnormal_systems", "label": "查看异常系统", "payload": {"count": len(abnormal)}})
        return {"success": True, "summary": summary, "data": {"items": items, "abnormal_items": abnormal}, "cards": cards, "actions": actions}
    finally:
        db.close()


def get_abnormal_systems(**_: Any) -> Dict[str, Any]:
    db = db_session_module.SessionLocal()
    try:
        items = _query_system_items(db, limit=20)
        abnormal = [item for item in items if item["status_color"] in {"yellow", "red"}]
        summary = f"当前异常系统 {len(abnormal)} 个。" if abnormal else "当前没有识别到异常系统。"
        actions = []
        if abnormal:
            actions.append({"type": "open_first_abnormal_system_detail", "label": "查看首个异常系统详情", "payload": {"system_id": abnormal[0]["system_id"], "system_name": abnormal[0]["system_name"]}})
            actions.append({"type": "refresh_abnormal_systems", "label": "刷新异常系统", "payload": {"message": "帮我查今天有哪些异常系统"}})
        else:
            actions.append({"type": "refresh_abnormal_systems", "label": "重新检查异常系统", "payload": {"message": "帮我查今天有哪些异常系统"}})
        return {
            "success": True,
            "summary": summary,
            "data": {"items": abnormal},
            "cards": [{"type": "system_status_overview", "title": "异常系统", "summary": summary, "items": abnormal}],
            "actions": actions,
        }
    finally:
        db.close()


def get_system_detail(system_name: Optional[str] = None, **_: Any) -> Dict[str, Any]:
    db = db_session_module.SessionLocal()
    try:
        system = _match_system(db, system_name)
        if not system:
            return {"success": False, "summary": "未找到目标系统", "data": {}, "cards": [], "actions": []}
        snapshot = (
            db.query(SystemStatusSnapshot)
            .filter(SystemStatusSnapshot.system_id == system.id)
            .order_by(SystemStatusSnapshot.captured_at.desc())
            .first()
        )
        detail = {
            "system_id": system.id,
            "system_name": system.name,
            "system_code": system.system_code,
            "env": system.env,
            "status_snapshot": {
                "status_color": snapshot.status_color if snapshot else "unknown",
                "cpu_usage": snapshot.cpu_usage if snapshot else None,
                "mem_usage": snapshot.mem_usage if snapshot else None,
                "disk_usage": snapshot.disk_usage if snapshot else None,
                "captured_at": snapshot.captured_at.isoformat() if snapshot and snapshot.captured_at else None,
            },
        }
        return {
            "success": True,
            "summary": f"系统 {system.name} 详情已获取",
            "data": detail,
            "cards": [{"type": "system_detail", "title": system.name, "detail": detail}],
            "actions": [
                {"type": "open_inspection_records", "label": "查看巡检记录", "payload": {"system_id": system.id, "system_name": system.name}},
                {"type": "open_selfcheck_records", "label": "查看自检记录", "payload": {"system_id": system.id, "system_name": system.name}},
            ],
        }
    finally:
        db.close()


def register_system_tools(registry) -> None:
    registry.register(ToolSpec(name="list_accessible_systems", description="查询当前已接入的系统列表", handler=list_accessible_systems))
    registry.register(ToolSpec(name="get_system_status_overview", description="查询系统状态总览", handler=get_system_status_overview))
    registry.register(ToolSpec(name="get_abnormal_systems", description="查询异常系统", handler=get_abnormal_systems))
    registry.register(ToolSpec(name="get_system_detail", description="查询系统详情", handler=get_system_detail))
