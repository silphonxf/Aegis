from __future__ import annotations

import json
from typing import Any, Dict, Optional

from app.db.session import SessionLocal
from app.models.system import System
from app.models.tool_task import ToolTask
from app.services.assistant.schemas import ToolSpec


def create_restart_approval(system_name: Optional[str] = None, **_: Any) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        target = system_name or "local-host"
        if system_name:
            matched_system = db.query(System).filter(System.name.like(f"%{system_name}%")).order_by(System.id.asc()).first()
            if matched_system:
                target = matched_system.name

        task = ToolTask(
            action="restart",
            target=target,
            status="pending_approval",
            result=json.dumps(
                {
                    "reason": "assistant request",
                    "note": None,
                    "executor": "assistant",
                    "started_at": None,
                    "finished_at": None,
                    "success": None,
                    "error": None,
                },
                ensure_ascii=False,
            ),
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        data = {"task_id": task.id, "status": task.status, "target": target}
        return {
            "success": True,
            "summary": f"已为 {target} 创建重启审批任务，当前状态：{task.status}。",
            "data": data,
            "cards": [{"type": "tool_task", "title": "重启审批任务", "detail": data}],
            "actions": [{"type": "view_tool_task", "label": "查看任务详情", "payload": {"task_id": task.id}}],
        }
    finally:
        db.close()


def register_toolbox_tools(registry) -> None:
    registry.register(
        ToolSpec(
            name="create_restart_approval",
            description="发起重启审批",
            handler=create_restart_approval,
            risk_level="high",
            requires_confirmation=True,
        )
    )
