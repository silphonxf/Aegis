import asyncio
import re
from typing import Any, Dict, Optional

from lark_oapi.channel import CardActionEvent, FeishuChannel, InboundMessage

import app.db.session as db_session
from app.services.security_response import (
    SecurityResponseError,
    claim_feishu_event,
    complete_feishu_event,
    confirm_jinan_batch,
    create_analysis_batch,
    discover_feishu_user,
    execute_batch,
    prepare_batch,
    serialize_batch,
)
from app.services.threatbook import ThreatbookError, validate_ip

from .cards import analysis_card, confirmation_card, result_card


IPV4_CANDIDATE = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")


def _extract_ips(text: str) -> str:
    valid = []
    for candidate in IPV4_CANDIDATE.findall(text):
        try:
            valid.append(validate_ip(candidate))
        except ThreatbookError:
            continue
    return "\n".join(dict.fromkeys(valid))


class FeishuSecurityHandler:
    def __init__(self, channel: FeishuChannel, firewall_target_code: str = "test-primary") -> None:
        self.channel = channel
        self.firewall_target_code = firewall_target_code

    def _send_text(self, chat_id: str, text: str) -> None:
        self.channel.send(chat_id, {"text": text})

    async def on_message(self, message: InboundMessage) -> None:
        await asyncio.to_thread(self._handle_message_sync, message)

    def _handle_message_sync(self, message: InboundMessage) -> None:
        if message.chat_type != "p2p" and not message.mentioned_bot:
            return
        open_id = message.sender.open_id
        db = db_session.SessionLocal()
        event_key = f"message:{message.message_id}"
        try:
            if not claim_feishu_event(db, event_key, "message"):
                return
            binding = discover_feishu_user(
                db,
                open_id=open_id,
                display_name=message.sender.display_name,
                union_id=message.sender.union_id,
                feishu_user_id=message.sender.user_id,
            )
            if not binding.enabled or not binding.can_query:
                identity_hint = (
                    f"请管理员在 Aegis 中绑定 open_id：{open_id}"
                    if message.chat_type == "p2p"
                    else "请管理员在 Aegis 的飞书身份列表中为你授权"
                )
                self._send_text(
                    message.chat_id,
                    f"你的飞书身份已登记，但尚未开通查询权限。{identity_hint}",
                )
                complete_feishu_event(db, event_key, "completed", {"authorized": False})
                return
            raw_ips = _extract_ips(message.content_text)
            if not raw_ips:
                self._send_text(message.chat_id, "请发送要研判的 IPv4，例如：查询 8.8.8.8 1.2.3.4")
                complete_feishu_event(db, event_key, "completed", {"ip_count": 0})
                return
            batch = create_analysis_batch(
                db,
                raw_input=raw_ips,
                requester_user_id=binding.aegis_user_id,
                requester_open_id=open_id,
                source_chat_id=message.chat_id,
                source_message_id=message.message_id,
                firewall_target_code=self.firewall_target_code,
            )
            self.channel.send(message.chat_id, {"card": analysis_card(serialize_batch(db, batch))})
            complete_feishu_event(db, event_key, "completed", {"batch_id": batch.id})
        except (SecurityResponseError, ThreatbookError) as exc:
            self._send_text(message.chat_id, f"IP 研判失败：{exc}")
            complete_feishu_event(db, event_key, "failed", {"error": str(exc)})
        except Exception as exc:
            complete_feishu_event(db, event_key, "failed", {"error": str(exc)})
            raise
        finally:
            db.close()

    async def on_card_action(self, event: CardActionEvent) -> None:
        await asyncio.to_thread(self._handle_card_action_sync, event)

    def _handle_card_action_sync(self, event: CardActionEvent) -> None:
        value: Any = event.action.value
        if not isinstance(value, dict):
            self._send_text(event.chat_id, "无效的卡片操作。")
            return
        action = str(value.get("action") or "")
        batch_id = str(value.get("batch_id") or "")
        if not batch_id or action not in {
            "prepare_recommended",
            "prepare_all_malicious",
            "confirm_jinan",
            "execute_dry_run",
            "execute_permanent",
        }:
            self._send_text(event.chat_id, "卡片操作参数无效。")
            return

        db = db_session.SessionLocal()
        event_key = f"card:{event.message_id}:{event.operator.open_id}:{action}:{batch_id}"
        try:
            if not claim_feishu_event(db, event_key, "card_action"):
                return
            if action.startswith("prepare_"):
                selection = "recommended" if action == "prepare_recommended" else "all_malicious"
                batch = prepare_batch(db, batch_id, selection, None, event.operator.open_id)
                card = confirmation_card(serialize_batch(db, batch))
            elif action == "confirm_jinan":
                batch = confirm_jinan_batch(db, batch_id, None, event.operator.open_id)
                card = confirmation_card(serialize_batch(db, batch))
            else:
                batch = execute_batch(
                    db,
                    batch_id,
                    None,
                    event.operator.open_id,
                    dry_run=action == "execute_dry_run",
                )
                card = result_card(serialize_batch(db, batch))
            self.channel.update_card(event.message_id, card)
            complete_feishu_event(db, event_key, "completed", {"batch_id": batch.id, "status": batch.status})
        except SecurityResponseError as exc:
            self._send_text(event.chat_id, f"操作被拒绝：{exc}")
            complete_feishu_event(db, event_key, "rejected", {"error": str(exc)})
        except Exception as exc:
            self._send_text(event.chat_id, f"封禁执行失败：{exc}")
            complete_feishu_event(db, event_key, "failed", {"error": str(exc)})
        finally:
            db.close()
