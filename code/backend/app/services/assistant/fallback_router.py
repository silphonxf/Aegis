from __future__ import annotations

from .schemas import RouteResult


class AssistantFallbackRouter:
    """Lightweight fallback intent recognizer.

    V1 keeps this rule-based, but the module boundary is reserved for
    future model-based routing.
    """

    def route(self, message: str) -> RouteResult:
        text = (message or "").strip()
        lowered = text.lower()

        if lowered in {"你好", "您好", "嗨", "hi", "hello", "哈喽"}:
            return RouteResult(
                intent="general_chat",
                reply="你好，我在。想看系统状态、巡检、自检，还是帮你分析日志？",
                actions=[
                    {"type": "quick_prompt", "label": "看系统状态", "payload": {"message": "帮我看示例业务系统状态"}},
                    {"type": "quick_prompt", "label": "看最近巡检", "payload": {"message": "看看示例业务系统最近巡检"}},
                    {"type": "quick_prompt", "label": "分析报错日志", "payload": {"message": "帮我分析这段报错日志"}},
                ],
            )

        if any(keyword in text for keyword in {"你能做什么", "你会什么", "帮助", "help", "能力", "怎么用"}):
            return RouteResult(
                intent="general_chat",
                reply="我可以直接处理移动端里的常用运维能力：巡检、自检、系统状态、日志分析、抓包分析、IP 风险研判、Ping/端口检测、工具任务和应急审批。你直接说要查什么或把日志/附件发给我即可。",
                cards=[
                    {
                        "type": "assistant_capabilities",
                        "title": "移动端 AI 能力",
                        "items": [
                            {"label": "巡检", "value": "查最近巡检记录"},
                            {"label": "自检", "value": "查自检记录、生成 AI 自检报告"},
                            {"label": "系统状态", "value": "查系统列表、状态总览、异常系统和详情"},
                            {"label": "日志/附件", "value": "分析报错文本、系统错误日志和上传文件"},
                            {"label": "网络排障", "value": "抓包分析、IP 风险研判、Ping、端口检测"},
                            {"label": "应急与任务", "value": "发起重启审批、查看工具任务"},
                        ],
                    }
                ],
                actions=[
                    {"type": "quick_prompt", "label": "查异常系统", "payload": {"message": "帮我查今天有哪些异常系统"}},
                    {"type": "quick_prompt", "label": "查巡检记录", "payload": {"message": "看看示例业务系统最近巡检记录"}},
                    {"type": "quick_prompt", "label": "分析 IP", "payload": {"message": "10.11.123.4 是恶意 IP 吗"}},
                ],
            )

        if "重启" in text and not any(keyword in text for keyword in ["审批", "发起", "申请"]):
            return RouteResult(
                intent="general_chat",
                reply="如果你是想发起重启相关操作，可以直接说“帮我为某个系统发起重启审批”。",
                actions=[
                    {"type": "quick_prompt", "label": "发起重启审批", "payload": {"message": "帮我为示例业务系统发起重启审批"}},
                ],
            )

        if "系统" in text:
            return RouteResult(
                intent="general_chat",
                reply="你是想看系统状态、巡检，还是自检？可以直接告诉我具体系统名。",
                actions=[
                    {"type": "quick_prompt", "label": "看系统状态", "payload": {"message": "帮我看示例业务系统状态"}},
                    {"type": "quick_prompt", "label": "看巡检记录", "payload": {"message": "看看示例业务系统最近巡检"}},
                    {"type": "quick_prompt", "label": "看自检记录", "payload": {"message": "看看示例业务系统最近自检"}},
                ],
            )

        if any(keyword in text for keyword in {"链路追踪", "调用链", "apm", "trace", "tracing"}):
            return RouteResult(
                intent="general_chat",
                reply="这类链路追踪/调用链查询能力我这边现在还没真正接入，所以不能给你返回真实列表或状态。如果你愿意，我可以先继续补这块能力入口，或者先帮你查当前已接入监控的系统列表。",
                actions=[
                    {"type": "quick_prompt", "label": "看已接入系统", "payload": {"message": "我现在有哪几个系统"}},
                ],
            )

        if text:
            return RouteResult(
                intent="general_chat",
                reply="我会优先调用已接入的移动端能力。你可以继续问系统状态、巡检、自检、日志/附件分析、抓包、IP 风险、Ping、端口、工具任务或应急审批。",
                actions=[
                    {"type": "quick_prompt", "label": "看已接入系统", "payload": {"message": "我现在有哪几个系统"}},
                    {"type": "quick_prompt", "label": "看系统状态", "payload": {"message": "帮我看示例业务系统状态"}},
                    {"type": "quick_prompt", "label": "分析日志", "payload": {"message": "帮我分析这段报错日志"}},
                ],
            )
        return RouteResult(intent="general_chat", reply="请告诉我你想完成什么操作。")
