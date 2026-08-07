from typing import Any, Dict, List


RISK_LABELS = {
    "high_risk": "高危",
    "medium_risk": "中危",
    "suspicious": "可疑",
    "safe": "安全",
}


def _button(text: str, action: str, batch_id: str, button_type: str = "default") -> Dict[str, Any]:
    return {
        "tag": "button",
        "text": {"tag": "plain_text", "content": text},
        "type": button_type,
        "value": {"action": action, "batch_id": batch_id},
    }


def _card(title: str, color: str, elements: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "schema": "2.0",
        "config": {"update_multi": True},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": color,
        },
        "body": {"elements": elements},
    }


def analysis_card(batch: Dict[str, Any]) -> Dict[str, Any]:
    items = batch["items"]
    malicious = [item for item in items if item["is_malicious"]]
    rows = []
    for item in items[:20]:
        marker = "🔴" if item["is_malicious"] else "🟢"
        jinan = " · 济南二次确认" if item["needs_jinan_confirmation"] else ""
        rows.append(
            f"{marker} **{item['ip']}** · {RISK_LABELS.get(item['risk_level'], item['risk_level'] or '未知')}{jinan}\n"
            f"{item['summary'] or '-'}"
        )
    elements: List[Dict[str, Any]] = [
        {
            "tag": "markdown",
            "content": (
                f"共研判 **{len(items)}** 个 IP，恶意 **{len(malicious)}** 个。\n"
                f"目标设备：`{batch['firewall_target_code']}`；封禁方式：**永久加入地址簿**。"
            ),
        },
        {"tag": "hr"},
        {"tag": "markdown", "content": "\n\n".join(rows) or "未发现可展示的 IP。"},
    ]
    if len(items) > 20:
        elements.append({"tag": "markdown", "content": f"另有 {len(items) - 20} 条未在卡片中展开。"})
    elements.append(
        {
            "tag": "action",
            "actions": [
                _button("选择建议封禁", "prepare_recommended", batch["id"], "primary"),
                _button("选择全部恶意", "prepare_all_malicious", batch["id"], "danger"),
            ],
        }
    )
    elements.append({"tag": "note", "elements": [{"tag": "plain_text", "content": "卡片 30 分钟内有效；按钮点击后仍会校验 Aegis 权限。"}]})
    return _card("Aegis IP 威胁研判", "blue", elements)


def confirmation_card(batch: Dict[str, Any]) -> Dict[str, Any]:
    selected = [item for item in batch["items"] if item["selected"]]
    ips = "、".join(item["ip"] for item in selected)
    has_jinan = any(item["needs_jinan_confirmation"] for item in selected)
    elements: List[Dict[str, Any]] = [
        {
            "tag": "markdown",
            "content": (
                f"待操作 **{len(selected)}** 个 IP：\n`{ips}`\n\n"
                f"目标设备：`{batch['firewall_target_code']}`\n"
                "动作：**永久加入已被策略引用的山石地址簿**"
            ),
        }
    ]
    if batch["status"] == "jinan_confirmation_pending":
        elements.extend(
            [
                {"tag": "markdown", "content": "⚠️ 本批次包含济南 IP，必须单独完成二次确认。"},
                {
                    "tag": "action",
                    "actions": [_button("确认济南 IP 也需要封禁", "confirm_jinan", batch["id"], "danger")],
                },
            ]
        )
        return _card("等待济南 IP 二次确认", "orange", elements)
    if has_jinan and batch["jinan_confirmed"]:
        elements.append({"tag": "markdown", "content": "✅ 济南 IP 二次确认已完成。"})
    elements.append(
        {
            "tag": "action",
            "actions": [
                _button("仅演练（不改防火墙）", "execute_dry_run", batch["id"], "default"),
                _button("确认永久封禁", "execute_permanent", batch["id"], "danger"),
            ],
        }
    )
    return _card("等待最终执行确认", "orange", elements)


def result_card(batch: Dict[str, Any]) -> Dict[str, Any]:
    selected = [item for item in batch["items"] if item["selected"]]
    if batch["status"] in {"succeeded", "dry_run_succeeded"}:
        dry_run = batch["status"] == "dry_run_succeeded"
        execution = batch.get("execution") or {}
        content = (
            f"{'演练完成，未修改防火墙' if dry_run else '永久封禁已执行并回读核验'}。\n\n"
            f"IP 数量：**{len(selected)}**\n"
            f"目标设备：`{batch['firewall_target_code']}`\n"
            f"新增：{len(execution.get('added_ips') or [])}；已存在：{len(execution.get('existing_ips') or [])}"
        )
        return _card("Aegis 封禁结果", "green", [{"tag": "markdown", "content": content}])
    return _card(
        "Aegis 封禁失败",
        "red",
        [{"tag": "markdown", "content": f"执行失败：{batch.get('error_message') or '未知错误'}"}],
    )
