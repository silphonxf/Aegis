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
                reply="我可以帮你查系统状态、巡检记录、自检记录、分析日志，也可以发起重启审批。你可以直接说，例如：帮我看示例业务系统状态。",
                cards=[
                    {
                        "type": "assistant_capabilities",
                        "title": "当前可用能力",
                        "items": [
                            {"label": "系统状态", "value": "查询异常系统、单个系统状态"},
                            {"label": "巡检/自检", "value": "查看最近记录与结果"},
                            {"label": "日志分析", "value": "分析报错文本并给出建议"},
                            {"label": "重启审批", "value": "高风险动作，需确认后发起"},
                        ],
                    }
                ],
                actions=[
                    {"type": "quick_prompt", "label": "查异常系统", "payload": {"message": "帮我查今天有哪些异常系统"}},
                    {"type": "quick_prompt", "label": "查巡检记录", "payload": {"message": "看看示例业务系统最近巡检记录"}},
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
                reply="我会优先帮你查真实已接入的数据；如果当前还没接入对应能力，我也会直接告诉你。你可以继续问我系统状态、系统列表、巡检、自检、日志分析或重启审批。",
                actions=[
                    {"type": "quick_prompt", "label": "看已接入系统", "payload": {"message": "我现在有哪几个系统"}},
                    {"type": "quick_prompt", "label": "看系统状态", "payload": {"message": "帮我看示例业务系统状态"}},
                    {"type": "quick_prompt", "label": "分析日志", "payload": {"message": "帮我分析这段报错日志"}},
                ],
            )
        return RouteResult(intent="general_chat", reply="请告诉我你想完成什么操作。")
