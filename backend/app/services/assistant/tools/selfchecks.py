from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from app.api.selfchecks import _build_alarm_items, _build_selfcheck_prompt, _snapshot_payload
import app.db.session as db_session_module
from app.models.selfcheck import SelfcheckRecord
from app.models.system import System, SystemStatusSnapshot
from app.schemas.ai import ChatRequest
from app.services.ai_provider import run_chat
from app.services.assistant.schemas import ToolSpec


def _find_system(db, system_name: Optional[str] = None, system_id: Optional[int] = None) -> Optional[System]:
    q = db.query(System).filter(System.is_active.is_(True))
    if system_id:
        return q.filter(System.id == system_id).order_by(System.id.asc()).first()
    if system_name:
        matched = q.filter(System.name.like(f"%{system_name}%")).order_by(System.id.asc()).first()
        if matched:
            return matched
        candidates = q.order_by(System.id.asc()).limit(200).all()
        for item in candidates:
            if item.name and item.name in system_name:
                return item
            if system_name in (item.name or ""):
                return item
    return q.order_by(System.id.asc()).first()


def list_selfcheck_records(system_name: Optional[str] = None, **_: Any) -> Dict[str, Any]:
    db = db_session_module.SessionLocal()
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


def run_system_selfcheck_report(system_name: Optional[str] = None, system_id: Optional[int] = None, range_minutes: int = 60, **_: Any) -> Dict[str, Any]:
    db = db_session_module.SessionLocal()
    try:
      range_minutes = min(max(int(range_minutes or 60), 1), 360)
      system = _find_system(db, system_name=system_name, system_id=system_id)
      if not system:
          return {"success": False, "summary": "未找到可自检的系统。", "data": {}, "cards": [], "actions": []}

      if not (getattr(system, "selfcheck_skill", None) or "").strip():
          return {
              "success": True,
              "summary": f"系统 {system.name} 暂未配置ai自检项目。",
              "data": {"system_id": system.id, "system_name": system.name, "ai_report": None},
              "cards": [{"type": "selfcheck_records", "title": "智能自检", "summary": "暂未配置ai自检项目", "items": [{"label": "系统", "value": system.name}]}],
              "actions": [],
          }

      host = (system.host_address or "").strip()
      related_systems = [system]
      if host:
          related_systems = db.query(System).filter(System.is_active.is_(True), System.host_address == host).order_by(System.id.asc()).all() or [system]
      related_ids = [item.id for item in related_systems]
      since = datetime.utcnow() - timedelta(minutes=range_minutes)
      snapshots = (
          db.query(SystemStatusSnapshot)
          .filter(SystemStatusSnapshot.system_id.in_(related_ids), SystemStatusSnapshot.captured_at >= since)
          .order_by(SystemStatusSnapshot.captured_at.desc())
          .limit(500)
          .all()
      )
      latest = snapshots[0] if snapshots else (
          db.query(SystemStatusSnapshot)
          .filter(SystemStatusSnapshot.system_id.in_(related_ids))
          .order_by(SystemStatusSnapshot.captured_at.desc())
          .first()
      )
      alarms = _build_alarm_items(snapshots)
      prompt = _build_selfcheck_prompt(system, range_minutes, latest, alarms)
      report = run_chat(ChatRequest(message=prompt, conversation_id=f"assistant-selfcheck-{system.id}"))
      reply = report.get("reply") or report.get("summary") or "已完成智能自检。"
      html = _build_selfcheck_html(system, range_minutes, latest, alarms, reply)
      return {
          "success": True,
          "summary": f"系统 {system.name} 智能自检完成。",
          "data": {
              "system_id": system.id,
              "system_name": system.name,
              "status": _snapshot_payload(latest) if latest else None,
              "alarms": alarms,
              "ai_report": report,
          },
          "cards": [
              {
                  "type": "system_selfcheck_report",
                  "title": f"{system.name} 智能自检",
                  "summary": reply[:240],
                  "html_report": html,
                  "items": [
                      {"label": "系统", "value": system.name},
                      {"label": "IP / 地址", "value": system.host_address or "-"},
                      {"label": "时间范围", "value": f"{range_minutes} 分钟"},
                      {"label": "告警数量", "value": str(len(alarms))},
                  ],
              }
          ],
          "actions": [],
      }
    finally:
        db.close()


def _escape_html(value: object) -> str:
    return str(value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")


def _build_selfcheck_html(system: System, range_minutes: int, latest: Optional[SystemStatusSnapshot], alarms: list[dict], report: str) -> str:
    latest_rows = ""
    if latest:
        latest_rows = "".join([
            f"<tr><th>状态</th><td>{_escape_html(latest.status_color)}</td></tr>",
            f"<tr><th>CPU</th><td>{_escape_html(latest.cpu_usage)}%</td></tr>",
            f"<tr><th>内存</th><td>{_escape_html(latest.mem_usage)}%</td></tr>",
            f"<tr><th>硬盘</th><td>{_escape_html(latest.disk_usage)}%</td></tr>",
            f"<tr><th>采集时间</th><td>{_escape_html(latest.captured_at)}</td></tr>",
        ])
    else:
        latest_rows = "<tr><td colspan=\"2\">暂无状态快照</td></tr>"
    alarm_rows = "".join(
        f"<li><strong>{_escape_html(item.get('captured_at'))}</strong>：{_escape_html('，'.join(item.get('reasons') or []))}</li>"
        for item in alarms
    ) or "<li>当前时间范围内暂无告警。</li>"
    return f"""<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{_escape_html(system.name)} 智能自检报告</title>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:0;background:#f5f7fb;color:#162b3f}}main{{max-width:960px;margin:0 auto;padding:24px}}section{{background:#fff;border:1px solid #dce6f0;border-radius:12px;padding:18px;margin:14px 0}}h1{{margin:0 0 8px}}table{{width:100%;border-collapse:collapse}}th,td{{border-bottom:1px solid #edf2f7;text-align:left;padding:10px}}pre{{white-space:pre-wrap;line-height:1.7}}</style></head>
<body><main><h1>{_escape_html(system.name)} 智能自检报告</h1><p>系统编码：{_escape_html(system.system_code)} · 地址：{_escape_html(system.host_address or '-')} · 范围：最近 {range_minutes} 分钟</p>
<section><h2>系统状态</h2><table>{latest_rows}</table></section>
<section><h2>告警信息</h2><ul>{alarm_rows}</ul></section>
<section><h2>AI 分析报告</h2><pre>{_escape_html(report)}</pre></section></main></body></html>"""


def register_selfcheck_tools(registry) -> None:
    registry.register(ToolSpec(name="list_selfcheck_records", description="查询自检记录", handler=list_selfcheck_records))
    registry.register(ToolSpec(name="run_system_selfcheck_report", description="调用管理端配置的自检 skill 生成系统智能自检报告", handler=run_system_selfcheck_report))
