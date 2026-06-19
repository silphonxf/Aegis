from __future__ import annotations

from typing import Any, Dict
from uuid import uuid4

from .schemas import ToolSpec


class AssistantPolicy:
    def build_pending_action(self, tool: ToolSpec, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action_id": f"act_{uuid4().hex}",
            "tool": tool.name,
            "arguments": arguments,
            "risk_level": tool.risk_level,
        }

    def requires_confirmation(self, tool: ToolSpec) -> bool:
        return bool(tool.requires_confirmation or tool.risk_level == "high")


policy = AssistantPolicy()
