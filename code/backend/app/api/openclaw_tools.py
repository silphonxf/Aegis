import hmac
import ipaddress
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.security_response import IpBlockBatch
from app.schemas.openclaw_tools import (
    OpenClawBatchConfirmRequest,
    OpenClawBatchExecuteRequest,
    OpenClawBatchItemSelectionRequest,
    OpenClawBatchPrepareRequest,
    OpenClawIpAnalyzeRequest,
)
from app.services.security_response import (
    SecurityResponseError,
    SecurityResponsePermissionError,
    SecurityResponseStateError,
    confirm_jinan_batch,
    create_analysis_batch,
    discover_feishu_user,
    execute_batch,
    prepare_batch,
    require_feishu_permission,
    serialize_batch,
    set_batch_item_selection,
)


router = APIRouter(prefix="/aegis/tools/v1", tags=["openclaw-tools"])


def _http_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def _security_error(exc: SecurityResponseError) -> HTTPException:
    if isinstance(exc, SecurityResponsePermissionError):
        return _http_error(403, "FEISHU_ACCOUNT_FORBIDDEN", str(exc))
    if isinstance(exc, SecurityResponseStateError):
        return _http_error(409, "IP_BLOCK_STATE_CONFLICT", str(exc))
    return _http_error(400, "SECURITY_RESPONSE_ERROR", str(exc))


def _client_is_allowed(request: Request) -> bool:
    raw_cidrs = settings.OPENCLAW_TOOL_ALLOWED_CLIENT_CIDRS.strip()
    if not raw_cidrs:
        return True
    if not request.client or not request.client.host:
        return False
    client_host = request.client.host
    try:
        direct_client_ip = ipaddress.ip_address(client_host)
    except ValueError:
        return False
    if direct_client_ip.is_loopback:
        proxied_host = (request.headers.get("X-Aegis-Proxy-Client-IP") or "").strip()
        if proxied_host:
            client_host = proxied_host
    try:
        client_ip = ipaddress.ip_address(client_host)
    except ValueError:
        return False
    for raw_cidr in raw_cidrs.split(","):
        raw_cidr = raw_cidr.strip()
        if not raw_cidr:
            continue
        try:
            if client_ip in ipaddress.ip_network(raw_cidr, strict=False):
                return True
        except ValueError:
            continue
    return False


def require_openclaw_feishu_identity(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_openclaw_channel: Optional[str] = Header(default=None),
    x_feishu_open_id: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> str:
    if not settings.OPENCLAW_TOOL_GATEWAY_ENABLED:
        raise _http_error(404, "TOOL_GATEWAY_DISABLED", "OpenClaw 远程工具网关未启用")

    expected_token = (settings.OPENCLAW_TOOL_GATEWAY_TOKEN or "").strip()
    if len(expected_token) < 24:
        raise _http_error(503, "TOOL_GATEWAY_MISCONFIGURED", "OpenClaw 工具网关令牌未安全配置")
    if not authorization or not authorization.startswith("Bearer "):
        raise _http_error(401, "TOOL_GATEWAY_UNAUTHORIZED", "缺少 Authorization Bearer token")
    supplied_token = authorization.split(" ", 1)[1].strip()
    if not hmac.compare_digest(supplied_token, expected_token):
        raise _http_error(403, "TOOL_GATEWAY_FORBIDDEN", "OpenClaw 工具网关令牌无效")
    if not _client_is_allowed(request):
        raise _http_error(403, "TOOL_GATEWAY_SOURCE_FORBIDDEN", "调用服务器地址不在允许列表中")
    if (x_openclaw_channel or "").strip().lower() != "feishu":
        raise _http_error(403, "TRUSTED_FEISHU_CONTEXT_REQUIRED", "此工具只能从 OpenClaw 飞书会话调用")

    open_id = (x_feishu_open_id or "").strip()
    if len(open_id) < 3 or len(open_id) > 128 or any(char in open_id for char in "\r\n"):
        raise _http_error(403, "TRUSTED_FEISHU_ID_REQUIRED", "缺少可信的飞书发送者 open_id")
    # A trusted but unknown OpenClaw sender is recorded in a disabled state so
    # a super administrator can see and explicitly authorize it in Aegis.
    discover_feishu_user(db, open_id=open_id)
    return open_id


def _owned_batch(db: Session, batch_id: str, open_id: str) -> IpBlockBatch:
    batch = db.query(IpBlockBatch).filter(IpBlockBatch.id == batch_id).first()
    if not batch:
        raise _http_error(404, "BATCH_NOT_FOUND", "封禁批次不存在")
    if batch.source != "openclaw" or batch.requester_open_id != open_id:
        raise _http_error(403, "BATCH_OWNER_MISMATCH", "不能操作其他飞书账号创建的封禁批次")
    return batch


@router.get("/healthz")
def openclaw_tool_healthz():
    return {
        "status": "ok",
        "service": "aegis-openclaw-tool-gateway",
        "enabled": settings.OPENCLAW_TOOL_GATEWAY_ENABLED,
    }


@router.get("/capabilities")
def openclaw_capabilities(
    open_id: str = Depends(require_openclaw_feishu_identity),
    db: Session = Depends(get_db),
):
    try:
        binding = require_feishu_permission(db, open_id, "query")
    except SecurityResponseError as exc:
        raise _security_error(exc) from exc
    return {
        "channel": "feishu",
        "display_name": binding.display_name,
        "can_query": binding.can_query,
        "can_block": binding.can_block,
        "permanent_block_enabled": settings.OPENCLAW_TOOL_ALLOW_PERMANENT_BLOCK,
        "firewall_target_code": settings.OPENCLAW_TOOL_FIREWALL_TARGET_CODE,
    }


@router.post("/ip/analyze")
def openclaw_analyze_ip(
    payload: OpenClawIpAnalyzeRequest,
    open_id: str = Depends(require_openclaw_feishu_identity),
    db: Session = Depends(get_db),
):
    try:
        binding = require_feishu_permission(db, open_id, "query")
        batch = create_analysis_batch(
            db,
            raw_input=payload.raw_input,
            requester_user_id=binding.aegis_user_id,
            requester_open_id=open_id,
            source_chat_id=payload.session_key,
            source_message_id=payload.message_id,
            firewall_target_code=settings.OPENCLAW_TOOL_FIREWALL_TARGET_CODE,
            source="openclaw",
        )
    except SecurityResponseError as exc:
        raise _security_error(exc) from exc
    return serialize_batch(db, batch)


@router.get("/ip/batches/{batch_id}")
def openclaw_get_batch(
    batch_id: str,
    open_id: str = Depends(require_openclaw_feishu_identity),
    db: Session = Depends(get_db),
):
    try:
        require_feishu_permission(db, open_id, "query")
    except SecurityResponseError as exc:
        raise _security_error(exc) from exc
    return serialize_batch(db, _owned_batch(db, batch_id, open_id))


@router.post("/ip/batches/{batch_id}/prepare")
def openclaw_prepare_batch(
    batch_id: str,
    payload: OpenClawBatchPrepareRequest,
    open_id: str = Depends(require_openclaw_feishu_identity),
    db: Session = Depends(get_db),
):
    _owned_batch(db, batch_id, open_id)
    try:
        batch = prepare_batch(
            db,
            batch_id,
            payload.selection,
            None,
            open_id,
            selected_ips=payload.selected_ips,
        )
    except SecurityResponseError as exc:
        raise _security_error(exc) from exc
    return serialize_batch(db, batch)


@router.post("/ip/batches/{batch_id}/selection")
def openclaw_select_batch_item(
    batch_id: str,
    payload: OpenClawBatchItemSelectionRequest,
    open_id: str = Depends(require_openclaw_feishu_identity),
    db: Session = Depends(get_db),
):
    _owned_batch(db, batch_id, open_id)
    try:
        batch = set_batch_item_selection(
            db,
            batch_id,
            payload.ip,
            payload.selected,
            None,
            open_id,
        )
    except SecurityResponseError as exc:
        raise _security_error(exc) from exc
    return serialize_batch(db, batch)


@router.post("/ip/batches/{batch_id}/confirm-jinan")
def openclaw_confirm_jinan(
    batch_id: str,
    _: OpenClawBatchConfirmRequest,
    open_id: str = Depends(require_openclaw_feishu_identity),
    db: Session = Depends(get_db),
):
    _owned_batch(db, batch_id, open_id)
    try:
        batch = confirm_jinan_batch(db, batch_id, None, open_id)
    except SecurityResponseError as exc:
        raise _security_error(exc) from exc
    return serialize_batch(db, batch)


@router.post("/ip/batches/{batch_id}/execute")
def openclaw_execute_batch(
    batch_id: str,
    payload: OpenClawBatchExecuteRequest,
    open_id: str = Depends(require_openclaw_feishu_identity),
    db: Session = Depends(get_db),
):
    _owned_batch(db, batch_id, open_id)
    if not payload.dry_run:
        if not settings.OPENCLAW_TOOL_ALLOW_PERMANENT_BLOCK:
            raise _http_error(403, "PERMANENT_BLOCK_DISABLED", "OpenClaw 永久封禁开关未启用")
        if not payload.confirmed:
            raise _http_error(400, "EXPLICIT_CONFIRMATION_REQUIRED", "永久封禁必须显式确认")
    try:
        batch = execute_batch(db, batch_id, None, open_id, payload.dry_run)
    except SecurityResponseError as exc:
        raise _security_error(exc) from exc
    return serialize_batch(db, batch)
