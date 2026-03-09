import json
import re
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.config import settings
from app.db.session import get_db
from app.models.ai_diagnosis import AIDiagnosis
from app.models.offline_analysis import OfflineAnalysisResult, OfflineAnalysisTask
from app.models.user import User
from app.schemas.ai import DiagnoseRequest
from app.schemas.offline_ai import OfflineAnalyzeRequest
from app.services.audit import log_action
from app.services.offline_llm import OfflineLLMError, diagnose_with_ollama, offline_analyze_with_ollama

router = APIRouter(prefix="/ai", tags=["ai"])


def _mock_suggestions(payload: DiagnoseRequest) -> list[str]:
    text = payload.detail.lower()
    suggestions = []

    if "cpu" in text or "load" in text:
        suggestions.append("先检查最近15分钟CPU突增进程（top/ps），确认是否发布或批处理引发。")
    if "内存" in payload.detail or "memory" in text:
        suggestions.append("检查内存泄漏与缓存命中率，必要时分时重启高占用服务。")
    if "连接" in payload.detail or "timeout" in text:
        suggestions.append("优先排查网络连通、连接池上限、下游依赖RT抖动。")

    if not suggestions:
        suggestions = [
            "先定位影响范围（单实例/全局），再按CPU、内存、磁盘、网络四象限逐项排查。",
            "保留现场日志与关键指标快照，避免重启后丢失证据。",
        ]
    return suggestions


OFFLINE_RULES = [
    {
        "code": "DB_CONN_FAIL",
        "pattern": r"(connection refused|could not connect|db.*timeout|数据库连接失败)",
        "severity": "high",
        "suggestion": "检查数据库连通性、账号权限、连接池上限；确认数据库实例状态正常。",
    },
    {
        "code": "DISK_FULL",
        "pattern": r"(no space left on device|disk full|磁盘.*已满)",
        "severity": "high",
        "suggestion": "清理日志与临时文件，扩容磁盘；为关键目录设置容量告警阈值。",
    },
    {
        "code": "OOM_KILLED",
        "pattern": r"(out of memory|oom-killer|killed process)",
        "severity": "high",
        "suggestion": "排查内存泄漏，限制进程内存，必要时分批任务并降低并发。",
    },
    {
        "code": "PORT_CONFLICT",
        "pattern": r"(address already in use|端口.*被占用)",
        "severity": "medium",
        "suggestion": "定位端口占用进程并释放，或调整服务端口并更新配置。",
    },
    {
        "code": "AUTH_FAILED",
        "pattern": r"(unauthorized|forbidden|invalid token|鉴权失败|权限不足)",
        "severity": "medium",
        "suggestion": "核对凭证有效期、签名密钥和角色权限映射，检查网关转发头。",
    },
    {
        "code": "SERVICE_TIMEOUT",
        "pattern": r"(timeout|timed out|read timeout|请求超时)",
        "severity": "medium",
        "suggestion": "检查下游RT、网络抖动与重试策略，避免无上限重试放大故障。",
    },
]


def _severity_rank(level: str) -> int:
    return {"low": 1, "medium": 2, "high": 3}.get(level, 1)


def _offline_rule_analyze(text: str, fallback_severity: str) -> tuple[str, list[dict], list[str], str]:
    matched = []
    suggestions = []
    summary_items = []
    final_severity = fallback_severity

    for rule in OFFLINE_RULES:
        if re.search(rule["pattern"], text, flags=re.I):
            matched.append({"code": rule["code"], "severity": rule["severity"]})
            suggestions.append(rule["suggestion"])
            summary_items.append(rule["code"])
            if _severity_rank(rule["severity"]) > _severity_rank(final_severity):
                final_severity = rule["severity"]

    if not matched:
        suggestions = [
            "未命中已知规则，请先按时间线定位首个报错，再关联上下游依赖日志进行排查。",
            "建议补充业务日志关键字段（trace_id/system_id/error_code）提升自动分析命中率。",
        ]
        summary = "未命中规则，建议人工复核。"
    else:
        summary = f"命中规则: {', '.join(summary_items)}"

    excerpt = "\n".join([ln for ln in text.splitlines() if ln.strip()][:60])
    return final_severity, matched, list(dict.fromkeys(suggestions)), summary, excerpt


@router.post("/diagnose")
def diagnose(
    payload: DiagnoseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    mode = "rule_fallback"
    severity = payload.severity
    summary = ""
    fallback_reason: str | None = None
    started_at = time.perf_counter()

    if settings.OFFLINE_AI_ENABLED and settings.OFFLINE_AI_PROVIDER.lower() == "ollama":
        try:
            severity, suggestions, summary = diagnose_with_ollama(payload.title, payload.detail, payload.severity)
            mode = "offline_ollama"
        except OfflineLLMError as e:
            suggestions = _mock_suggestions(payload)
            summary = "离线模型不可用，已回退规则建议。"
            fallback_reason = str(e)[:200]
    else:
        suggestions = _mock_suggestions(payload)
        summary = "离线模型未启用，已使用规则建议。"
        fallback_reason = "offline_ai_disabled_or_provider_mismatch"

    elapsed_ms = int((time.perf_counter() - started_at) * 1000)

    row = AIDiagnosis(
        title=payload.title,
        severity=severity,
        detail=payload.detail,
        suggestions=json.dumps(suggestions, ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    log_action(
        db,
        "ai_diagnose",
        "ai",
        current_user,
        {
            "diagnosis_id": row.id,
            "severity": severity,
            "mode": mode,
            "elapsed_ms": elapsed_ms,
            "fallback_reason": fallback_reason,
        },
    )
    return {
        "id": row.id,
        "mode": mode,
        "title": payload.title,
        "severity": severity,
        "summary": summary,
        "suggestions": suggestions,
        "elapsed_ms": elapsed_ms,
        "fallback_reason": fallback_reason,
    }


@router.get("/diagnoses")
def list_diagnoses(
    page: int = 1,
    size: int = 20,
    severity: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "super_admin")),
):
    page = max(page, 1)
    size = min(max(size, 1), 100)

    q = db.query(AIDiagnosis)
    if severity:
        q = q.filter(AIDiagnosis.severity == severity)

    total = q.count()
    items = q.order_by(AIDiagnosis.created_at.desc()).offset((page - 1) * size).limit(size).all()

    return {
        "page": page,
        "size": size,
        "total": total,
        "filters": {"severity": severity},
        "items": [
            {
                "id": i.id,
                "title": i.title,
                "severity": i.severity,
                "detail": i.detail,
                "suggestions": json.loads(i.suggestions),
                "created_at": i.created_at,
            }
            for i in items
        ],
    }


@router.post("/offline/analyze")
def offline_analyze(
    payload: OfflineAnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    mode = "rule_fallback"
    fallback_reason: str | None = None
    started_at = time.perf_counter()
    if settings.OFFLINE_AI_ENABLED and settings.OFFLINE_AI_PROVIDER.lower() == "ollama":
        try:
            final_severity, summary, suggestions, matched = offline_analyze_with_ollama(
                payload.title, payload.detail, payload.severity
            )
            excerpt = "\n".join([ln for ln in payload.detail.splitlines() if ln.strip()][:80])
            mode = "offline_ollama"
        except OfflineLLMError as e:
            final_severity, matched, suggestions, summary, excerpt = _offline_rule_analyze(payload.detail, payload.severity)
            fallback_reason = str(e)[:200]
    else:
        final_severity, matched, suggestions, summary, excerpt = _offline_rule_analyze(payload.detail, payload.severity)
        fallback_reason = "offline_ai_disabled_or_provider_mismatch"

    elapsed_ms = int((time.perf_counter() - started_at) * 1000)

    task = OfflineAnalysisTask(
        source_type=payload.source_type,
        source_ref=payload.source_ref,
        status="done",
        severity=final_severity,
        title=payload.title,
        summary=summary,
        created_by=current_user.username,
    )
    db.add(task)
    db.flush()

    result = OfflineAnalysisResult(
        task_id=task.id,
        matched_rules=json.dumps(matched, ensure_ascii=False),
        suggestions=json.dumps(suggestions, ensure_ascii=False),
        raw_excerpt=excerpt,
    )
    db.add(result)
    db.commit()

    log_action(
        db,
        "ai_offline_analyze",
        "ai_offline",
        current_user,
        {
            "task_id": task.id,
            "severity": final_severity,
            "mode": mode,
            "elapsed_ms": elapsed_ms,
            "fallback_reason": fallback_reason,
        },
    )
    return {
        "task_id": task.id,
        "status": task.status,
        "mode": mode,
        "severity": final_severity,
        "summary": summary,
        "matched_rules": matched,
        "suggestions": suggestions,
        "elapsed_ms": elapsed_ms,
        "fallback_reason": fallback_reason,
    }


@router.get("/offline/tasks")
def list_offline_tasks(
    page: int = 1,
    size: int = 20,
    severity: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "super_admin")),
):
    page = max(page, 1)
    size = min(max(size, 1), 100)

    q = db.query(OfflineAnalysisTask)
    if severity:
        q = q.filter(OfflineAnalysisTask.severity == severity)

    total = q.count()
    items = q.order_by(OfflineAnalysisTask.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return {
        "page": page,
        "size": size,
        "total": total,
        "items": [
            {
                "id": t.id,
                "title": t.title,
                "source_type": t.source_type,
                "source_ref": t.source_ref,
                "status": t.status,
                "severity": t.severity,
                "summary": t.summary,
                "created_by": t.created_by,
                "created_at": t.created_at,
            }
            for t in items
        ],
    }


@router.get("/offline/tasks/{task_id}")
def get_offline_task(
    task_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "super_admin")),
):
    task = db.query(OfflineAnalysisTask).filter(OfflineAnalysisTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail={"code": "TASK_NOT_FOUND", "message": "任务不存在"})

    result = db.query(OfflineAnalysisResult).filter(OfflineAnalysisResult.task_id == task_id).order_by(OfflineAnalysisResult.id.desc()).first()
    return {
        "task": {
            "id": task.id,
            "title": task.title,
            "source_type": task.source_type,
            "source_ref": task.source_ref,
            "status": task.status,
            "severity": task.severity,
            "summary": task.summary,
            "created_by": task.created_by,
            "created_at": task.created_at,
        },
        "result": {
            "matched_rules": json.loads(result.matched_rules) if result else [],
            "suggestions": json.loads(result.suggestions) if result else [],
            "raw_excerpt": result.raw_excerpt if result else "",
            "created_at": result.created_at if result else None,
        },
    }
