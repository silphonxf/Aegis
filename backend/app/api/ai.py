import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.ai_diagnosis import AIDiagnosis
from app.models.user import User
from app.schemas.ai import DiagnoseRequest
from app.services.audit import log_action

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


@router.post("/diagnose")
def diagnose(
    payload: DiagnoseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    suggestions = _mock_suggestions(payload)
    row = AIDiagnosis(
        title=payload.title,
        severity=payload.severity,
        detail=payload.detail,
        suggestions=json.dumps(suggestions, ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    log_action(db, "ai_diagnose", "ai", current_user, {"diagnosis_id": row.id, "severity": payload.severity})
    return {
        "id": row.id,
        "mode": "mock",
        "title": payload.title,
        "severity": payload.severity,
        "suggestions": suggestions,
        "disclaimer": "当前为迭代3 mock 诊断接口，仅提供辅助建议，不自动执行变更。",
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
