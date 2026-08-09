from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.firewall import FirewallBlockConfig
from app.models.security_response import FeishuEventReceipt, FeishuUserBinding, IpBlockBatch, IpBlockItem
from app.models.user import User
from app.services.audit import log_action
from app.services.firewall import block_ips_with_firewall
from app.services.threatbook import ThreatbookError, batch_query_ip_reputation
from app.core.config import settings


class SecurityResponseError(Exception):
    pass


class SecurityResponsePermissionError(SecurityResponseError):
    pass


class SecurityResponseStateError(SecurityResponseError):
    pass


def claim_feishu_event(db: Session, event_key: str, event_type: str) -> bool:
    try:
        db.add(FeishuEventReceipt(event_key=event_key, event_type=event_type, status="processing"))
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False


def complete_feishu_event(
    db: Session,
    event_key: str,
    status: str,
    result: Optional[Dict[str, Any]] = None,
) -> None:
    receipt = db.query(FeishuEventReceipt).filter(FeishuEventReceipt.event_key == event_key).first()
    if not receipt:
        return
    receipt.status = status
    receipt.result_json = json.dumps(result, ensure_ascii=False) if result else None
    receipt.completed_at = datetime.utcnow()
    db.commit()


def serialize_binding(binding: FeishuUserBinding) -> Dict[str, Any]:
    return {
        "id": binding.id,
        "open_id": binding.open_id,
        "display_name": binding.display_name,
        "aegis_user_id": binding.aegis_user_id,
        "can_query": binding.can_query,
        "can_block": binding.can_block,
        "enabled": binding.enabled,
        "created_at": binding.created_at.isoformat() if binding.created_at else None,
        "updated_at": binding.updated_at.isoformat() if binding.updated_at else None,
    }


def discover_feishu_user(
    db: Session,
    open_id: str,
    display_name: Optional[str] = None,
    union_id: Optional[str] = None,
    feishu_user_id: Optional[str] = None,
) -> FeishuUserBinding:
    binding = db.query(FeishuUserBinding).filter(FeishuUserBinding.open_id == open_id).first()
    if not binding:
        binding = FeishuUserBinding(
            open_id=open_id,
            display_name=display_name,
            union_id=union_id,
            feishu_user_id=feishu_user_id,
            enabled=False,
            can_query=False,
            can_block=False,
        )
        db.add(binding)
    else:
        binding.display_name = display_name or binding.display_name
        binding.union_id = union_id or binding.union_id
        binding.feishu_user_id = feishu_user_id or binding.feishu_user_id
        binding.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(binding)
    return binding


def require_feishu_permission(db: Session, open_id: str, permission: str) -> FeishuUserBinding:
    binding = db.query(FeishuUserBinding).filter(FeishuUserBinding.open_id == open_id).first()
    if not binding or not binding.enabled:
        raise SecurityResponsePermissionError("飞书账号尚未在 Aegis 管理端启用")
    if permission == "query" and not binding.can_query:
        raise SecurityResponsePermissionError("当前飞书账号没有 IP 查询权限")
    if permission == "block":
        if not binding.can_block:
            raise SecurityResponsePermissionError("当前飞书账号没有封禁权限")
        user = db.query(User).filter(User.id == binding.aegis_user_id).first()
        if not user or not user.is_active or not user.role or user.role.code not in {"admin", "super_admin"}:
            raise SecurityResponsePermissionError("封禁权限必须绑定有效的 Aegis 管理员账号")
    return binding


def upsert_feishu_binding(
    db: Session,
    open_id: str,
    display_name: Optional[str],
    aegis_user_id: Optional[int],
    can_query: bool,
    can_block: bool,
    enabled: bool,
) -> FeishuUserBinding:
    user = db.query(User).filter(User.id == aegis_user_id).first() if aegis_user_id else None
    if can_block and (not user or not user.is_active or user.role.code not in {"admin", "super_admin"}):
        raise SecurityResponsePermissionError("封禁权限只能授予已启用的 Aegis 管理员")
    binding = db.query(FeishuUserBinding).filter(FeishuUserBinding.open_id == open_id).first()
    if not binding:
        binding = FeishuUserBinding(open_id=open_id)
        db.add(binding)
    binding.display_name = display_name or binding.display_name
    binding.aegis_user_id = aegis_user_id
    binding.can_query = can_query
    binding.can_block = can_block
    binding.enabled = enabled
    binding.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(binding)
    return binding


def _firewall_target(db: Session, target_code: str) -> Optional[FirewallBlockConfig]:
    return db.query(FirewallBlockConfig).filter(FirewallBlockConfig.target_code == target_code).first()


def _require_firewall_target(db: Session, target_code: str) -> FirewallBlockConfig:
    target = _firewall_target(db, target_code)
    if not target:
        raise SecurityResponseStateError(f"山石目标不存在：{target_code}")
    if not target.enabled:
        raise SecurityResponseStateError(f"山石目标未启用：{target_code}")
    if not target.is_test_target and not settings.FEISHU_ALLOW_NON_TEST_FIREWALL_TARGETS:
        raise SecurityResponseStateError("当前阶段只允许飞书操作标记为测试设备的山石目标")
    return target


def create_analysis_batch(
    db: Session,
    raw_input: str,
    requester_user_id: Optional[int],
    requester_open_id: Optional[str],
    source_chat_id: Optional[str],
    source_message_id: Optional[str],
    firewall_target_code: str = "test-primary",
    analysis: Optional[Dict[str, Any]] = None,
    source: Optional[str] = None,
) -> IpBlockBatch:
    if requester_open_id:
        require_feishu_permission(db, requester_open_id, "query")
    target = _require_firewall_target(db, firewall_target_code)
    try:
        result = analysis or batch_query_ip_reputation([raw_input], lang="zh", realtime_verdict=True)
    except ThreatbookError as exc:
        raise SecurityResponseError(f"威胁情报查询失败：{exc}") from exc
    batch = IpBlockBatch(
        id=str(uuid4()),
        status="analyzed",
        source=source or ("feishu" if requester_open_id else "admin"),
        source_chat_id=source_chat_id,
        source_message_id=source_message_id,
        requester_open_id=requester_open_id,
        requester_user_id=requester_user_id,
        firewall_config_id=target.id,
        firewall_target_code=firewall_target_code,
        firewall_host=target.firewall_ip,
        address_book_name=target.address_book_name,
        reason="Aegis 威胁情报研判确认封禁（永久）",
        analysis_json=json.dumps(result, ensure_ascii=False),
        expires_at=datetime.utcnow() + timedelta(minutes=30),
    )
    db.add(batch)
    for item in result.get("items") or []:
        if item.get("resource_type", "ip") != "ip" or not item.get("ip"):
            continue
        db.add(
            IpBlockItem(
                batch_id=batch.id,
                ip=item["ip"],
                risk_level=item.get("risk_level"),
                is_malicious=bool(item.get("is_malicious")),
                should_block=bool(item.get("should_block")),
                needs_jinan_confirmation=bool(item.get("needs_manual_confirmation")),
                selected=False,
                summary=item.get("summary"),
            )
        )
    db.commit()
    db.refresh(batch)
    requester = db.query(User).filter(User.id == requester_user_id).first() if requester_user_id else None
    log_action(
        db,
        "create_ip_analysis_batch",
        "security_response",
        requester,
        {
            "batch_id": batch.id,
            "source": batch.source,
            "requester_open_id": requester_open_id,
            "count": len(result.get("items") or []),
            "firewall_target_code": firewall_target_code,
        },
    )
    return batch


def _get_batch(db: Session, batch_id: str) -> IpBlockBatch:
    batch = db.query(IpBlockBatch).filter(IpBlockBatch.id == batch_id).first()
    if not batch:
        raise SecurityResponseStateError("封禁批次不存在")
    if batch.expires_at <= datetime.utcnow() and batch.status not in {
        "succeeded",
        "dry_run_succeeded",
        "failed",
        "expired",
    }:
        batch.status = "expired"
        batch.updated_at = datetime.utcnow()
        db.commit()
        raise SecurityResponseStateError("确认卡片已过期，请重新查询")
    return batch


def prepare_batch(
    db: Session,
    batch_id: str,
    selection: str,
    confirmer_user_id: Optional[int],
    confirmer_open_id: Optional[str],
    selected_ips: Optional[List[str]] = None,
) -> IpBlockBatch:
    if confirmer_open_id:
        binding = require_feishu_permission(db, confirmer_open_id, "block")
        confirmer_user_id = binding.aegis_user_id
    batch = _get_batch(db, batch_id)
    if batch.status != "analyzed":
        raise SecurityResponseStateError(f"当前批次状态 {batch.status}，不能重复选择")
    items = db.query(IpBlockItem).filter(IpBlockItem.batch_id == batch.id).all()
    if selection not in {"recommended", "all_malicious", "selected"}:
        raise SecurityResponseStateError("不支持的 IP 选择方式")

    explicit_selection = None
    if selection == "selected":
        if selected_ips is None:
            explicit_selection = {item.ip for item in items if item.selected}
        else:
            explicit_selection = {str(ip).strip() for ip in selected_ips if str(ip).strip()}
        known_ips = {item.ip for item in items}
        unknown_ips = sorted(explicit_selection - known_ips)
        if unknown_ips:
            raise SecurityResponseStateError(f"所选 IP 不属于本次研判清单：{', '.join(unknown_ips)}")

    for item in items:
        if selection == "recommended":
            item.selected = item.should_block
        elif selection == "all_malicious":
            item.selected = item.is_malicious
        else:
            item.selected = item.ip in explicit_selection
        if item.selected:
            item.status = "selected"
        elif item.status == "selected":
            item.status = "analyzed"
    selected = [item for item in items if item.selected]
    if not selected:
        raise SecurityResponseStateError("本批次没有已选择的 IP")
    batch.confirmer_open_id = confirmer_open_id
    batch.confirmer_user_id = confirmer_user_id
    batch.status = (
        "jinan_confirmation_pending"
        if any(item.needs_jinan_confirmation for item in selected)
        else "execution_confirmation_pending"
    )
    batch.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(batch)
    return batch


def set_batch_item_selection(
    db: Session,
    batch_id: str,
    ip: str,
    selected: bool,
    confirmer_user_id: Optional[int],
    confirmer_open_id: Optional[str],
) -> IpBlockBatch:
    if confirmer_open_id:
        binding = require_feishu_permission(db, confirmer_open_id, "block")
        confirmer_user_id = binding.aegis_user_id
    batch = _get_batch(db, batch_id)
    if batch.status != "analyzed":
        raise SecurityResponseStateError(f"当前批次状态 {batch.status}，不能修改 IP 选择")
    item = db.query(IpBlockItem).filter(
        IpBlockItem.batch_id == batch.id,
        IpBlockItem.ip == ip.strip(),
    ).first()
    if not item:
        raise SecurityResponseStateError("所选 IP 不属于本次研判清单")
    item.selected = selected
    item.status = "selected" if selected else "analyzed"
    item.updated_at = datetime.utcnow()
    batch.confirmer_open_id = confirmer_open_id
    batch.confirmer_user_id = confirmer_user_id
    batch.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(batch)
    return batch


def confirm_jinan_batch(
    db: Session,
    batch_id: str,
    confirmer_user_id: Optional[int],
    confirmer_open_id: Optional[str],
) -> IpBlockBatch:
    if confirmer_open_id:
        binding = require_feishu_permission(db, confirmer_open_id, "block")
        confirmer_user_id = binding.aegis_user_id
    batch = _get_batch(db, batch_id)
    if batch.status != "jinan_confirmation_pending":
        raise SecurityResponseStateError("当前批次不处于济南 IP 二次确认状态")
    batch.jinan_confirmed = True
    batch.confirmer_open_id = confirmer_open_id
    batch.confirmer_user_id = confirmer_user_id
    batch.status = "execution_confirmation_pending"
    batch.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(batch)
    return batch


def execute_batch(
    db: Session,
    batch_id: str,
    confirmer_user_id: Optional[int],
    confirmer_open_id: Optional[str],
    dry_run: bool,
) -> IpBlockBatch:
    if confirmer_open_id:
        binding = require_feishu_permission(db, confirmer_open_id, "block")
        confirmer_user_id = binding.aegis_user_id
    batch = _get_batch(db, batch_id)
    if batch.status != "execution_confirmation_pending":
        raise SecurityResponseStateError("批次尚未完成执行前确认，或已被执行")
    selected = db.query(IpBlockItem).filter(
        IpBlockItem.batch_id == batch.id,
        IpBlockItem.selected.is_(True),
    ).all()
    if not selected:
        raise SecurityResponseStateError("批次中没有已选择的 IP")
    if any(item.needs_jinan_confirmation for item in selected) and not batch.jinan_confirmed:
        raise SecurityResponseStateError("包含济南 IP，必须先完成二次确认")

    target = _require_firewall_target(db, batch.firewall_target_code)
    if (
        target.id != batch.firewall_config_id
        or target.firewall_ip != batch.firewall_host
        or target.address_book_name != batch.address_book_name
    ):
        raise SecurityResponseStateError("山石目标在研判后发生变化，请重新发起 IP 查询")

    updated = (
        db.query(IpBlockBatch)
        .filter(
            IpBlockBatch.id == batch.id,
            IpBlockBatch.status == "execution_confirmation_pending",
        )
        .update(
            {
                IpBlockBatch.status: "executing",
                IpBlockBatch.confirmer_open_id: confirmer_open_id,
                IpBlockBatch.confirmer_user_id: confirmer_user_id,
                IpBlockBatch.updated_at: datetime.utcnow(),
            },
            synchronize_session=False,
        )
    )
    if updated != 1:
        db.rollback()
        raise SecurityResponseStateError("批次正在执行或已执行，请勿重复点击")
    db.commit()
    db.refresh(batch)
    try:
        result = block_ips_with_firewall(
            [item.ip for item in selected],
            reason=batch.reason,
            dry_run=dry_run,
            db=db,
            target_code=batch.firewall_target_code,
        )
        batch.status = "dry_run_succeeded" if dry_run else "succeeded"
        batch.execution_json = json.dumps(result, ensure_ascii=False)
        batch.executed_at = datetime.utcnow()
        for item in selected:
            item.status = "dry_run" if dry_run else "blocked"
            item.result_json = json.dumps({"verified": item.ip in result.get("verified_ips", [])}, ensure_ascii=False)
    except Exception as exc:
        batch.status = "failed"
        batch.error_message = str(exc)
        for item in selected:
            item.status = "failed"
        db.commit()
        confirmer = db.query(User).filter(User.id == confirmer_user_id).first() if confirmer_user_id else None
        log_action(
            db,
            "execute_ip_block_batch_failed",
            "security_response",
            confirmer,
            {
                "batch_id": batch.id,
                "confirmer_open_id": confirmer_open_id,
                "firewall_target_code": batch.firewall_target_code,
                "ips": [item.ip for item in selected],
                "dry_run": dry_run,
                "error": str(exc),
            },
        )
        raise SecurityResponseError(f"山石封禁执行失败：{exc}") from exc
    batch.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(batch)
    confirmer = db.query(User).filter(User.id == confirmer_user_id).first() if confirmer_user_id else None
    log_action(
        db,
        "execute_ip_block_batch",
        "security_response",
        confirmer,
        {
            "batch_id": batch.id,
            "confirmer_open_id": confirmer_open_id,
            "firewall_target_code": batch.firewall_target_code,
            "ips": [item.ip for item in selected],
            "dry_run": dry_run,
            "status": batch.status,
            "execution": result,
        },
    )
    return batch


def serialize_batch(db: Session, batch: IpBlockBatch) -> Dict[str, Any]:
    items = db.query(IpBlockItem).filter(IpBlockItem.batch_id == batch.id).order_by(IpBlockItem.id.asc()).all()
    try:
        analysis = json.loads(batch.analysis_json) if batch.analysis_json else {}
    except (TypeError, ValueError):
        analysis = {}
    analysis_by_ip = {
        str(item.get("ip")): item
        for item in (analysis.get("items") or [])
        if isinstance(item, dict) and item.get("ip")
    }

    def serialize_item(item: IpBlockItem) -> Dict[str, Any]:
        intel = analysis_by_ip.get(item.ip, {})
        basic = intel.get("basic") if isinstance(intel.get("basic"), dict) else {}
        location = basic.get("location") if isinstance(basic.get("location"), dict) else {}
        asn = intel.get("asn") if isinstance(intel.get("asn"), dict) else {}
        return {
            "ip": item.ip,
            "risk_level": item.risk_level,
            "risk_score": intel.get("risk_score"),
            "is_malicious": item.is_malicious,
            "should_block": item.should_block,
            "needs_jinan_confirmation": item.needs_jinan_confirmation,
            "selected": item.selected,
            "summary": item.summary,
            "status": item.status,
            "country": intel.get("country") or location.get("country"),
            "province": location.get("province"),
            "city": location.get("city"),
            "location": location.get("display"),
            "carrier": basic.get("carrier"),
            "asn_number": asn.get("number"),
            "asn_info": asn.get("info"),
            "asn_rank": asn.get("rank"),
            "attack_types": intel.get("malicious_types") or intel.get("malicious_judgments") or [],
            "judgments": intel.get("judgments") or [],
            "tags": intel.get("tags") or [],
            "severity": intel.get("severity"),
            "confidence_level": intel.get("confidence_level"),
            "scene": intel.get("scene"),
            "update_time": intel.get("update_time"),
            "permalink": intel.get("permalink"),
        }

    return {
        "id": batch.id,
        "status": batch.status,
        "source": batch.source,
        "firewall_target_code": batch.firewall_target_code,
        "firewall_host": batch.firewall_host,
        "address_book_name": batch.address_book_name,
        "jinan_confirmed": batch.jinan_confirmed,
        "expires_at": batch.expires_at.isoformat() if batch.expires_at else None,
        "execution": json.loads(batch.execution_json) if batch.execution_json else None,
        "error_message": batch.error_message,
        "items": [serialize_item(item) for item in items],
    }
