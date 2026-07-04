from typing import Any, Dict, List, Optional, Set, Tuple
import json
import re
from pathlib import Path
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.selfcheck import ChecklistTemplate, SelfcheckRecord, SelfcheckReport
from app.models.system import System, SystemStatusSnapshot, SystemUserBinding
from app.models.user import User
from app.schemas.ai import ChatRequest
from app.schemas.selfcheck import SelfcheckRecordCreate, SelfcheckRecordSimpleCreate, SelfcheckTemplateCreate
from app.services.audit import log_action
from app.services.ai_provider import run_chat
from app.services.openclaw_client import OpenClawClientError, openclaw_client

router = APIRouter(prefix="/selfchecks", tags=["selfchecks"])
logger = get_logger("selfchecks")

REPORT_DIR = Path(__file__).resolve().parents[2] / "selfcheck_reports"
REPORT_RETENTION_DAYS = 7
DEFAULT_REPORT_LOOKBACK_HOURS = 6
EAST8_OFFSET = timedelta(hours=8)


def _safe_file_part(value: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z._-]+", "-", (value or "").strip())
    return cleaned.strip(".-_") or "system"


def _east8_now() -> datetime:
    return datetime.utcnow() + EAST8_OFFSET


def _format_east8(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.replace(microsecond=0).isoformat() + "+08:00"


def _cleanup_old_reports(now: Optional[datetime] = None) -> int:
    now = now or datetime.utcnow()
    cutoff = now - timedelta(days=REPORT_RETENTION_DAYS)
    if not REPORT_DIR.exists():
        return 0
    deleted = 0
    for path in REPORT_DIR.glob("*.json"):
        try:
            if datetime.utcfromtimestamp(path.stat().st_mtime) < cutoff:
                path.unlink()
                deleted += 1
        except OSError:
            logger.warning("清理过期 AI 自检报告失败: path=%s", path)
    return deleted


def _serialize_report_file(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    checked_at = data.get("checked_at")
    if not checked_at:
        checked_at = datetime.utcfromtimestamp(path.stat().st_mtime).isoformat()
    system = data.get("system") or {}
    ai_report = data.get("ai_report") or {}
    return {
        "file_name": path.name,
        "file_path": str(path),
        "system_id": system.get("system_id"),
        "system_code": system.get("system_code"),
        "system_name": system.get("system_name"),
        "checked_at": checked_at,
        "range_minutes": data.get("range_minutes"),
        "alarm_count": len(data.get("alarms") or []),
        "summary": data.get("summary") or ai_report.get("summary") or ai_report.get("reply"),
    }


def _report_identifier(report_id: int) -> str:
    return f"report-{report_id}.json"


def _serialize_report_row(row: SelfcheckReport) -> Dict[str, Any]:
    return {
        "id": row.id,
        "file_name": _report_identifier(row.id),
        "file_path": None,
        "storage": "database",
        "system_id": row.system_id,
        "system_code": row.system_code,
        "system_name": row.system_name,
        "checked_at": _format_east8(row.checked_at),
        "range_minutes": row.range_minutes,
        "alarm_count": row.alarm_count,
        "summary": row.summary,
    }


def _save_selfcheck_report(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    checked_at = _east8_now()
    system = payload.get("system") or {}
    report = dict(payload)
    report["checked_at"] = _format_east8(checked_at)
    report["summary"] = (payload.get("ai_report") or {}).get("reply") or (payload.get("ai_report") or {}).get("summary") or ""
    row = SelfcheckReport(
        system_id=system.get("system_id"),
        system_code=system.get("system_code"),
        system_name=system.get("system_name"),
        range_minutes=payload.get("range_minutes"),
        alarm_count=len(payload.get("alarms") or []),
        summary=report["summary"],
        payload_json=json.dumps(report, ensure_ascii=False, default=str),
        checked_at=checked_at,
    )
    db.add(row)
    db.flush()
    return _serialize_report_row(row)


def _list_report_rows(db: Session, system_id: Optional[int], start_at: Optional[datetime], end_at: Optional[datetime]) -> List[Dict[str, Any]]:
    q = db.query(SelfcheckReport)
    if system_id is not None:
        q = q.filter(SelfcheckReport.system_id == system_id)
    if start_at:
        q = q.filter(SelfcheckReport.checked_at >= start_at)
    if end_at:
        q = q.filter(SelfcheckReport.checked_at <= end_at)
    rows = q.order_by(SelfcheckReport.checked_at.desc(), SelfcheckReport.id.desc()).all()
    return [_serialize_report_row(row) for row in rows]


def _list_report_files(system_id: Optional[int], start_at: Optional[datetime], end_at: Optional[datetime]) -> List[Dict[str, Any]]:
    _cleanup_old_reports()
    if not REPORT_DIR.exists():
        return []
    rows = []
    for path in REPORT_DIR.glob("*.json"):
        item = _serialize_report_file(path)
        checked_at_raw = item.get("checked_at")
        try:
            checked_at = datetime.fromisoformat(str(checked_at_raw).replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            checked_at = datetime.utcfromtimestamp(path.stat().st_mtime)
        if system_id is not None and item.get("system_id") != system_id:
            continue
        if start_at and checked_at < start_at.replace(tzinfo=None):
            continue
        if end_at and checked_at > end_at.replace(tzinfo=None):
            continue
        rows.append(item)
    return sorted(rows, key=lambda item: str(item.get("checked_at") or ""), reverse=True)


def _load_report_payload(file_name: str) -> Dict[str, Any]:
    if Path(file_name).name != file_name or not file_name.endswith(".json"):
        raise HTTPException(status_code=400, detail={"code": "INVALID_REPORT_FILE", "message": "报告文件名非法"})
    path = REPORT_DIR / file_name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail={"code": "REPORT_NOT_FOUND", "message": "AI 自检报告不存在或已过期"})
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("读取 AI 自检报告失败: path=%s error=%s", path, exc)
        raise HTTPException(status_code=500, detail={"code": "REPORT_READ_FAILED", "message": "AI 自检报告读取失败"}) from exc
    data["report_file"] = _serialize_report_file(path)
    data["alarm_count"] = len(data.get("alarms") or [])
    return data


def _load_report_row_payload(db: Session, file_name: str) -> Dict[str, Any]:
    match = re.fullmatch(r"(?:report-)?(\d+)(?:\.json)?", file_name or "")
    if not match:
        raise HTTPException(status_code=400, detail={"code": "INVALID_REPORT_FILE", "message": "报告标识非法"})
    row = db.query(SelfcheckReport).filter(SelfcheckReport.id == int(match.group(1))).first()
    if not row:
        raise HTTPException(status_code=404, detail={"code": "REPORT_NOT_FOUND", "message": "AI 自检报告不存在"})
    try:
        data = json.loads(row.payload_json)
    except Exception as exc:
        logger.warning("读取数据库 AI 自检报告失败: report_id=%s error=%s", row.id, exc)
        raise HTTPException(status_code=500, detail={"code": "REPORT_READ_FAILED", "message": "AI 自检报告读取失败"}) from exc
    data["report_file"] = _serialize_report_row(row)
    data["alarm_count"] = len(data.get("alarms") or [])
    return data


def _visible_system_query(db: Session, user: User):
    q = db.query(System).filter(System.is_active.is_(True))
    if user.role.code in {"admin", "super_admin"}:
        return q
    return q.join(SystemUserBinding, SystemUserBinding.system_id == System.id).filter(
        SystemUserBinding.binding_role == "owner",
        SystemUserBinding.user_id == user.id,
    )


def _snapshot_payload(item: SystemStatusSnapshot) -> Dict[str, Any]:
    return {
        "id": item.id,
        "system_id": item.system_id,
        "host_online": item.host_online,
        "port_ok": item.port_ok,
        "cpu_usage": item.cpu_usage,
        "mem_usage": item.mem_usage,
        "disk_usage": item.disk_usage,
        "cpu_level": item.cpu_level,
        "mem_level": item.mem_level,
        "disk_level": item.disk_level,
        "status_color": item.status_color,
        "captured_at": item.captured_at,
    }


def _build_alarm_items(snapshots: List[SystemStatusSnapshot]) -> List[Dict[str, Any]]:
    alarms = []
    for snap in snapshots:
        reasons = []
        if snap.status_color in {"yellow", "red"}:
            reasons.append(f"状态 {snap.status_color}")
        for label, usage, level in [
            ("CPU", snap.cpu_usage, snap.cpu_level),
            ("内存", snap.mem_usage, snap.mem_level),
            ("硬盘", snap.disk_usage, snap.disk_level),
        ]:
            if level in {"warning", "critical"}:
                reasons.append(f"{label} {usage if usage is not None else '-'}% / {level}")
        if snap.host_online == "abnormal":
            reasons.append("主机不可达")
        if snap.port_ok == "abnormal":
            reasons.append("端口异常")
        if reasons:
            alarms.append({
                "snapshot_id": snap.id,
                "system_id": snap.system_id,
                "captured_at": snap.captured_at,
                "status_color": snap.status_color,
                "reasons": reasons,
            })
    return alarms


def _build_selfcheck_prompt(system: System, range_minutes: int, latest: Optional[SystemStatusSnapshot], alarms: List[Dict[str, Any]]) -> str:
    skill = (getattr(system, "selfcheck_skill", None) or "").strip()
    if not skill:
        skill = "请按 CPU、内存、硬盘、主机在线、端口状态和告警信息进行系统自检，输出结论、风险等级、原因和处理建议。"
    latest_text = "暂无状态快照"
    if latest:
        latest_text = (
            f"状态={latest.status_color}; CPU={latest.cpu_usage}%; 内存={latest.mem_usage}%; 硬盘={latest.disk_usage}%; "
            f"CPU级别={latest.cpu_level}; 内存级别={latest.mem_level}; 硬盘级别={latest.disk_level}; "
            f"主机={latest.host_online}; 端口={latest.port_ok}; 采集时间={latest.captured_at}"
        )
    alarm_text = "\n".join(
        f"- {item['captured_at']} system_id={item['system_id']} {', '.join(item['reasons'])}"
        for item in alarms[:20]
    ) or "当前时间范围内未发现告警。"
    return (
        "你是 Aegis 系统自检助手。请严格根据管理端配置的自检 skill、系统状态和告警信息生成自检报告。\n"
        "报告请包含：总体结论、风险等级、关键指标、告警判断、处理建议。\n\n"
        f"系统：{system.name}（{system.system_code}）\n"
        f"系统IP/地址：{system.host_address or '未配置'}\n"
        f"环境：{system.env}\n"
        f"时间范围：最近 {range_minutes} 分钟\n\n"
        f"管理端自检 skill：\n{skill[:1200]}\n\n"
        f"最新系统状态：\n{latest_text}\n\n"
        f"告警信息：\n{alarm_text}"
    )


def _metric_text(label: str, usage: Optional[int], level: str) -> str:
    usage_text = f"{usage}%" if usage is not None else "暂无数据"
    return f"{label}: {usage_text} / {level or 'unknown'}"


def _build_local_selfcheck_report(
    system: System,
    range_minutes: int,
    latest: Optional[SystemStatusSnapshot],
    alarms: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if latest:
        status_color = latest.status_color or "unknown"
        severity = "high" if status_color == "red" else "medium" if status_color == "yellow" or alarms else "low"
        conclusion = "异常" if severity == "high" else "需关注" if severity == "medium" else "正常"
        metrics = [
            _metric_text("CPU", latest.cpu_usage, latest.cpu_level),
            _metric_text("内存", latest.mem_usage, latest.mem_level),
            _metric_text("硬盘", latest.disk_usage, latest.disk_level),
            f"主机在线: {latest.host_online or 'unknown'}",
            f"端口状态: {latest.port_ok or 'unknown'}",
            f"采集时间: {latest.captured_at}",
        ]
    else:
        severity = "medium"
        conclusion = "需关注"
        metrics = ["暂无状态快照，无法完成指标判定。"]

    alarm_lines = [
        f"- {item.get('captured_at')}: {'; '.join(item.get('reasons') or [])}"
        for item in alarms[:20]
    ]
    if not alarm_lines:
        alarm_lines = ["- 当前时间范围内未发现告警。"]

    suggestions = []
    if not latest:
        suggestions.append("先确认系统状态采集任务是否正常运行，并补采最新快照。")
    if alarms:
        suggestions.append("优先处理告警项，并按采集时间倒序确认异常是否仍在持续。")
    if latest and latest.host_online == "abnormal":
        suggestions.append("检查主机网络连通性、DNS/路由、防火墙策略和主机存活状态。")
    if latest and latest.port_ok == "abnormal":
        suggestions.append("检查业务端口监听、服务进程状态和安全组/防火墙放行策略。")
    if latest and latest.cpu_level in {"warning", "critical"}:
        suggestions.append("定位 CPU 高占用进程，关联发布、批处理或异常请求峰值。")
    if latest and latest.mem_level in {"warning", "critical"}:
        suggestions.append("检查内存泄漏、缓存膨胀和进程重启策略。")
    if latest and latest.disk_level in {"warning", "critical"}:
        suggestions.append("清理日志与临时文件，确认磁盘扩容和日志轮转策略。")
    if not suggestions:
        suggestions.append("保持当前巡检频率，继续观察 CPU、内存、硬盘、主机和端口状态。")

    skill = (getattr(system, "selfcheck_skill", None) or "").strip()
    reply = "\n".join([
        f"总体结论：{system.name} 最近 {range_minutes} 分钟自检{conclusion}。",
        f"风险等级：{severity}",
        "",
        "关键指标：",
        *[f"- {item}" for item in metrics],
        "",
        "告警判断：",
        *alarm_lines,
        "",
        "处理建议：",
        *[f"{idx + 1}. {item}" for idx, item in enumerate(suggestions)],
        "",
        f"自检依据：{skill[:200] if skill else '系统状态快照与告警信息'}",
    ])
    return {
        "conversation_id": f"selfcheck-{system.id}",
        "mode": "selfcheck_local",
        "summary": f"{system.name} 自检{conclusion}，风险等级 {severity}。",
        "reply": reply,
        "severity": severity,
        "suggestions": suggestions,
        "attachment_notes": [],
        "fallback_reason": None,
    }


def _normalize_selfcheck_report(
    report: Optional[Dict[str, Any]],
    system: System,
    range_minutes: int,
    latest: Optional[SystemStatusSnapshot],
    alarms: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if report and report.get("mode") != "rule_fallback":
        return report
    return _build_local_selfcheck_report(system, range_minutes, latest, alarms)


def _is_mysql_selfcheck(system: System) -> bool:
    text = f"{system.name or ''}\n{system.system_code or ''}\n{getattr(system, 'selfcheck_skill', None) or ''}".lower()
    return "mysql" in text or "mariadb" in text


def _extract_first(patterns: List[str], text: str) -> Optional[str]:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            value = (match.group(1) or "").strip().strip("，,;；。")
            if value:
                return value
    return None


def _extract_mysql_config(system: System) -> Dict[str, Any]:
    skill = (getattr(system, "selfcheck_skill", None) or "").strip()
    host = _extract_first([r"(?:host|主机|地址|ip)\s*[=:：]\s*([0-9A-Za-z_.-]+)"], skill) or (system.host_address or "127.0.0.1")
    port_raw = _extract_first([r"(?:port|端口)\s*[=:：]\s*(\d+)"], skill)
    database = _extract_first([
        r"mysql\s*数据库\s*(?:是|为|名为|名称为)?\s*([0-9A-Za-z_$.-]+)\s*(?:用户|用户名|user)",
        r"(?:database|dbname|db|库名|数据库名|数据库)\s*[=:：]\s*([0-9A-Za-z_$.-]+)",
    ], skill)
    user = _extract_first([
        r"(?:用户名|用户|user|username)\s*[=:：]?\s*([^\s，,;；]+)",
    ], skill)
    password = _extract_first([
        r"(?:密码|口令|password|passwd|pwd)\s*[=:：]?\s*([^\s，,;；]+)",
    ], skill)
    return {
        "host": host,
        "port": int(port_raw or 3306),
        "database": database,
        "user": user,
        "password": password,
    }


def _redact_mysql_skill(skill: str) -> str:
    return _redact_secret_text(skill)[:1200]


def _redact_secret_text(value: str) -> str:
    redacted = re.sub(r"((?:密码|口令|password|passwd|pwd)\s*[=:：]?\s*)([^\s，,;；]+)", r"\1******", value, flags=re.I)
    redacted = re.sub(r"((?:identified\s+by|password)\s+['\"])([^'\"]+)(['\"])", r"\1******\3", redacted, flags=re.I)
    return redacted


def _redact_collected_status(value: Any) -> Any:
    if isinstance(value, str):
        return _redact_secret_text(value)
    if isinstance(value, list):
        return [_redact_collected_status(item) for item in value]
    if isinstance(value, dict):
        return {key: _redact_collected_status(item) for key, item in value.items()}
    return value


def _mysql_query(cursor: Any, sql: str) -> Any:
    try:
        cursor.execute(sql)
        return cursor.fetchall()
    except Exception as exc:
        return {"error": str(exc)[:300]}


def _collect_mysql_status(system: System) -> Dict[str, Any]:
    try:
        import pymysql
        from pymysql.cursors import DictCursor
    except Exception as exc:
        return {"ok": False, "error": f"后端缺少 pymysql，无法连接 MySQL: {exc}"}

    config = _extract_mysql_config(system)
    if not config.get("user") or not config.get("password"):
        return {
            "ok": False,
            "error": "自检 skill 中未解析到 MySQL 用户名或密码，无法采集数据库状态。",
            "target": {"host": config["host"], "port": config["port"], "database": config.get("database")},
        }

    target = {"host": config["host"], "port": config["port"], "database": config.get("database"), "user": config.get("user")}
    try:
        conn = pymysql.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database=config.get("database") or None,
            charset="utf8mb4",
            cursorclass=DictCursor,
            connect_timeout=5,
            read_timeout=8,
            write_timeout=8,
        )
    except Exception as exc:
        return {"ok": False, "error": f"MySQL 连接失败: {exc}", "target": target}

    try:
        with conn.cursor() as cursor:
            status_names = ",".join(
                repr(item)
                for item in [
                    "Threads_connected",
                    "Threads_running",
                    "Max_used_connections",
                    "Connections",
                    "Aborted_connects",
                    "Connection_errors_max_connections",
                    "Innodb_row_lock_current_waits",
                    "Innodb_row_lock_time",
                    "Innodb_row_lock_waits",
                    "Innodb_deadlocks",
                    "Table_locks_waited",
                ]
            )
            variable_names = ",".join(
                repr(item)
                for item in ["max_connections", "version", "version_comment", "transaction_isolation", "tx_isolation", "innodb_lock_wait_timeout"]
            )
            raw_status = _mysql_query(cursor, f"SHOW GLOBAL STATUS WHERE Variable_name IN ({status_names})")
            raw_variables = _mysql_query(cursor, f"SHOW VARIABLES WHERE Variable_name IN ({variable_names})")
            process_summary = _mysql_query(
                cursor,
                "SELECT COUNT(*) AS total, "
                "SUM(CASE WHEN COMMAND = 'Sleep' THEN 1 ELSE 0 END) AS sleeping, "
                "SUM(CASE WHEN COMMAND <> 'Sleep' THEN 1 ELSE 0 END) AS active "
                "FROM information_schema.PROCESSLIST",
            )
            processlist = _mysql_query(
                cursor,
                "SELECT ID, USER, HOST, DB, COMMAND, TIME, STATE, LEFT(INFO, 500) AS INFO "
                "FROM information_schema.PROCESSLIST ORDER BY TIME DESC LIMIT 20",
            )
            innodb_status = _mysql_query(cursor, "SHOW ENGINE INNODB STATUS")
            lock_waits = _mysql_query(cursor, "SELECT * FROM information_schema.INNODB_LOCK_WAITS LIMIT 20")
            data_lock_waits = _mysql_query(cursor, "SELECT * FROM performance_schema.data_lock_waits LIMIT 20")
    finally:
        conn.close()

    return _redact_collected_status({
        "ok": True,
        "target": target,
        "global_status": raw_status,
        "variables": raw_variables,
        "process_summary": process_summary,
        "processlist": processlist,
        "innodb_status": _extract_innodb_status_excerpt(innodb_status),
        "innodb_lock_waits": lock_waits,
        "performance_schema_data_lock_waits": data_lock_waits,
    })


def _extract_innodb_status_excerpt(raw_status: Any) -> Dict[str, Any]:
    if isinstance(raw_status, dict) and raw_status.get("error"):
        return raw_status
    text = ""
    if isinstance(raw_status, list) and raw_status:
        row = raw_status[0]
        if isinstance(row, dict):
            text = str(row.get("Status") or "")
    latest_deadlock = ""
    marker = "LATEST DETECTED DEADLOCK"
    if marker in text:
        latest_deadlock = text[text.find(marker): text.find("------------", text.find(marker) + len(marker))]
        latest_deadlock = latest_deadlock.strip()[:3000]
    transactions = ""
    trx_marker = "TRANSACTIONS"
    if trx_marker in text:
        transactions = text[text.find(trx_marker): text.find("FILE I/O", text.find(trx_marker))]
        transactions = transactions.strip()[:3000]
    return {
        "latest_detected_deadlock": latest_deadlock or "未在 SHOW ENGINE INNODB STATUS 中发现最近死锁片段。",
        "transactions_excerpt": transactions,
    }


def _mysql_selfcheck_prompt(system: System, mysql_status: Dict[str, Any]) -> str:
    skill = _redact_mysql_skill((getattr(system, "selfcheck_skill", None) or "").strip())
    payload = json.dumps(mysql_status, ensure_ascii=False, default=str, indent=2)[:12000]
    return (
        "你是 Aegis 的 MySQL 数据库自检助手。请只根据管理端自检 skill 和后端实际采集到的 MySQL 运行状态分析数据库健康度，"
        "不要分析主机 CPU、内存、硬盘等硬件指标。\n"
        "重点判断：当前连接数、连接池/连接上限风险、Threads_running、连接错误、锁等待、最近死锁、长时间运行 SQL 或异常状态。\n"
        "请输出中文报告，包含：总体结论、风险等级、关键数据库指标、死锁/锁等待判断、连接池判断、处理建议。\n\n"
        f"系统：{system.name}（{system.system_code}）\n"
        f"系统地址：{system.host_address or '未配置'}\n"
        f"环境：{system.env}\n\n"
        f"管理端自检 skill（已脱敏）：\n{skill}\n\n"
        f"MySQL 采集结果：\n{payload}"
    )


def _build_mysql_collection_report(system: System, mysql_status: Dict[str, Any]) -> Dict[str, Any]:
    if mysql_status.get("ok"):
        summary = "已采集 MySQL 状态，但 OpenClaw 未配置或调用失败，未生成 AI 分析。"
        reply = (
            f"总体结论：{summary}\n\n"
            f"MySQL 目标：{json.dumps(mysql_status.get('target') or {}, ensure_ascii=False)}\n\n"
            f"采集结果：\n{json.dumps(mysql_status, ensure_ascii=False, default=str, indent=2)[:6000]}"
        )
        severity = "medium"
    else:
        summary = "MySQL 状态采集失败。"
        reply = f"总体结论：{summary}\n\n原因：{mysql_status.get('error') or '未知错误'}"
        severity = "high"
    return {
        "conversation_id": f"selfcheck-mysql-{system.id}",
        "mode": "mysql_status_collected",
        "summary": summary,
        "reply": reply,
        "severity": severity,
        "suggestions": ["检查 MySQL 连接配置和 OpenClaw 配置后重新执行数据库自检。"],
        "mysql_status": mysql_status,
        "fallback_reason": "openclaw_not_configured_or_failed",
    }


def _run_mysql_selfcheck_report(system: System) -> Dict[str, Any]:
    mysql_status = _collect_mysql_status(system)
    if openclaw_client.is_configured():
        try:
            report = openclaw_client.chat(
                message=_mysql_selfcheck_prompt(system, mysql_status),
                conversation_id=f"selfcheck-mysql-{system.id}",
            )
            report["mode"] = "openclaw_mysql_selfcheck"
            report["mysql_status"] = mysql_status
            report["fallback_reason"] = None
            return report
        except OpenClawClientError as exc:
            report = _build_mysql_collection_report(system, mysql_status)
            report["fallback_reason"] = str(exc)[:200]
            return report
    return _build_mysql_collection_report(system, mysql_status)


def _build_selfcheck_status_payload(db: Session, current_user: User, system_id: int, range_minutes: int) -> Dict[str, Any]:
    range_minutes = min(max(range_minutes, 1), 360)
    system = _visible_system_query(db, current_user).filter(System.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail={"code": "SYSTEM_NOT_FOUND", "message": "系统不存在或无权访问"})

    host = (system.host_address or "").strip()
    related_systems = [system]
    if host:
        related_systems = (
            _visible_system_query(db, current_user)
            .filter(System.host_address == host)
            .order_by(System.id.asc())
            .all()
        ) or [system]
    related_ids = [item.id for item in related_systems]
    since = datetime.utcnow() - timedelta(minutes=range_minutes)
    snapshots = (
        db.query(SystemStatusSnapshot)
        .filter(SystemStatusSnapshot.system_id.in_(related_ids), SystemStatusSnapshot.captured_at >= since)
        .order_by(SystemStatusSnapshot.captured_at.desc())
        .limit(500)
        .all()
        if related_ids else []
    )
    latest = snapshots[0] if snapshots else (
        db.query(SystemStatusSnapshot)
        .filter(SystemStatusSnapshot.system_id.in_(related_ids))
        .order_by(SystemStatusSnapshot.captured_at.desc())
        .first()
        if related_ids else None
    )
    alarms = _build_alarm_items(snapshots)
    return {
        "system": {
            "system_id": system.id,
            "system_code": system.system_code,
            "system_name": system.name,
            "host_address": system.host_address,
            "env": system.env,
            "selfcheck_skill": getattr(system, "selfcheck_skill", None),
        },
        "range_minutes": range_minutes,
        "status": {
            "latest": _snapshot_payload(latest) if latest else None,
            "series": [_snapshot_payload(item) for item in reversed(snapshots[-120:])],
            "source_system_ids": related_ids,
        },
        "alarms": alarms,
        "alarm_count": len(alarms),
    }


@router.get("/run")
def run_system_selfcheck(
    system_id: int,
    range_minutes: int = 60,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    response_payload = _build_selfcheck_status_payload(db, current_user, system_id, range_minutes)
    system_payload = response_payload["system"]
    system = _visible_system_query(db, current_user).filter(System.id == system_payload["system_id"]).first()
    alarms = response_payload["alarms"]
    has_skill = bool((getattr(system, "selfcheck_skill", None) or "").strip())
    report = None
    if has_skill:
        if _is_mysql_selfcheck(system):
            report = _run_mysql_selfcheck_report(system)
        else:
            latest_payload = response_payload["status"]["latest"]
            latest = None
            if latest_payload:
                latest = (
                    db.query(SystemStatusSnapshot)
                    .filter(SystemStatusSnapshot.id == latest_payload["id"])
                    .first()
                )
            prompt = _build_selfcheck_prompt(system, response_payload["range_minutes"], latest, alarms)
            report = run_chat(ChatRequest(message=prompt, conversation_id=f"selfcheck-{system.id}"))
            report = _normalize_selfcheck_report(report, system, response_payload["range_minutes"], latest, alarms)
    log_action(db, "run_system_selfcheck", "selfcheck", current_user, {"system_id": system.id, "range_minutes": response_payload["range_minutes"], "alarm_count": len(alarms)})
    response_payload["ai_report"] = report
    response_payload["report_file"] = _save_selfcheck_report(db, response_payload)
    db.commit()
    return response_payload

@router.get("/status")
def get_system_selfcheck_status(
    system_id: int,
    range_minutes: int = 60,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _build_selfcheck_status_payload(db, current_user, system_id, range_minutes)

@router.get("/reports")
def list_selfcheck_reports(
    system_id: Optional[int] = None,
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    page = max(page, 1)
    size = min(max(size, 1), 100)
    visible_ids = {row.id for row in _visible_system_query(db, current_user).all()}
    if system_id is not None and system_id not in visible_ids:
        raise HTTPException(status_code=404, detail={"code": "SYSTEM_NOT_FOUND", "message": "系统不存在或无权访问"})
    if start_at is None and end_at is None:
        start_at = datetime.utcnow() - timedelta(hours=DEFAULT_REPORT_LOOKBACK_HOURS)
    items = _list_report_rows(db, system_id, start_at, end_at)
    if system_id is None:
        items = [item for item in items if item.get("system_id") in visible_ids]
    total = len(items)
    page_items = items[(page - 1) * size: page * size]
    return {
        "page": page,
        "size": size,
        "total": total,
        "retention_days": REPORT_RETENTION_DAYS,
        "default_lookback_hours": DEFAULT_REPORT_LOOKBACK_HOURS,
        "items": page_items,
    }

@router.get("/reports/{file_name}")
def get_selfcheck_report(
    file_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = _load_report_row_payload(db, file_name)
    visible_ids = {row.id for row in _visible_system_query(db, current_user).all()}
    system_id = (data.get("system") or {}).get("system_id")
    if system_id not in visible_ids:
        raise HTTPException(status_code=404, detail={"code": "REPORT_NOT_FOUND", "message": "AI 自检报告不存在或无权访问"})
    return data

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
