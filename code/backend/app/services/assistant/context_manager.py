from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import uuid4


class ContextManager:
    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}

    def ensure(self, conversation_id: Optional[str]) -> tuple[str, Dict[str, Any]]:
        conv_id = conversation_id or f"conv_{uuid4().hex}"
        ctx = self._store.setdefault(
            conv_id,
            {
                "messages": [],
                "last_tool": None,
                "last_system_name": None,
                "last_system_id": None,
                "last_pending_action": None,
            },
        )
        return conv_id, ctx

    def update(self, conversation_id: str, context: Dict[str, Any]) -> None:
        self._store[conversation_id] = context


context_manager = ContextManager()
