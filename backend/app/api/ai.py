from fastapi import APIRouter, Depends

from app.api.deps import require_roles
from app.models.user import User
from app.schemas.ai import DiagnoseRequest

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/diagnose")
def diagnose(payload: DiagnoseRequest, _: User = Depends(require_roles("admin", "super_admin"))):
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

    return {
        "mode": "mock",
        "title": payload.title,
        "severity": payload.severity,
        "suggestions": suggestions,
        "disclaimer": "当前为迭代3 mock 诊断接口，仅提供辅助建议，不自动执行变更。",
    }
